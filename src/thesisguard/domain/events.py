"""Event candidates (analysis-engine output contract) and normalized events."""

from __future__ import annotations

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from thesisguard.domain.enums import PolarityHint, SourceTier


class EventCandidate(BaseModel):
    """One structured event extracted from one source document.

    This is the strict schema every analysis engine (LLM or fixture) must satisfy.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: str = Field(min_length=1)
    tier: SourceTier
    published_at: AwareDatetime
    issuer: str = Field(min_length=1)
    action: str = Field(min_length=1)
    event_type: str = Field(min_length=1)
    entities: tuple[str, ...] = ()
    event_date: AwareDatetime
    key_figures: tuple[str, ...] = ()
    conditions: str | None = None
    concepts: tuple[str, ...] = ()
    polarity_hint: PolarityHint
    quotes: tuple[str, ...] = ()


class NormalizedEvent(BaseModel):
    """One real-world event after deduplication. Article count is NOT evidence count."""

    model_config = ConfigDict(frozen=True)

    event_key: str
    base_key: str
    representative_source_id: str
    member_source_ids: tuple[str, ...]
    candidates: tuple[EventCandidate, ...]
    issuer: str
    action: str
    event_type: str
    entities: tuple[str, ...]
    event_date: AwareDatetime
    key_figures: tuple[str, ...]
    concepts: tuple[str, ...]
    polarity_hint: PolarityHint
