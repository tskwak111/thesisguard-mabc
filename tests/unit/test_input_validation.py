"""Contract tests for the DailyEvidencePack input schema and its validator."""

from __future__ import annotations

import hashlib
from typing import Any

import pytest

from thesisguard.application.input_validation import (
    MAX_QUESTIONS,
    PackValidationError,
    parse_pack,
    validate_pack,
)


def _source(source_id: str = "S001", **overrides: Any) -> dict[str, Any]:
    body = overrides.pop("body", "가상의 공시 본문입니다. FICTIONAL TEST DATA.")
    data: dict[str, Any] = {
        "source_id": source_id,
        "publisher": "가상전자공시",
        "url_or_id": "https://example.invalid/filing/1",
        "doc_type": "FILING",
        "published_at": "2026-08-21T09:00:00+09:00",
        "collected_at": "2026-08-22T18:00:00+09:00",
        "as_of": "2026-08-22T15:30:00+09:00",
        "tier": "A",
        "title": "가상전자 공시 제목",
        "body": body,
    }
    data.update(overrides)
    if "content_hash" not in data:
        data["content_hash"] = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return data


def _valid_pack_dict() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "briefing_as_of": "2026-08-22T18:00:00+09:00",
        "first_run": False,
        "portfolio": [
            {
                "stock_code": "A000000",
                "stock_name": "가상전자보통주",
                "market": "KRX",
                "kind": "HOLDING",
                "weight": 30.0,
            },
            {
                "stock_code": "B000000",
                "stock_name": "가상배터리보통주",
                "kind": "WATCH",
            },
        ],
        "thesis_cards": [
            {
                "stock_code": "A000000",
                "summary": "AI 서버 수요로 고부가 메모리 논지 유지",
                "approved_version": "v1",
                "core_assumptions": [
                    {
                        "id": "ASM-1",
                        "text": "AI 서버 투자가 중기적으로 증가한다.",
                        "concept_tags": ["ai_capex"],
                    }
                ],
                "strengthen_conditions": [
                    {
                        "id": "STR-1",
                        "text": "핵심 고객사 AI 설비투자 가이던스 상향",
                        "concept_tags": ["ai_capex"],
                    }
                ],
                "review_conditions": [
                    {
                        "id": "REV-1",
                        "text": "AI 설비투자 축소 발표",
                        "concept_tags": ["ai_capex_down"],
                    }
                ],
                "tracked_indicators": [],
                "risk_factors": ["ai_theme", "long_term_rate"],
            },
            {
                "stock_code": "B000000",
                "stock_name": "가상배터리보통주",
                "summary": "ESS 수요 확대 논지",
                "approved_version": "v1",
                "core_assumptions": [
                    {
                        "id": "ASM-B1",
                        "text": "ESS 설비투자가 증가한다.",
                        "concept_tags": ["ess_capex"],
                    }
                ],
            },
        ],
        "previous_states": [
            {
                "stock_code": "A000000",
                "state": "MAINTAIN",
                "known_event_keys": [],
                "last_briefing_at": "2026-08-21T18:00:00+09:00",
            }
        ],
        "market_context": [],
        "today_sources": [_source()],
    }


class TestParsePack:
    def test_valid_minimal_pack_parses(self) -> None:
        pack = parse_pack(_valid_pack_dict())
        assert pack.schema_version == "1.0"
        assert pack.portfolio[0].kind.value == "HOLDING"
        assert pack.today_sources[0].tier.value == "A"

    def test_naive_datetime_is_rejected(self) -> None:
        data = _valid_pack_dict()
        data["briefing_as_of"] = "2026-08-22T18:00:00"
        with pytest.raises(PackValidationError):
            parse_pack(data)

    def test_unknown_state_value_rejected(self) -> None:
        data = _valid_pack_dict()
        data["previous_states"][0]["state"] = "SUPER_BULLISH"
        with pytest.raises(PackValidationError):
            parse_pack(data)

    def test_content_hash_mismatch_rejected(self) -> None:
        data = _valid_pack_dict()
        data["today_sources"][0]["content_hash"] = "deadbeef"
        with pytest.raises(PackValidationError):
            parse_pack(data)


class TestRequiredInputValidation:
    def test_complete_pack_has_no_errors_and_no_questions(self) -> None:
        report = validate_pack(parse_pack(_valid_pack_dict()))
        assert report.errors == []
        assert report.questions == []

    def test_missing_previous_state_produces_question_not_crash(self) -> None:
        data = _valid_pack_dict()
        data["previous_states"] = []
        data["portfolio"][0]["weight"] = None
        del data["portfolio"][0]["weight"]
        pack = parse_pack(data)
        report = validate_pack(pack)
        assert report.errors == []  # first-run style omission is answerable, not fatal
        assert 1 <= len(report.questions) <= MAX_QUESTIONS

    def test_missing_sources_blocks_analysis_with_questions(self) -> None:
        data = _valid_pack_dict()
        data["today_sources"] = []
        pack = parse_pack(data)
        report = validate_pack(pack)
        assert report.questions, "missing today's material must ask up to 3 questions"
        assert len(report.questions) <= MAX_QUESTIONS

    def test_never_more_than_three_questions_even_when_everything_missing(self) -> None:
        data = _valid_pack_dict()
        data["portfolio"] = []
        data["thesis_cards"] = []
        data["previous_states"] = []
        data["today_sources"] = []
        data["market_context"] = []
        pack = parse_pack(data)
        report = validate_pack(pack)
        assert len(report.questions) == MAX_QUESTIONS

    def test_duplicate_source_ids_are_blocking_error(self) -> None:
        data = _valid_pack_dict()
        data["today_sources"].append(_source())
        pack = parse_pack(data)
        report = validate_pack(pack)
        assert any("S001" in e for e in report.errors)

    def test_portfolio_weight_sum_over_100_is_blocking_error(self) -> None:
        data = _valid_pack_dict()
        data["portfolio"][1]["kind"] = "HOLDING"
        data["portfolio"][1]["weight"] = 80.0
        pack = parse_pack(data)
        report = validate_pack(pack)
        assert any("weight" in e.lower() for e in report.errors)

    def test_conflicting_stock_names_for_same_code_rejected(self) -> None:
        data = _valid_pack_dict()
        data["thesis_cards"][0]["stock_name"] = "가상전자우선주"
        pack = parse_pack(data)
        report = validate_pack(pack)
        assert any("A000000" in e for e in report.errors)

    def test_tier_d_source_is_flagged_but_not_an_error(self) -> None:
        data = _valid_pack_dict()
        rumor = _source(
            source_id="R001",
            doc_type="SOCIAL",
            tier="D",
            title="커뮤니티 루머",
            body="출처 불명의 루머입니다.",
        )
        data["today_sources"].append(rumor)
        pack = parse_pack(data)
        report = validate_pack(pack)
        assert report.errors == []
        assert any(w.source_id == "R001" for w in report.warnings)


class TestThesisCardCoverage:
    def test_portfolio_stock_without_thesis_card_asks_question(self) -> None:
        data = _valid_pack_dict()
        data["portfolio"].append(
            {"stock_code": "C000000", "stock_name": "가상바이오", "kind": "WATCH"}
        )
        pack = parse_pack(data)
        report = validate_pack(pack)
        assert report.errors == []
        assert any("C000000" in q for q in report.questions)
        assert len(report.questions) <= MAX_QUESTIONS
