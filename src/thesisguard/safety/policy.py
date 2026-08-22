"""Shared financial-safety policy constants for output filters."""

from __future__ import annotations

import re
from enum import StrEnum
from re import Pattern


class ProhibitionCategory(StrEnum):
    BUY_SELL_ORDER = "BUY_SELL_ORDER"
    TARGET_PRICE = "TARGET_PRICE"
    ALLOCATION_ADVICE = "ALLOCATION_ADVICE"
    PRICE_PREDICTION = "PRICE_PREDICTION"


# Lines containing any of these markers are safety disclaimers, not advice.
ALLOWLIST_MARKERS: tuple[str, ...] = (
    "지시가 아님",
    "제공하지 않습니다",
    "권하지 않습니다",
    "권고하지 않습니다",
)

PROHIBITED_PATTERNS: tuple[tuple[ProhibitionCategory, Pattern[str]], ...] = tuple(
    (category, re.compile(pattern, re.IGNORECASE))
    for category, pattern in [
        # buy/sell orders and imperatives (KR)
        (
            ProhibitionCategory.BUY_SELL_ORDER,
            r"매수하세요|매수하라|매수해야|지금 사야|사야 합니다|매수 적기|들어갈 타이밍",
        ),
        (
            ProhibitionCategory.BUY_SELL_ORDER,
            r"매도하세요|매도하라|매도해야|즉시 매도|팔아야 합니다|지금 팔아|매도 적기",
        ),
        (ProhibitionCategory.BUY_SELL_ORDER, r"(?<![가-힣])사라(?![가-힣])"),
        (ProhibitionCategory.BUY_SELL_ORDER, r"(?<![가-힣])팔아라(?![가-힣])"),
        (ProhibitionCategory.BUY_SELL_ORDER, r"\bbuy\s+now\b|\byou\s+should\s+buy\b"),
        (
            ProhibitionCategory.BUY_SELL_ORDER,
            r"\bsell\s+now\b|\bsell\s+immediately\b|\byou\s+should\s+sell\b",
        ),
        # target price / return promises
        (ProhibitionCategory.TARGET_PRICE, r"목표가|목표\s?주가|목표수익률|target\s+price"),
        # allocation / position sizing advice
        (
            ProhibitionCategory.ALLOCATION_ADVICE,
            r"비중.{0,12}늘리|비중.{0,12}줄이|비중 확대|비중 축소|적정 비중|물타기로 대응|increase\s+your\s+position|reduce\s+your\s+position",
        ),
        # price/return predictions
        (
            ProhibitionCategory.PRICE_PREDICTION,
            r"오를 가능성|상승할 것으로 예상|상승 예상|올라갈 것|will\s+rise",
        ),
    ]
)


def is_allowlisted(line: str) -> bool:
    return any(marker in line for marker in ALLOWLIST_MARKERS)
