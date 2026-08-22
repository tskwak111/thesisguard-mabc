"""Deterministic reference analysis engine driven by pack-authored event_facts."""

from __future__ import annotations

from thesisguard.domain.enums import PolarityHint
from thesisguard.domain.events import EventCandidate
from thesisguard.domain.pack import DailyEvidencePack
from thesisguard.domain.sources import SourceDocument


class FixtureAnalysisEngine:
    """Converts `event_facts` annotations into EventCandidates without any network.

    Sources without annotations produce one UNKNOWN-polarity generic candidate so
    they can still be deduplicated and audited, but they cannot drive transitions.
    """

    def extract_events(self, pack: DailyEvidencePack) -> list[EventCandidate]:
        candidates: list[EventCandidate] = []
        for source in pack.today_sources:
            candidates.extend(self._candidates_for(source))
        return candidates

    def _candidates_for(self, source: SourceDocument) -> list[EventCandidate]:
        if source.event_facts:
            return [
                EventCandidate(
                    source_id=source.source_id,
                    tier=source.tier,
                    published_at=source.published_at,
                    issuer=fact.issuer,
                    action=fact.action,
                    event_type=fact.event_type,
                    entities=fact.entities,
                    event_date=fact.event_date,
                    key_figures=fact.key_figures,
                    conditions=fact.conditions,
                    concepts=fact.concepts,
                    polarity_hint=fact.polarity_hint,
                    quotes=fact.quotes,
                )
                for fact in source.event_facts
            ]
        return [
            EventCandidate(
                source_id=source.source_id,
                tier=source.tier,
                published_at=source.published_at,
                issuer=source.publisher,
                action=source.title,
                event_type="GENERIC",
                entities=(),
                event_date=source.published_at,
                key_figures=(),
                conditions=None,
                concepts=(),
                polarity_hint=PolarityHint.UNKNOWN,
                quotes=(),
            )
        ]
