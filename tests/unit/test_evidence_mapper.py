"""Unit tests for deterministic evidence mapping and thesis-state transitions."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from thesisguard.application.event_normalizer import normalize_events
from thesisguard.application.evidence_mapper import EvidenceMapper
from thesisguard.application.state_transition import decide_state
from thesisguard.domain.enums import (
    ConfirmationLevel,
    Directness,
    EvidenceDirection,
    Novelty,
    PolarityHint,
    Relevance,
    SourceTier,
    ThesisState,
)
from thesisguard.domain.events import EventCandidate
from thesisguard.domain.evidence import EvidenceLink
from thesisguard.domain.state import PreviousState

T0 = datetime(2026, 8, 22, 9, 0, tzinfo=UTC)


def cand(**over: Any) -> EventCandidate:
    data: dict[str, Any] = {
        "source_id": "S001",
        "tier": SourceTier.A,
        "published_at": T0,
        "issuer": "가상전자",
        "action": "무엇인가 발생",
        "event_type": "FILING",
        "entities": ("가상전자",),
        "event_date": T0 - timedelta(days=1),
        "concepts": (),
        "polarity_hint": PolarityHint.POSITIVE,
    }
    data.update(over)
    return EventCandidate.model_validate(data)


def _thesis_card() -> Any:
    from thesisguard.domain.thesis import ThesisCard

    return ThesisCard.model_validate(
        {
            "stock_code": "A000000",
            "stock_name": "가상전자",
            "summary": "AI 메모리 수요 논지",
            "approved_version": "v1",
            "core_assumptions": [
                {"id": "ASM-1", "text": "AI 투자 확대", "concept_tags": ["ai_capex"]}
            ],
            "strengthen_conditions": [
                {"id": "STR-1", "text": "가이던스 상향", "concept_tags": ["guidance_up"]}
            ],
            "review_conditions": [
                {"id": "REV-1", "text": "투자 축소", "concept_tags": ["capex_cut"]}
            ],
            "tracked_indicators": [],
            "risk_factors": ["ai_theme"],
        }
    )


def _map(candidates: list[EventCandidate], novelty: dict[str, Novelty] | None = None):
    events = normalize_events(candidates)
    nov = novelty or {}
    resolver = lambda e: nov.get(e.event_key, Novelty.NEW)  # noqa: E731
    return EvidenceMapper().map_events(events, [_thesis_card()], resolver)


timedelta = __import__("datetime").timedelta


class TestEvidenceMapping:
    def test_positive_tier_a_on_core_assumption_maps_strengthen_direct(self) -> None:
        links = _map([cand(concepts=("ai_capex",))])
        assert len(links) == 1
        link = links[0]
        assert link.relevance is Relevance.CORE_ASSUMPTION
        assert link.target_id == "ASM-1"
        assert link.direction is EvidenceDirection.STRENGTHEN
        assert link.directness is Directness.DIRECT
        assert link.tier is SourceTier.A
        assert link.confirmation is ConfirmationLevel.OFFICIAL
        assert "S001" in link.source_ids

    def test_negative_on_review_condition_flags_trigger_and_weakens(self) -> None:
        links = _map([cand(concepts=("capex_cut",), polarity_hint=PolarityHint.NEGATIVE)])
        assert links[0].relevance is Relevance.REVIEW_CONDITION
        assert links[0].review_trigger_met is True
        assert links[0].direction is EvidenceDirection.WEAKEN

    def test_off_topic_event_is_unrelated(self) -> None:
        links = _map([cand(concepts=("soccer",))])
        assert links[0].relevance is Relevance.UNRELATED

    def test_syndicated_copies_yield_single_evidence_link(self) -> None:
        cands = [
            cand(source_id=f"N{i}", tier=SourceTier.B, concepts=("ai_capex",)) for i in range(10)
        ]
        cands.append(cand(concepts=("ai_capex",)))
        links = _map(cands)
        assert len(links) == 1
        assert len(links[0].source_ids) == 11

    def test_repeat_novelty_recorded_for_gate_use(self) -> None:
        events = normalize_events([cand(concepts=("ai_capex",))])
        links = _map([cand(concepts=("ai_capex",))], novelty={events[0].event_key: Novelty.REPEAT})
        assert links[0].novelty is Novelty.REPEAT


def _link(**over: Any) -> EvidenceLink:
    data: dict[str, Any] = {
        "evidence_id": "E1",
        "event_key": "k",
        "stock_code": "A",
        "relevance": Relevance.CORE_ASSUMPTION,
        "target_id": "ASM-1",
        "direction": EvidenceDirection.STRENGTHEN,
        "directness": Directness.DIRECT,
        "novelty": Novelty.NEW,
        "confirmation": ConfirmationLevel.OFFICIAL,
        "tier": SourceTier.A,
        "impact_horizon": "MEDIUM",
        "source_ids": ("S001",),
    }
    data.update(over)
    return EvidenceLink.model_validate(data)


class TestStateTransitions:
    def _decide(self, links: list[EvidenceLink], prev: ThesisState | None = ThesisState.MAINTAIN):
        ps = PreviousState(stock_code="A", state=prev, known_event_keys=(), last_briefing_at=T0)
        return decide_state(ps, links, T0, stock_code="A")

    def test_no_new_evidence_maintains(self) -> None:
        result = self._decide([])
        assert result.new_state is ThesisState.MAINTAIN

    def test_repeat_only_evidence_maintains(self) -> None:
        result = self._decide([_link(novelty=Novelty.REPEAT)])
        assert result.new_state is ThesisState.MAINTAIN

    def test_tier_a_direct_strengthen(self) -> None:
        result = self._decide([_link()])
        assert result.new_state is ThesisState.STRENGTHENED

    def test_tier_d_rumor_never_changes_state(self) -> None:
        result = self._decide(
            [_link(tier=SourceTier.D, confirmation=ConfirmationLevel.UNCONFIRMED)]
        )
        assert result.new_state is ThesisState.MAINTAIN

    def test_tier_c_alone_cannot_strengthen(self) -> None:
        result = self._decide(
            [
                _link(
                    tier=SourceTier.C,
                    confirmation=ConfirmationLevel.SINGLE_SOURCE,
                )
            ]
        )
        assert result.new_state is not ThesisState.STRENGTHENED

    def test_conflicting_strong_evidence_holds(self) -> None:
        links = [
            _link(),
            _link(
                evidence_id="E2",
                direction=EvidenceDirection.WEAKEN,
                confirmation=ConfirmationLevel.MULTI_CONFIRMED,
                tier=SourceTier.B,
            ),
        ]
        result = self._decide(links)
        assert result.new_state is ThesisState.HOLD
        assert result.hold_reasons

    def test_tier_a_direct_contradiction_from_maintain_can_weaken(self) -> None:
        result = self._decide([_link(direction=EvidenceDirection.WEAKEN)])
        assert result.new_state is ThesisState.WEAKENED

    def test_tier_b_single_negative_is_only_watch(self) -> None:
        """One sensational Tier-B article must NOT flip to WEAKENED."""
        result = self._decide(
            [
                _link(
                    direction=EvidenceDirection.WEAKEN,
                    tier=SourceTier.B,
                    confirmation=ConfirmationLevel.SINGLE_SOURCE,
                )
            ]
        )
        assert result.new_state is ThesisState.WATCH

    def test_tier_b_multi_confirmed_negative_weakens_with_clamp(self) -> None:
        """No Tier A direct evidence: jump is clamped to one step (WATCH)."""
        result = self._decide(
            [
                _link(
                    direction=EvidenceDirection.WEAKEN,
                    tier=SourceTier.B,
                    confirmation=ConfirmationLevel.MULTI_CONFIRMED,
                )
            ]
        )
        assert result.new_state is ThesisState.WATCH

    def test_review_condition_met_by_tier_a_direct(self) -> None:
        result = self._decide(
            [
                _link(
                    relevance=Relevance.REVIEW_CONDITION,
                    direction=EvidenceDirection.WEAKEN,
                )
            ]
        )
        assert result.new_state is ThesisState.REVIEW_REQUIRED

    @pytest.mark.parametrize("bad", [True, False])
    def test_first_run_without_previous_state_is_conservative(self, bad: bool) -> None:
        ps = PreviousState(stock_code="A", state=None, known_event_keys=(), last_briefing_at=None)
        links = [_link()] if bad else []
        result = decide_state(ps, links, T0, stock_code="A")
        if bad:
            assert result.new_state is ThesisState.STRENGTHENED
        else:
            assert result.new_state is ThesisState.MAINTAIN

    def test_hold_previous_state_requires_strong_reason_to_leave(self) -> None:
        """From HOLD, only strong one-sided evidence resumes a directional state."""
        weak = _link(
            direction=EvidenceDirection.WEAKEN, tier=SourceTier.B, directness=Directness.INDIRECT
        )
        result = self._decide([weak], prev=ThesisState.HOLD)
        assert result.new_state is ThesisState.HOLD
