"""Single source of truth for all domain enums and their Korean display labels."""

from __future__ import annotations

from enum import StrEnum

KOREAN: dict[str, str] = {
    "STRENGTHENED": "강화됨",
    "MAINTAIN": "유지",
    "WATCH": "관찰 필요",
    "WEAKENED": "약화됨",
    "REVIEW_REQUIRED": "재검토 필요",
    "HOLD": "판단 보류",
    "FIRST_RUN": "첫 실행",
}


class ThesisState(StrEnum):
    """The only six allowed thesis states. Never extended without a design change."""

    STRENGTHENED = "STRENGTHENED"
    MAINTAIN = "MAINTAIN"
    WATCH = "WATCH"
    WEAKENED = "WEAKENED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    HOLD = "HOLD"

    @property
    def korean(self) -> str:
        return KOREAN[self.value]


# Severity ladder used by the deterministic one-step-per-day gate.
SEVERITY_LADDER: tuple[ThesisState, ...] = (
    ThesisState.MAINTAIN,
    ThesisState.WATCH,
    ThesisState.WEAKENED,
    ThesisState.REVIEW_REQUIRED,
)


def ladder_distance(a: ThesisState, b: ThesisState) -> int | None:
    """Distance on the negative-severity ladder; None if either state is off-ladder."""
    try:
        return abs(SEVERITY_LADDER.index(a) - SEVERITY_LADDER.index(b))
    except ValueError:
        return None


class PositionKind(StrEnum):
    HOLDING = "HOLDING"
    WATCH = "WATCH"


class SourceTier(StrEnum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class DocType(StrEnum):
    FILING = "FILING"
    IR = "IR"
    NEWS = "NEWS"
    REPORT = "REPORT"
    SOCIAL = "SOCIAL"


class Directness(StrEnum):
    DIRECT = "DIRECT"
    INDIRECT = "INDIRECT"


class Novelty(StrEnum):
    NEW = "NEW"
    UPDATE = "UPDATE"
    REPEAT = "REPEAT"
    RESURFACED = "RESURFACED"


class ConfirmationLevel(StrEnum):
    OFFICIAL = "OFFICIAL"
    MULTI_CONFIRMED = "MULTI_CONFIRMED"
    SINGLE_SOURCE = "SINGLE_SOURCE"
    UNCONFIRMED = "UNCONFIRMED"


class ImpactHorizon(StrEnum):
    SHORT = "SHORT"
    MEDIUM = "MEDIUM"
    LONG = "LONG"


class EvidenceDirection(StrEnum):
    STRENGTHEN = "STRENGTHEN"
    WEAKEN = "WEAKEN"
    MIXED = "MIXED"
    NEUTRAL = "NEUTRAL"
    UNKNOWN = "UNKNOWN"


class PolarityHint(StrEnum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    MIXED = "MIXED"
    NEUTRAL = "NEUTRAL"
    UNKNOWN = "UNKNOWN"


class Relevance(StrEnum):
    CORE_ASSUMPTION = "CORE_ASSUMPTION"
    STRENGTHEN_CONDITION = "STRENGTHEN_CONDITION"
    REVIEW_CONDITION = "REVIEW_CONDITION"
    TRACKED_INDICATOR = "TRACKED_INDICATOR"
    CONTEXT = "CONTEXT"
    UNRELATED = "UNRELATED"


KOREAN["POSITION_HOLDING"] = "보유"
KOREAN["POSITION_WATCH"] = "관심"
