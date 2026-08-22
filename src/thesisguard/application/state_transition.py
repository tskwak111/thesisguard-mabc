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
    stock_code: str = "UNKNOWN",
) -> StateDecision:
    prev_state = previous.state if previous else None
    usable = [e for e in evidences if _transitionable(e)]
    strong = [e for e in usable if _is_strong(e)]

    if not strong:
        if prev_state is ThesisState.HOLD:
            return StateDecision(
                stock_code=stock_code,
                previous_state=prev_state,
                new_state=ThesisState.HOLD,
                reasons=("이전 상태가 판단 보류이며, 약한 신호만으로는 해소되지 않습니다",),
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
                reasons=("신뢰도는 있으나 확인 수준이 낮은 부정 신호로 관찰 필요",),
                evidence_ids_used=tuple(e.evidence_id for e in negatives),
            )
        return StateDecision(
            stock_code=stock_code,
            previous_state=prev_state,
            new_state=ThesisState.MAINTAIN,
            reasons=("중요한 신규 강증거가 없어 상태를 유지합니다",),
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
        reasons.append("강한 강화·약화 증거가 상충하여 판단을 보류합니다")
        used.extend(e.evidence_id for e in strengthens + weakens)
        decision = _result(ThesisState.HOLD)
        return decision.model_copy(update={"hold_reasons": tuple(reasons)})

    if review_hit:
        reasons.append("사용자가 설정한 재검토 조건을 Tier A 직접 증거가 충족했습니다")
        used.append(review_hit[0].evidence_id)
        return _result(ThesisState.REVIEW_REQUIRED)

    if weakens:
        reasons.append("핵심 가정에 반하는 고신뢰 직접 증거가 확인되었습니다")
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
                reasons=("강화 증거가 공식·복수 확인 요건을 충족하지 않습니다",),
            )
        reasons.append("공식 출처 또는 독립 복수 확인된 지지 증거가 확인되었습니다")
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
        reasons.append(f"1일 1단계 게이트 적용: {target.korean} → {clamped.korean}")
        return _result(clamped)
    return _result(target)


def _step_toward(current: ThesisState, target: ThesisState) -> ThesisState:
    from thesisguard.domain.enums import SEVERITY_LADDER

    ci = SEVERITY_LADDER.index(current) if current in SEVERITY_LADDER else 0
    ti = SEVERITY_LADDER.index(target)
    step = ci + 1 if ti > ci else max(ci - 1, 0)
    return SEVERITY_LADDER[step]
