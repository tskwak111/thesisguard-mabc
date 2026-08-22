"""Portfolio common-risk detection (Step 8).

Qualitative levels only. No fake precision scores, probabilities or loss estimates.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from thesisguard.domain.enums import (
    EvidenceDirection,
    Novelty,
    PositionKind,
    Relevance,
)
from thesisguard.domain.evidence import EvidenceLink
from thesisguard.domain.portfolio import PortfolioItem
from thesisguard.domain.thesis import ThesisCard


class RiskLevel(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


KOREAN_LEVEL: dict[RiskLevel, str] = {
    RiskLevel.HIGH: "높음",
    RiskLevel.MEDIUM: "중간",
    RiskLevel.LOW: "낮음",
}


class RiskExposure(BaseModel):
    model_config = ConfigDict(frozen=True)

    factor: str
    stock_codes: tuple[str, ...]
    stock_names: tuple[str, ...] = ()
    total_weight: float | None = None
    level: RiskLevel
    rationale: str
    deteriorating_today: bool = False


def _level(count: int, total_weight: float | None) -> RiskLevel:
    if count >= 3 or (total_weight is not None and total_weight >= 50.0):
        return RiskLevel.HIGH
    if count == 2 or (total_weight is not None and total_weight >= 25.0):
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def map_common_risks(
    positions: list[PortfolioItem],
    thesis_cards: list[ThesisCard],
    context_links: list[EvidenceLink],
    briefing_as_of: datetime,  # noqa: ARG001 reserved for time-aware rules
    adverse_market_tags: frozenset[str] | set[str] = frozenset(),
    market_sources_by_tag: dict[str, tuple[str, ...]] | None = None,
) -> list[RiskExposure]:
    name_by_code = {p.stock_code: p.stock_name for p in positions}
    codes_by_factor: dict[str, list[str]] = {}
    for card in thesis_cards:
        for factor in card.risk_factors:
            codes_by_factor.setdefault(factor, [])
            if card.stock_code not in codes_by_factor[factor]:
                codes_by_factor[factor].append(card.stock_code)

    exposures: list[RiskExposure] = []
    for factor in sorted(codes_by_factor):
        codes = tuple(sorted(codes_by_factor[factor]))
        if len(codes) < 2:
            continue  # common-risk map covers only shared exposure across positions
        holding_weights = [
            p.weight
            for p in positions
            if p.stock_code in codes and p.kind == PositionKind.HOLDING and p.weight is not None
        ]
        total_weight = round(sum(holding_weights), 2) if holding_weights else None
        deteriorating = (
            any(
                link.novelty in {Novelty.NEW, Novelty.UPDATE}
                and link.direction in {EvidenceDirection.WEAKEN, EvidenceDirection.MIXED}
                and factor in link.matched_concepts
                and link.relevance is Relevance.CONTEXT
                for link in context_links
            )
            or factor in adverse_market_tags
        )
        level = _level(len(codes), total_weight)
        names = [name_by_code.get(c, c) for c in codes]
        weight_note = (
            f" 보유 비중 합계는 {total_weight:.0f}%입니다." if total_weight is not None else ""
        )
        rationale = f"{len(codes)}개 종목({', '.join(names)})이 동일 위험요인 '{factor}'에 노출되어 있습니다.{weight_note}"
        market_sources = (market_sources_by_tag or {}).get(factor)
        if market_sources and factor in adverse_market_tags:
            rationale += f" 시장 맥락에서 오늘 악화 신호가 확인되었습니다(근거: {', '.join(market_sources)})."
        elif deteriorating:
            rationale += " 오늘 신규 악화 신호가 확인되었습니다."
        exposures.append(
            RiskExposure(
                factor=factor,
                stock_codes=codes,
                stock_names=tuple(names),
                total_weight=total_weight,
                level=level,
                rationale=rationale,
                deteriorating_today=deteriorating,
            )
        )
    return exposures
