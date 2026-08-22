"""Safety tests: prohibited financial advice must be blocked in Korean and English."""

from __future__ import annotations

import pytest

from thesisguard.safety.prohibited_advice import (
    ProhibitionCategory,
    scan_prohibited_advice,
)


def categories(text: str) -> set[ProhibitionCategory]:
    return {hit.category for hit in scan_prohibited_advice(text)}


class TestKoreanProhibitions:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("지금 매수하세요.", ProhibitionCategory.BUY_SELL_ORDER),
            ("이 종목을 사라.", ProhibitionCategory.BUY_SELL_ORDER),
            ("지금 사야 합니다.", ProhibitionCategory.BUY_SELL_ORDER),
            ("즉시 매도해야 합니다.", ProhibitionCategory.BUY_SELL_ORDER),
            ("팔아라는 답은 드릴 수 없지만 팔아야 합니다.", ProhibitionCategory.BUY_SELL_ORDER),
            ("목표가는 15만 원입니다.", ProhibitionCategory.TARGET_PRICE),
            ("목표 주가 20만원을 제시합니다.", ProhibitionCategory.TARGET_PRICE),
            ("비중을 30%로 늘리세요.", ProhibitionCategory.ALLOCATION_ADVICE),
            ("비중 축소를 권고합니다.", ProhibitionCategory.ALLOCATION_ADVICE),
            ("내일 오를 가능성이 높습니다.", ProhibitionCategory.PRICE_PREDICTION),
            ("단기에 30% 상승할 것으로 예상됩니다.", ProhibitionCategory.PRICE_PREDICTION),
        ],
    )
    def test_blocked(self, text: str, expected: ProhibitionCategory) -> None:
        assert expected in categories(text)

    def test_euphemisms_are_caught(self) -> None:
        assert categories("지금이 들어갈 타이밍입니다.") == {ProhibitionCategory.BUY_SELL_ORDER}
        assert categories("물타기로 대응하는 것이 좋겠습니다.") == {
            ProhibitionCategory.ALLOCATION_ADVICE
        }


class TestEnglishProhibitions:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("You should buy now.", ProhibitionCategory.BUY_SELL_ORDER),
            ("Sell immediately.", ProhibitionCategory.BUY_SELL_ORDER),
            ("Target price is 150,000 KRW.", ProhibitionCategory.TARGET_PRICE),
            ("Increase your position to 30%.", ProhibitionCategory.ALLOCATION_ADVICE),
            ("It will rise tomorrow.", ProhibitionCategory.PRICE_PREDICTION),
        ],
    )
    def test_blocked(self, text: str, expected: ProhibitionCategory) -> None:
        assert expected in categories(text)


class TestAllowedExpressions:
    """The safety filter must not over-block legitimate monitoring language."""

    @pytest.mark.parametrize(
        "text",
        [
            "본 결과는 정보 정리이며 매수·매도 지시가 아닙니다.",
            "투자논지가 약화됐습니다.",
            "핵심 가정을 뒷받침하는 증거가 확인되었습니다.",
            "사용자의 최종 투자 판단은 사용자가 내려야 합니다.",
            "매수·매도 추천을 제공하지 않습니다.",
            "주가는 하락했습니다. 원인은 불명입니다.",
        ],
    )
    def test_allowed(self, text: str) -> None:
        assert categories(text) == set()
