"""Portfolio positions. Quantities and average prices are never used to derive advice."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from thesisguard.domain.enums import PositionKind


class PortfolioItem(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    stock_code: str = Field(min_length=1)
    stock_name: str = Field(min_length=1)
    market: str | None = None
    kind: PositionKind
    weight: float | None = Field(default=None, ge=0, le=100)
