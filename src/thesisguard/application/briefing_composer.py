"""Briefing composition (Step 10): one report model, two synchronized renderings."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Final

from thesisguard.domain.briefing import BriefingReport, StockBriefing
from thesisguard.errors import ContractViolation
from thesisguard.safety.prohibited_advice import assert_no_prohibited_advice

SECTION_TITLES: Final[tuple[str, ...]] = (
    "1. 오늘 한 줄",
    "2. 어제와 달라진 핵심 변화",
    "3. 보유종목",
    "4. 관심종목",
    "5. 포트폴리오 공통 위험",
    "6. 판단 보류·정보 부족",
    "7. 정보 품질",
    "8. 안전 안내",
)

NO_CHANGE_HEADLINE: Final[str] = "오늘 투자논지를 변경할 만한 새로운 증거는 확인되지 않았습니다."


def _stock_section(sb: StockBriefing) -> list[str]:
    is_watch = sb.kind == "WATCH"
    lines = [f"### {sb.stock_name} — {sb.state.korean}"]
    if sb.previous_state_label:
        lines.append(f"- 상태 변화: {sb.previous_state_label}")
    if sb.condition_access:
        lines.append(f"- 관심 조건 접근 여부: {sb.condition_access}")
    if sb.facts:
        for fact in sb.facts:
            lines.append(f"- 확인된 사실: {fact}")
    elif is_watch:
        lines.append("- 새롭게 달라진 항목: 없음")
    else:
        lines.append(
            "- 확인된 사실: 오늘 투자논지를 변경할 만한 새로운 증거는 확인되지 않았습니다."
        )
    if sb.thesis_impact and not is_watch:
        lines.append(f"- 투자논지 영향(해석): {sb.thesis_impact}")
    opposing = (
        "; ".join(sb.opposing_notes)
        if sb.opposing_notes
        else "오늘 자료 범위 내에서는 확인되지 않았습니다"
    )
    lines.append(f"- 반대 또는 제한 증거: {opposing}")
    for item in sb.next_check_items:
        lines.append(f"- 다음 확인 항목: {item}")
    if sb.source_ids:
        lines.append(f"- 근거 출처: {', '.join(sb.source_ids)}")
    return lines


def render_markdown(report: BriefingReport) -> str:
    lines: list[str] = ["# 오늘의 투자논지 변화 브리핑"]

    lines += ["", f"## {SECTION_TITLES[0]}", "", report.headline]

    lines += ["", f"## {SECTION_TITLES[1]}"]
    if report.key_changes:
        for change in report.key_changes:
            src = f" ({', '.join(change.source_ids)})" if change.source_ids else ""
            lines.append(f"- {change.description}{src}")
    else:
        lines.append(f"- {NO_CHANGE_HEADLINE}")

    lines += ["", f"## {SECTION_TITLES[2]}"]
    for holding in report.holdings:
        lines += _stock_section(holding)
    if not report.holdings:
        lines.append("- 해당 없음")

    lines += ["", f"## {SECTION_TITLES[3]}"]
    for watch in report.watchlist:
        lines += _stock_section(watch)
    if not report.watchlist:
        lines.append("- 해당 없음")

    lines += ["", f"## {SECTION_TITLES[4]}"]
    for risk in report.common_risks:
        marker = " (오늘 악화)" if risk.deteriorating_today else ""
        lines.append(f"- [{risk.level_korean}] {risk.factor}: {risk.rationale}{marker}")
    if not report.common_risks:
        lines.append("- 2개 이상 종목이 공유하는 공통 위험요인은 발견되지 않았습니다.")

    lines += ["", f"## {SECTION_TITLES[5]}"]
    if report.hold_items:
        for item in report.hold_items:
            lines.append(f"- {item}")
    else:
        lines.append("- 판단 보류 항목 없음")
    for trend in report.unconfirmed_trends:
        lines.append(f"- 미확인 동향(상태 판정에 미반영): {trend}")

    iq = report.info_quality
    lines += [
        "",
        f"## {SECTION_TITLES[6]}",
        f"- 공식 원문 수: {iq.official_sources}",
        f"- 신뢰 가능한 보도 수: {iq.trusted_secondary}",
        f"- 중복 제거 수: {iq.duplicates_merged}",
        f"- 제외한 미확인 정보 수: {iq.excluded_unconfirmed}",
        f"- 데이터 기준 시각: {iq.data_as_of.isoformat()}",
    ]

    lines += ["", f"## {SECTION_TITLES[7]}", "", report.safety_notice, ""]
    markdown = "\n".join(lines)
    assert_no_prohibited_advice(markdown)
    return markdown


def render_json(report: BriefingReport) -> str:
    return json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2)


def write_outputs(report: BriefingReport, output_dir: Path) -> tuple[Path, Path]:
    """Write briefing.json and briefing.md atomically-consistent with each other."""
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "briefing.json"
    md_path = output_dir / "briefing.md"
    payload = render_json(report)
    parsed = BriefingReport.model_validate_json(payload)
    if parsed != report:
        raise ContractViolation("JSON round-trip changed the briefing report")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    json_path.write_text(payload + "\n", encoding="utf-8")
    return json_path, md_path


def make_briefing_id(as_of_iso: str, headline: str) -> str:
    return hashlib.sha256(f"{as_of_iso}|{headline}".encode()).hexdigest()[:16]
