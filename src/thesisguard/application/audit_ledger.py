"""Append-only style audit ledger covering every pipeline decision."""

from __future__ import annotations

from typing import Any

from pydantic import AwareDatetime, BaseModel, ConfigDict


class EventAudit(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_key: str
    representative_source_id: str
    member_source_ids: tuple[str, ...]
    novelty: str
    issuer: str
    action: str


class ExclusionRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    subject: str
    reason: str


class AuditLedger(BaseModel):
    model_config = ConfigDict(frozen=True)

    briefing_as_of: AwareDatetime
    schema_version: str = "1.0"
    sources_used: tuple[str, ...] = ()
    issues: tuple[str, ...] = ()
    questions: tuple[str, ...] = ()
    events_created: tuple[EventAudit, ...] = ()
    excluded: tuple[ExclusionRecord, ...] = ()
    mappings: tuple[dict[str, Any], ...] = ()
    state_changes: tuple[dict[str, Any], ...] = ()
    skeptic_passed: bool = True
    skeptic_findings: tuple[dict[str, Any], ...] = ()
    injection_flags: tuple[str, ...] = ()

    def to_json(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
