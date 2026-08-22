"""Contract tests for event normalization (extraction output), dedup and novelty."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from pydantic import ValidationError

from thesisguard.application.event_normalizer import (
    compute_base_key,
    normalize_events,
)
from thesisguard.application.novelty_detector import classify_novelty
from thesisguard.domain.enums import Novelty, PolarityHint, SourceTier
from thesisguard.domain.events import EventCandidate
from thesisguard.domain.state import PreviousState

T0 = datetime(2026, 8, 22, 9, 0, tzinfo=UTC)


def cand(**over: Any) -> EventCandidate:
    data: dict[str, Any] = {
        "source_id": "S001",
        "tier": SourceTier.A,
        "published_at": T0,
        "issuer": "가상전자",
        "action": "AI 데이터센터 투자 계약 체결",
        "event_type": "CONTRACT",
        "entities": ("가상전자",),
        "event_date": T0 - timedelta(days=1),
        "key_figures": ("규모 2조원",),
        "concepts": ("ai_capex",),
        "polarity_hint": PolarityHint.POSITIVE,
    }
    data.update(over)
    return EventCandidate.model_validate(data)


class TestDeduplication:
    def test_press_release_syndication_merges_to_one_event(self) -> None:
        """20 syndicated articles about one press release must be ONE event."""
        cands = [cand()] + [cand(source_id=f"N{i:03d}", tier=SourceTier.B) for i in range(1, 20)]
        events = normalize_events(cands)
        assert len(events) == 1
        assert len(events[0].member_source_ids) == 20
        assert events[0].representative_source_id == "S001"  # Tier A outranks B

    def test_titles_differing_but_same_fact_merge(self) -> None:
        a = cand(source_id="A", action="AI 데이터센터 투자 계약 체결")
        b = cand(source_id="B", tier=SourceTier.B, action="가상전자, 거대 AI 계약 수주")
        assert len(normalize_events([a, b])) == 1

    def test_different_issuers_are_separate_events(self) -> None:
        assert len(normalize_events([cand(), cand(issuer="다른회사")])) == 2

    def test_different_key_figures_are_separate_events(self) -> None:
        assert len(normalize_events([cand(), cand(key_figures=("규모 5조원",))])) == 2

    def test_order_independent_stable_result(self) -> None:
        a = cand(source_id="A")
        b = cand(source_id="B", tier=SourceTier.B)
        r1 = normalize_events([a, b])
        r2 = normalize_events([b, a])
        assert [e.event_key for e in r1] == [e.event_key for e in r2]

    def test_base_key_excludes_figures_so_updates_are_detectable(self) -> None:
        k1 = compute_base_key(cand())
        k2 = compute_base_key(cand(key_figures=("규모 5조원",)))
        assert k1 == k2


class TestNovelty:
    def _prev(self, known: tuple[str, ...], last_at: datetime | None = T0) -> PreviousState:
        return PreviousState(
            stock_code="X",
            state="MAINTAIN",
            known_event_keys=known,
            last_briefing_at=last_at,
        )

    def test_unseen_recent_event_is_new(self) -> None:
        event = normalize_events([cand()])[0]
        assert classify_novelty(event, self._prev(()), T0) is Novelty.NEW

    def test_same_full_key_is_repeat(self) -> None:
        event = normalize_events([cand()])[0]
        prev = self._prev((event.event_key,))
        assert classify_novelty(event, prev, T0) is Novelty.REPEAT

    def test_changed_figures_on_known_event_is_update(self) -> None:
        old = normalize_events([cand()])[0]
        updated = normalize_events([cand(key_figures=("규모 5조원",))])[0]
        assert compute_base_key(updated.candidates[0]) == compute_base_key(old.candidates[0])
        prev = self._prev((old.event_key,))
        assert classify_novelty(updated, prev, T0) is Novelty.UPDATE

    def test_old_article_resurfaced_today_is_excluded_from_core(self) -> None:
        stale = normalize_events([cand(event_date=T0 - timedelta(days=30))])[0]
        novelty = classify_novelty(stale, self._prev(()), T0)
        assert novelty is Novelty.RESURFACED

    def test_no_previous_state_means_new(self) -> None:
        event = normalize_events([cand()])[0]
        assert classify_novelty(event, None, T0) is Novelty.NEW


class TestExtractionContract:
    def test_candidate_requires_structured_fields(self) -> None:
        with pytest.raises(ValidationError):
            EventCandidate.model_validate({"source_id": "S", "title": "제목만 있는 기사"})
