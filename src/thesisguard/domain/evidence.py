"""Evidence links: the auditable connection between an event and a thesis element."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from thesisguard.domain.enums import (
    ConfirmationLevel,
    Directness,
    EvidenceDirection,
    ImpactHorizon,
    Novelty,
    Relevance,
    SourceTier,
)


class EvidenceLink(BaseModel):
    """Every axis required by the design (§13.2) plus provenance and opposition."""

    model_config = ConfigDict(frozen=True)

    evidence_id: str = Field(min_length=1)
    event_key: str
    stock_code: str
    relevance: Relevance
    target_id: str | None = None
    direction: EvidenceDirection
    directness: Directness
    novelty: Novelty
    confirmation: ConfirmationLevel
    tier: SourceTier
    impact_horizon: ImpactHorizon = ImpactHorizon.MEDIUM
    source_ids: tuple[str, ...] = ()
    quote_refs: tuple[str, ...] = ()
    review_trigger_met: bool = False
    opposing_evidence_ids: tuple[str, ...] = ()
