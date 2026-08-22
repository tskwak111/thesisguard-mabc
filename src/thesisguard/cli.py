"""Local CLI: validate / analyze / evaluate / safety-check. No network required."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from thesisguard.adapters.fixture_analysis_engine import FixtureAnalysisEngine
from thesisguard.application.input_validation import PackValidationError, parse_pack, validate_pack
from thesisguard.errors import ThesisGuardError

EXIT_OK = 0
EXIT_FAILURE = 1
EXIT_USAGE = 2


def _load_json(path_text: str) -> tuple[Path, dict[str, object]]:
    path = Path(path_text)
    if not path.exists():
        print(f"오류: 파일을 찾을 수 없습니다: {path}", file=sys.stderr)
        raise SystemExit(EXIT_FAILURE)
    try:
        return path, json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"오류: JSON 파싱 실패 ({path}): {exc}", file=sys.stderr)
        raise SystemExit(EXIT_FAILURE) from exc


def cmd_validate(argv: list[str]) -> int:
    _, data = _load_json(argv[0])
    try:
        pack = parse_pack(data)
    except PackValidationError as exc:
        print(f"스키마 검증 실패:\n{exc}", file=sys.stderr)
        return EXIT_FAILURE
    report = validate_pack(pack)
    for error in report.errors:
        print(f"[오류] {error}")
    for warn in report.warnings:
        print(f"[경고] {warn.message}")
    for question in report.questions:
        print(f"[질문] {question}")
    if not report.errors and not report.questions and not report.warnings:
        print("OK: 입력 팩이 유효합니다.")
    elif not report.errors:
        print("OK: 분석 가능하나 위 표기된 항목을 확인하세요.")
    return EXIT_OK if not report.errors else EXIT_FAILURE


def cmd_analyze(argv: list[str]) -> int:
    _, data = _load_json(argv[0])
    output_dir = Path(argv[1])
    try:
        pack = parse_pack(data)
        from thesisguard.application.briefing_composer import write_outputs
        from thesisguard.application.orchestrator import run_analysis

        result = run_analysis(pack, FixtureAnalysisEngine())
    except (PackValidationError, ThesisGuardError, Exception) as exc:
        if isinstance(exc, Exception) and not isinstance(exc, ThesisGuardError):
            name = type(exc).__name__
            print(f"분석 오류({name}): {exc}", file=sys.stderr)
        else:
            print(f"분석 오류: {exc}", file=sys.stderr)
        return EXIT_FAILURE
    json_path, md_path = write_outputs(result.report, output_dir)
    audit_path = output_dir / "audit.json"
    audit_path.write_text(
        json.dumps(result.audit.to_json(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"JSON 결과: {json_path}")
    print(f"Markdown 브리핑: {md_path}")
    print(f"감사 원장: {audit_path}")
    print(result.report.headline)
    for issue in result.validation_issues:
        print(f"[참고] {issue}")
    return EXIT_OK


def cmd_evaluate(argv: list[str]) -> int:
    dataset_dir, gold_dir = Path(argv[0]), Path(argv[1])
    from thesisguard.evaluation.runner import run_evaluation

    try:
        summary = run_evaluation(dataset_dir, gold_dir)
    except ThesisGuardError as exc:
        print(f"평가 오류: {exc}", file=sys.stderr)
        return EXIT_FAILURE
    summary_payload = json.dumps(summary.model_dump(mode="json"), ensure_ascii=False, indent=2)
    out_path = dataset_dir.parent / "evaluation_summary.json"
    out_path.write_text(summary_payload + "\n", encoding="utf-8")
    print(summary_payload)
    print(f"요약 저장: {out_path}")
    return EXIT_OK


def cmd_safety_check(argv: list[str]) -> int:
    text_path, _unused = Path(argv[0]), None
    if not text_path.exists():
        print(f"오류: 파일을 찾을 수 없습니다: {text_path}", file=sys.stderr)
        return EXIT_FAILURE
    text = text_path.read_text(encoding="utf-8")
    from thesisguard.safety.prohibited_advice import scan_prohibited_advice

    hits = scan_prohibited_advice(text)
    failed = False
    for hit in hits:
        failed = True
        print(f"[금지표현] {hit.category.value}: {hit.matched_text!r} @ {hit.line[:60]}...")
    if not failed:
        print("OK: 금지 투자지시 표현이 발견되지 않았습니다.")
    return EXIT_FAILURE if failed else EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="thesisguard", description="ThesisGuard - Thesis Change Detector reference CLI"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_validate = sub.add_parser("validate", help="DailyEvidencePack 스키마·필수 입력 검증")
    p_validate.add_argument("pack")

    p_analyze = sub.add_parser("analyze", help="팩 분석 후 JSON/Markdown/감사원장 출력")
    p_analyze.add_argument("pack")
    p_analyze.add_argument("--output-dir", required=True)

    p_eval = sub.add_parser("evaluate", help="평가 데이터셋 실행 및 지표 계산")
    p_eval.add_argument("dataset_dir")
    p_eval.add_argument("--gold", required=True)

    p_safety = sub.add_parser("safety-check", help="텍스트 파일 금지 투자지시 스캔")
    p_safety.add_argument("file")

    args = parser.parse_args(argv)
    handlers = {
        "validate": lambda a: cmd_validate([a.pack]),
        "analyze": lambda a: cmd_analyze([a.pack, a.output_dir]),
        "evaluate": lambda a: cmd_evaluate([a.dataset_dir, a.gold]),
        "safety-check": lambda a: cmd_safety_check([a.file]),
    }
    try:
        return handlers[args.command](args)
    except SystemExit as exc:
        code = exc.code
        return code if isinstance(code, int) else EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
