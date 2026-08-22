"""Briefing draft and final report models shared across the pipeline."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from thesisguard.domain.enums import ThesisState


class FactClaim(BaseModel):
    """One factual assertion that must trace to at least one real source."""

    model_config = ConfigDict(frozen=True)

    claim_id: str = Field(min_length=1)
    statement: str
    source_ids: tuple[str, ...] = ()
    event_keys: tuple[str, ...] = ()
    kind: Literal["FACT", "INTERPRETATION", "UNCONFIRMED"] = "FACT"


class BriefingDraft(BaseModel):
    """Intermediate structured briefing before Markdown composition."""

    model_config = ConfigDict(frozen=True)

    as_of: AwareDatetime
    headline: str
    key_changes: tuple[str, ...] = ()
    claims: tuple[FactClaim, ...] = ()
    cited_event_keys: tuple[str, ...] = ()

    def as_of_dt(self) -> datetime:
        return self.as_of


class KeyChange(BaseModel):
    model_config = ConfigDict(frozen=True)

    description: str
    stock_code: str | None = None
    event_key: str
    source_ids: tuple[str, ...] = ()
    direction_korean: str = ""


class StockBriefing(BaseModel):
    model_config = ConfigDict(frozen=True)

    stock_code: str
    stock_name: str
    kind: str
    state: ThesisState
    previous_state_label: str | None = None
    facts: tuple[str, ...] = ()
    thesis_impact: str | None = None
    condition_access: str | None = None
    next_check_items: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()
    opposing_notes: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()


class RiskBrief(BaseModel):
    model_config = ConfigDict(frozen=True)

    factor: str
    level_korean: str
    rationale: str
    deteriorating_today: bool = False


class InfoQuality(BaseModel):
    model_config = ConfigDict(frozen=True)

    official_sources: int
    trusted_secondary: int
    duplicates_merged: int
    excluded_unconfirmed: int
    data_as_of: AwareDatetime


class BriefingReport(BaseModel):
    """Final machine-checkable output. Markdown is rendered 1:1 from this model."""

    model_config = ConfigDict(frozen=True)

    schema_version: str = "1.0"
    briefing_id: str
    as_of: AwareDatetime
    headline: str
    no_change: bool = False
    key_changes: tuple[KeyChange, ...] = ()
    holdings: tuple[StockBriefing, ...] = ()
    watchlist: tuple[StockBriefing, ...] = ()
    common_risks: tuple[RiskBrief, ...] = ()
    hold_items: tuple[str, ...] = ()
    unconfirmed_trends: tuple[str, ...] = ()
    info_quality: InfoQuality
    claims: tuple[FactClaim, ...] = ()
    safety_notice: str = (
        "본 결과는 정보 정리와 기존 투자논지 점검을 위한 것이며 매수·매도 지시가 아닙니다. "
        "투자 수익률·목표가를 제공하지 않으며 최종 투자 판단은 사용자가 내려야 합니다."
    )
