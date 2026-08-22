"""Previous thesis state carried between daily runs."""

from __future__ import annotations

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from thesisguard.domain.enums import ThesisState


class PreviousState(BaseModel):
    """`state=None` means FIRST_RUN: the user has no earlier recorded state."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    stock_code: str = Field(min_length=1)
    state: ThesisState | None = None
    known_event_keys: tuple[str, ...] = ()
    last_briefing_at: AwareDatetime | None = None


class StateDecision(BaseModel):
    """Outcome of the deterministic transition engine for one stock."""

    model_config = ConfigDict(frozen=True)

    stock_code: str
    previous_state: ThesisState | None = None
    new_state: ThesisState
    reasons: tuple[str, ...] = ()
    evidence_ids_used: tuple[str, ...] = ()
    hold_reasons: tuple[str, ...] = ()
