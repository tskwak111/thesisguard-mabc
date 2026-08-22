"""The single input unit of the Thesis Change Detector skill."""

from __future__ import annotations

from pydantic import AwareDatetime, BaseModel, ConfigDict

from thesisguard.domain.enums import PolarityHint
from thesisguard.domain.portfolio import PortfolioItem
from thesisguard.domain.sources import SourceDocument
from thesisguard.domain.state import PreviousState
from thesisguard.domain.thesis import ThesisCard

SCHEMA_VERSION = "1.0"


class MarketContextItem(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    indicator: str
    value_or_change: str
    as_of: AwareDatetime
    source_id: str
    risk_factor_tags: tuple[str, ...] = ()
    """Qualitative direction supplied by the pack author; UNKNOWN is never inferred."""
    change_direction: PolarityHint = PolarityHint.UNKNOWN


class DailyEvidencePack(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str
    briefing_as_of: AwareDatetime
    first_run: bool = False
    portfolio: tuple[PortfolioItem, ...] = ()
    thesis_cards: tuple[ThesisCard, ...] = ()
    previous_states: tuple[PreviousState, ...] = ()
    market_context: tuple[MarketContextItem, ...] = ()
    today_sources: tuple[SourceDocument, ...] = ()
    user_question: str | None = None

    def stocks(self) -> dict[str, str]:
        return {item.stock_code: item.stock_name for item in self.portfolio}

    def thesis_by_code(self) -> dict[str, ThesisCard]:
        return {card.stock_code: card for card in self.thesis_cards}
