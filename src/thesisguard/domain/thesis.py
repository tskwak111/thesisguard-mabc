"""Thesis card: the user-approved investment thesis and its structured elements."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ThesisElement(BaseModel):
    """A core assumption, strengthen condition, review condition or tracked indicator.

    concept_tags drive deterministic evidence mapping; free text alone is never matched.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    concept_tags: tuple[str, ...] = ()


class ThesisCard(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    stock_code: str = Field(min_length=1)
    stock_name: str | None = None
    summary: str = Field(min_length=1)
    approved_version: str = Field(min_length=1)
    horizon: str | None = None
    core_assumptions: tuple[ThesisElement, ...] = Field(min_length=1)
    strengthen_conditions: tuple[ThesisElement, ...] = ()
    review_conditions: tuple[ThesisElement, ...] = ()
    tracked_indicators: tuple[ThesisElement, ...] = ()
    risk_factors: tuple[str, ...] = ()

    def name(self) -> str:
        return self.stock_name or self.stock_code
