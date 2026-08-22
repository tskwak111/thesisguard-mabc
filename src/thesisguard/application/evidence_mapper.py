"""Deterministic evidence mapping (Steps 5-6).

Concept tags on thesis elements are matched against event concepts. Direction is
derived from polarity hints; the state engine re-validates every strong transition.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable

from thesisguard.domain.enums import (
    ConfirmationLevel,
    Directness,
    EvidenceDirection,
    ImpactHorizon,
    Novelty,
    PolarityHint,
    Relevance,
    SourceTier,
)
from thesisguard.domain.events import NormalizedEvent
from thesisguard.domain.evidence import EvidenceLink
from thesisguard.domain.thesis import ThesisCard

_DIRECT_RELEVANCE = {
    Relevance.CORE_ASSUMPTION,
    Relevance.STRENGTHEN_CONDITION,
    Relevance.REVIEW_CONDITION,
}

_DIRECTION_BY_POLARITY = {
    PolarityHint.POSITIVE: EvidenceDirection.STRENGTHEN,
    PolarityHint.NEGATIVE: EvidenceDirection.WEAKEN,
    PolarityHint.MIXED: EvidenceDirection.MIXED,
    PolarityHint.NEUTRAL: EvidenceDirection.NEUTRAL,
    PolarityHint.UNKNOWN: EvidenceDirection.UNKNOWN,
}


def _confirmation(event: NormalizedEvent, rep_tier: SourceTier) -> ConfirmationLevel:
    if rep_tier == SourceTier.D:
        return ConfirmationLevel.UNCONFIRMED
    if rep_tier == SourceTier.A:
        return ConfirmationLevel.OFFICIAL
    if len(event.member_source_ids) >= 2:
        return ConfirmationLevel.MULTI_CONFIRMED
    if rep_tier == SourceTier.C:
        return ConfirmationLevel.UNCONFIRMED
    return ConfirmationLevel.SINGLE_SOURCE


class EvidenceMapper:
    def map_events(
        self,
        events: list[NormalizedEvent],
        thesis_cards: list[ThesisCard],
        novelty_resolver: Callable[[NormalizedEvent], Novelty] | None = None,
        risk_factor_tags_by_code: dict[str, tuple[str, ...]] | None = None,
    ) -> list[EvidenceLink]:
        links: list[EvidenceLink] = []
        resolve = novelty_resolver or (lambda event: Novelty.NEW)
        for event in events:
            novelty = resolve(event)
            for card in thesis_cards:
                link = self._map_single(event, card, novelty, risk_factor_tags_by_code or {})
                if link is not None:
                    links.append(link)
        return links

    def _map_single(
        self,
        event: NormalizedEvent,
        card: ThesisCard,
        novelty: Novelty,
        risk_tags_by_code: dict[str, tuple[str, ...]],
    ) -> EvidenceLink | None:
        concepts = set(event.concepts)
        best: tuple[Relevance, str | None] | None = None

        for assumption in card.core_assumptions:
            if concepts & set(assumption.concept_tags):
                best = (Relevance.CORE_ASSUMPTION, assumption.id)
                break
        if best is None:
            for condition in card.review_conditions:
                if concepts & set(condition.concept_tags):
                    best = (Relevance.REVIEW_CONDITION, condition.id)
                    break
        if best is None:
            for condition in card.strengthen_conditions:
                if concepts & set(condition.concept_tags):
                    best = (Relevance.STRENGTHEN_CONDITION, condition.id)
                    break
        if best is None:
            for indicator in card.tracked_indicators:
                if concepts & set(indicator.concept_tags):
                    best = (Relevance.TRACKED_INDICATOR, indicator.id)
                    break
        if best is None:
            risk_tags = set(card.risk_factors) | set(risk_tags_by_code.get(card.stock_code, ()))
            if concepts & risk_tags:
                best = (Relevance.CONTEXT, None)

        relevance, target_id = best if best else (Relevance.UNRELATED, None)
        matched: tuple[str, ...] = ()
        if best is not None:
            matched = (
                tuple(sorted(concepts & set(card.risk_factors)))
                if relevance is Relevance.CONTEXT
                else event.concepts
            )

        rep_tier = event.candidates[0].tier if event.candidates else SourceTier.D
        direction = _DIRECTION_BY_POLARITY[event.polarity_hint]
        review_trigger_met = relevance is Relevance.REVIEW_CONDITION and direction in {
            EvidenceDirection.WEAKEN,
            EvidenceDirection.MIXED,
        }
        directness = Directness.DIRECT if relevance in _DIRECT_RELEVANCE else Directness.INDIRECT
        horizon = (
            ImpactHorizon.SHORT
            if relevance in {Relevance.CONTEXT, Relevance.TRACKED_INDICATOR}
            else ImpactHorizon.MEDIUM
        )

        digest = hashlib.sha256(
            f"{event.event_key}:{card.stock_code}:{relevance}".encode()
        ).hexdigest()[:10]
        return EvidenceLink(
            evidence_id=f"EV-{digest}",
            event_key=event.event_key,
            stock_code=card.stock_code,
            relevance=relevance,
            target_id=target_id,
            direction=direction,
            directness=directness,
            novelty=novelty,
            confirmation=_confirmation(event, rep_tier),
            tier=rep_tier,
            impact_horizon=horizon,
            source_ids=event.member_source_ids,
            matched_concepts=matched,
            quote_refs=event.candidates[0].quotes if event.candidates else (),
            review_trigger_met=review_trigger_met,
        )
