"""Source documents and event-fact annotations (the strict LLM-output contract)."""

from __future__ import annotations

import hashlib

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from thesisguard.domain.enums import DocType, PolarityHint, SourceTier
from thesisguard.errors import PackValidationError


class EventFact(BaseModel):
    """Structured annotation of one event inside a source document.

    This is the contract an LLM extraction step must satisfy. Locally it is authored
    by the pack writer; it never bypasses the deterministic state gates downstream.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    issuer: str = Field(min_length=1)
    action: str = Field(min_length=1)
    entities: tuple[str, ...] = ()
    event_type: str = Field(min_length=1)
    event_date: AwareDatetime
    key_figures: tuple[str, ...] = ()
    conditions: str | None = None
    concepts: tuple[str, ...] = ()
    polarity_hint: PolarityHint
    quotes: tuple[str, ...] = ()


class SourceDocument(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", validate_assignment=True)

    source_id: str = Field(min_length=1)
    publisher: str = Field(min_length=1)
    url_or_id: str
    doc_type: DocType
    published_at: AwareDatetime
    collected_at: AwareDatetime
    as_of: AwareDatetime
    tier: SourceTier
    title: str
    body: str
    content_hash: str
    event_facts: tuple[EventFact, ...] = ()

    @field_validator("content_hash")
    @classmethod
    def hash_must_match_body(cls, v: str, info: ValidationInfo) -> str:
        body = info.data.get("body")
        if isinstance(body, str) and v != hashlib.sha256(body.encode("utf-8")).hexdigest():
            raise PackValidationError(f"content_hash does not match body for source {v[:12]}")
        return v
