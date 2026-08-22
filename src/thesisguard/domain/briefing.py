"""Briefing draft models shared by composer, skeptic validator and audit ledger."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


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
