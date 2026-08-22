"""Unit tests for portfolio common-risk detection (Step 8)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from thesisguard.application.risk_mapper import (
    RiskLevel,
    map_common_risks,
)
from thesisguard.domain.enums import (
    ConfirmationLevel,
    Directness,
    Novelty,
    Relevance,
    SourceTier,
)
from thesisguard.domain.evidence import EvidenceLink
from thesisguard.domain.portfolio import PortfolioItem
from thesisguard.domain.thesis import ThesisCard

T0 = datetime(2026, 8, 22, tzinfo=UTC)


def _card(code: str, name: str, risks: tuple[str, ...]) -> ThesisCard:
    data: dict[str, Any] = {
        "stock_code": code,
        "stock_name": name,
        "summary": f"{name} 논지",
        "approved_version": "v1",
        "core_assumptions": [{"id": f"ASM-{code}", "text": "핵심 가정", "concept_tags": ["x"]}],
        "risk_factors": risks,
    }
    return ThesisCard.model_validate(data)


def _pos(code: str, name: str, kind: str = "HOLDING", weight: float | None = None) -> PortfolioItem:
    return PortfolioItem.model_validate(
        {"stock_code": code, "stock_name": name, "kind": kind}
        | ({"weight": weight} if weight is not None else {})
    )


def _context_link(stock: str, concept: str, direction: str = "WEAKEN") -> EvidenceLink:
    return EvidenceLink.model_validate(
        {
            "evidence_id": f"E-{stock}-{concept}",
            "event_key": f"k-{stock}-{concept}",
            "stock_code": stock,
            "relevance": Relevance.CONTEXT,
            "direction": direction,
            "directness": Directness.INDIRECT,
            "novelty": Novelty.NEW,
            "confirmation": ConfirmationLevel.OFFICIAL,
            "tier": SourceTier.A,
            "impact_horizon": "SHORT",
            "source_ids": ("S001",),
            "matched_concepts": (concept,),
        }
    )


class TestCommonRiskMapping:
    def test_three_positions_sharing_theme_is_high(self) -> None:
        cards = [
            _card("A", "가상전자", ("ai_theme",)),
            _card("B", "가상전력", ("ai_theme",)),
            _card("C", "가상소재", ("ai_theme",)),
        ]
        positions = [
            _pos("A", "가상전자"),
            _pos("B", "가상전력"),
            _pos("C", "가상소재"),
        ]
        result = map_common_risks(positions, cards, [], T0)
        assert len(result) == 1
        assert result[0].level is RiskLevel.HIGH
        assert len(result[0].stock_codes) == 3

    def test_two_positions_is_medium_single_exposure_excluded(self) -> None:
        """Common-risk map covers shared exposure; single-stock factors are omitted."""
        cards = [
            _card("A", "가상전자", ("ai_theme",)),
            _card("B", "가상전력", ("ai_theme",)),
            _card("D", "가상제약", ("rate",)),
        ]
        positions = [
            _pos(c, n) for c, n in [("A", "가상전자"), ("B", "가상전력"), ("D", "가상제약")]
        ]
        result = {r.factor: r.level for r in map_common_risks(positions, cards, [], T0)}
        assert result == {"ai_theme": RiskLevel.MEDIUM}

    def test_weight_sum_reported_when_available(self) -> None:
        cards = [
            _card("A", "가", ("ai",)),
            _card("B", "나", ("ai",)),
            _card("C", "다", ("ai",)),
        ]
        positions = [
            _pos("A", "가", weight=20),
            _pos("B", "나", weight=15),
            _pos("C", "다", weight=10),
        ]
        result = map_common_risks(positions, cards, [], T0)
        assert result[0].total_weight == 45.0

    def test_no_shared_factors_gives_empty_map(self) -> None:
        cards = [
            _card("A", "가", ("ai",)),
            _card("B", "나", ("bio",)),
        ]
        positions = [_pos("A", "가"), _pos("B", "나")]
        assert map_common_risks(positions, cards, [], T0) == []

    def test_fresh_negative_context_link_marks_deterioration_today(self) -> None:
        cards = [
            _card("A", "가", ("ai",)),
            _card("B", "나", ("ai",)),
            _card("C", "다", ("ai",)),
        ]
        positions = [_pos("A", "가"), _pos("B", "나"), _pos("C", "다")]
        links = [_context_link("A", "ai")]
        result = map_common_risks(positions, cards, links, T0)
        assert result[0].deteriorating_today is True
        assert result[0].rationale

    def test_old_or_positive_context_does_not_mark_deterioration(self) -> None:
        cards = [
            _card("A", "가", ("ai",)),
            _card("B", "나", ("ai",)),
            _card("C", "다", ("ai",)),
        ]
        positions = [_pos("A", "가"), _pos("B", "나"), _pos("C", "다")]
        stale_repeat = _context_link("A", "ai").model_copy(update={"novelty": Novelty.REPEAT})
        positive = _context_link("B", "ai", direction="STRENGTHEN")
        result = map_common_risks(positions, cards, [stale_repeat, positive], T0)
        assert all(r.deteriorating_today is False for r in result)
