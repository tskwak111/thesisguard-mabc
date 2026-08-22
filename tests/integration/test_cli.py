"""Integration tests for the local CLI surface."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from thesisguard.cli import main

if TYPE_CHECKING:
    import pytest as _pytest


def run(capsys: _pytest.CaptureFixture[str], *argv: str) -> tuple[int, str, str]:
    code = main(list(argv))
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_validate_ok(tmp_path: Path, capsys: _pytest.CaptureFixture[str]) -> None:
    pack_path = Path("examples/normal/daily_evidence_pack.json")
    code, out, err = run(capsys, "validate", str(pack_path))
    assert code == 0, (out, err)
    assert "OK" in out


def test_validate_missing_input_reports_questions(
    capsys: _pytest.CaptureFixture[str],
) -> None:
    pack_path = Path("examples/missing_input/daily_evidence_pack.json")
    code, out, _err = run(capsys, "validate", str(pack_path))
    assert code == 0  # questions are non-fatal for validate
    assert "[질문]" in out


def test_analyze_writes_json_md_audit(tmp_path: Path, capsys: _pytest.CaptureFixture[str]) -> None:
    outdir = tmp_path / "out"
    code, out, err = run(
        capsys,
        "analyze",
        "examples/no_change/daily_evidence_pack.json",
        "--output-dir",
        str(outdir),
    )
    assert code == 0, (out, err)
    briefing = json.loads((outdir / "briefing.json").read_text())
    assert briefing["headline"]
    assert (outdir / "briefing.md").exists()
    assert (outdir / "audit.json").exists()


def test_safety_check_flags_bad_file(tmp_path: Path, capsys: _pytest.CaptureFixture[str]) -> None:
    bad = tmp_path / "bad.md"
    bad.write_text("지금 매수하세요.", encoding="utf-8")
    code, out, _err = run(capsys, "safety-check", str(bad))
    assert code == 1
    assert "금지표현" in out
    good = tmp_path / "good.md"
    good.write_text("투자논지가 약화됐습니다.", encoding="utf-8")
    code2, out2, _e2 = run(capsys, "safety-check", str(good))
    assert code2 == 0
    assert "OK" in out2


def test_missing_file_is_clean_error(tmp_path: Path, capsys: _pytest.CaptureFixture[str]) -> None:
    code, _out, err = run(capsys, "validate", str(tmp_path / "nope.json"))
    assert code == 1
    assert "Traceback" not in err
