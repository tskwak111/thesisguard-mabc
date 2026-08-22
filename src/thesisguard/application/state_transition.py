"""Deterministic thesis-state transition gates (Step 7).

The analysis layer only proposes; this module decides. Strong transitions must pass
explicit code gates: source tier, directness, novelty, confirmation and conflict rules.
"""

from __future__ import annotations

from datetime import datetime

from thesisguard.domain.enums import (
    ConfirmationLevel,
    Directness,
    EvidenceDirection,
    Novelty,
    Relevance,
    SourceTier,
    ThesisState,
    ladder_distance,
)
from thesisguard.domain.evidence import EvidenceLink
from thesisguard.domain.state import PreviousState, StateDecision

_TRANSITION_NOVELTIES = {Novelty.NEW, Novelty.UPDATE}
_RELEVANCES = {
    Relevance.CORE_ASSUMPTION,
    Relevance.STRENGTHEN_CONDITION,
    Relevance.REVIEW_CONDITION,
}


def _is_strong(link: EvidenceLink) -> bool:
    """Strong evidence: Tier A direct, or Tier B with official/multi confirmation."""
    if link.directness is not Directness.DIRECT:
        return False
    if link.tier == SourceTier.A:
        return True
    return link.tier == SourceTier.B and link.confirmation in {
        ConfirmationLevel.OFFICIAL,
        ConfirmationLevel.MULTI_CONFIRMED,
    }


def _transitionable(link: EvidenceLink) -> bool:
    return (
        link.novelty in _TRANSITION_NOVELTIES
        and link.tier != SourceTier.D
        and link.confirmation is not ConfirmationLevel.UNCONFIRMED
        and link.relevance in _RELEVANCES
        and link.direction in {EvidenceDirection.STRENGTHEN, EvidenceDirection.WEAKEN}
    )


def decide_state(
    previous: PreviousState | None,
    evidences: list[EvidenceLink],
    briefing_as_of: datetime,
) -> StateDecision:
    prev_state = previous.state if previous else None
    stock_code = previous.stock_code if previous is not None else "UNKNOWN"
    usable = [e for e in evidences if _transitionable(e)]
    strong = [e for e in usable if _is_strong(e)]

    if not strong:
        if prev_state is ThesisState.HOLD:
            return StateDecision(
                stock_code=stock_code,
                previous_state=prev_state,
                new_state=ThesisState.HOLD,
                reasons=("previous state is HOLD; weak signals do not resolve the conflict",),
            )
        negatives = [
            e
            for e in usable
            if e.direction is EvidenceDirection.WEAKEN and e.novelty in _TRANSITION_NOVELTIES
        ]
        if negatives:
            return StateDecision(
                stock_code=stock_code,
                previous_state=prev_state,
                new_state=ThesisState.WATCH,
                reasons=("credible but not fully confirmed negative signal; watch only",),
                evidence_ids_used=tuple(e.evidence_id for e in negatives),
            )
        return StateDecision(
            stock_code=stock_code,
            previous_state=prev_state,
            new_state=ThesisState.MAINTAIN,
            reasons=("no strong new material evidence; state maintained",),
        )

    strengthens = [e for e in strong if e.direction is EvidenceDirection.STRENGTHEN]
    weakens = [e for e in strong if e.direction is EvidenceDirection.WEAKEN]

    reasons: list[str] = []
    used: list[str] = []

    def _result(state: ThesisState) -> StateDecision:
        return StateDecision(
            stock_code=stock_code,
            previous_state=prev_state,
            new_state=state,
            reasons=tuple(reasons),
            evidence_ids_used=tuple(used),
        )

    review_hit = [
        e
        for e in usable
        if e.relevance is Relevance.REVIEW_CONDITION
        and e.direction in {EvidenceDirection.WEAKEN, EvidenceDirection.MIXED}
        and e.tier == SourceTier.A
        and e.directness is Directness.DIRECT
        and e.novelty in _TRANSITION_NOVELTIES
    ]

    if strengthens and weakens:
        reasons.append("conflicting strong strengthen/weaken evidence; judgment held")
        used.extend(e.evidence_id for e in strengthens + weakens)
        decision = _result(ThesisState.HOLD)
        return decision.model_copy(update={"hold_reasons": tuple(reasons)})

    if review_hit:
        reasons.append("user-defined review condition met by direct Tier A evidence")
        used.append(review_hit[0].evidence_id)
        return _result(ThesisState.REVIEW_REQUIRED)

    if weakens:
        reasons.append("direct high-credibility contrary evidence on core assumption")
        used.extend(e.evidence_id for e in weakens)
        target = ThesisState.WEAKENED
    elif strengthens:
        gate_ok = any(
            e.tier == SourceTier.A or e.confirmation is ConfirmationLevel.MULTI_CONFIRMED
            for e in strengthens
        )
        if not gate_ok:
            return StateDecision(
                stock_code=stock_code,
                previous_state=prev_state,
                new_state=ThesisState.MAINTAIN,
                reasons=("strengthen evidence lacks official/multi confirmation",),
            )
        reasons.append("official or independently confirmed supporting evidence")
        used.extend(e.evidence_id for e in strengthens)
        target = ThesisState.STRENGTHENED
    else:
        return _result(ThesisState.MAINTAIN)

    if prev_state is None:
        return _result(target)

    distance = ladder_distance(prev_state, target)
    has_tier_a_direct = any(
        e.tier == SourceTier.A and e.directness is Directness.DIRECT for e in strong
    )
    if (
        distance is not None
        and distance > 1
        and not (has_tier_a_direct or target is ThesisState.STRENGTHENED)
    ):
        clamped = _step_toward(prev_state, target)
        reasons.append(
            f"one-step-per-day gate applied: {target.value} downgraded to {clamped.value}"
        )
        return _result(clamped)
    return _result(target)


def _step_toward(current: ThesisState, target: ThesisState) -> ThesisState:
    from thesisguard.domain.enums import SEVERITY_LADDER

    ci = SEVERITY_LADDER.index(current) if current in SEVERITY_LADDER else 0
    ti = SEVERITY_LADDER.index(target)
    step = ci + 1 if ti > ci else max(ci - 1, 0)
    return SEVERITY_LADDER[step]
