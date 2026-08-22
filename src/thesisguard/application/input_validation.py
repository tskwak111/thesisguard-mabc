"""Strict schema parsing and required-input validation for DailyEvidencePack.

Missing mandatory inputs never get silently patched. They produce at most
MAX_QUESTIONS clarifying questions; unresolved gaps must lead to HOLD downstream.
"""

from __future__ import annotations

import hashlib
from typing import Any

from pydantic import BaseModel, ConfigDict
from pydantic import ValidationError as PydanticValidationError

from thesisguard.domain.enums import PositionKind, SourceTier
from thesisguard.domain.pack import SCHEMA_VERSION, DailyEvidencePack
from thesisguard.errors import PackValidationError

__all__ = ["MAX_QUESTIONS", "PackValidationError", "parse_pack", "validate_pack"]

MAX_QUESTIONS = 3


def parse_pack(data: dict[str, Any]) -> DailyEvidencePack:
    try:
        return DailyEvidencePack.model_validate(data)
    except PydanticValidationError as exc:
        raise PackValidationError(_format_pydantic_error(exc)) from exc


class Warning_(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_id: str
    code: str
    message: str


class ValidationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    errors: list[str] = []
    warnings: list[Warning_] = []
    questions: list[str] = []


QUESTION_SOURCES_MISSING = (
    "오늘 자료의 출처와 기준 시각을 제공해 주세요. 최소 1개 이상의 source 문서가 필요합니다."
)
QUESTION_THESIS_MISSING = "분석할 종목의 핵심 투자 가정이 담긴 투자논지 카드를 제공해 주세요."
QUESTION_PORTFOLIO_MISSING = "보유·관심 종목 목록(종목명/종목코드/보유·관심 구분)을 제공해 주세요."
QUESTION_PREVIOUS_STATE_MISSING = "종목별 이전 논지 상태 또는 '첫 실행' 여부를 알려주세요."


def _missing_thesis_card_codes(pack: DailyEvidencePack) -> list[str]:
    card_codes = {card.stock_code for card in pack.thesis_cards}
    return [p.stock_code for p in pack.portfolio if p.stock_code not in card_codes]


def validate_pack(pack: DailyEvidencePack) -> ValidationReport:
    errors: list[str] = []
    warnings: list[Warning_] = []

    seen_ids: set[str] = set()
    for source in pack.today_sources:
        if source.source_id in seen_ids:
            errors.append(f"duplicate source_id detected: {source.source_id}")
        seen_ids.add(source.source_id)

    holding_weight = sum(
        item.weight or 0.0 for item in pack.portfolio if item.kind == PositionKind.HOLDING
    )
    if holding_weight > 100.0 + 1e-9:
        errors.append(f"total HOLDING weight exceeds 100%: {holding_weight:.1f}")

    names_by_code: dict[str, str] = {}
    conflicts: list[str] = []
    for item in pack.portfolio:
        known = names_by_code.setdefault(item.stock_code, item.stock_name)
        if known != item.stock_name:
            conflicts.append(item.stock_code)
    for card in pack.thesis_cards:
        if card.stock_name is None:
            continue
        known = names_by_code.setdefault(card.stock_code, card.stock_name)
        if known != card.stock_name:
            conflicts.append(card.stock_code)
    for code in sorted(set(conflicts)):
        errors.append(
            f"conflicting stock names for code {code}: entity must be resolved before analysis"
        )

    questions: list[str] = []
    if not pack.today_sources:
        questions.append(QUESTION_SOURCES_MISSING)
    if not pack.thesis_cards:
        questions.append(QUESTION_THESIS_MISSING)
    missing_cards = _missing_thesis_card_codes(pack)
    if missing_cards:
        questions.append(
            f"다음 종목의 투자논지 카드가 없습니다: {', '.join(missing_cards)}. 핵심 가정을 제공해 주세요."
        )
    if not pack.portfolio:
        questions.append(QUESTION_PORTFOLIO_MISSING)
    if not pack.previous_states and not pack.first_run:
        questions.append(QUESTION_PREVIOUS_STATE_MISSING)
    questions = questions[:MAX_QUESTIONS]

    for source in pack.today_sources:
        if source.tier == SourceTier.D:
            warnings.append(
                Warning_(
                    source_id=source.source_id,
                    code="TIER_D_UNCONFIRMED",
                    message=(
                        f"source {source.source_id} is Tier D; excluded from state transitions"
                    ),
                )
            )
        expected = hashlib.sha256(source.body.encode("utf-8")).hexdigest()
        if source.content_hash != expected:  # defensive double-check beyond parse gate
            errors.append(f"content_hash mismatch for source {source.source_id}")

    if pack.schema_version != SCHEMA_VERSION:
        errors.append(f"unsupported schema_version: {pack.schema_version}")

    return ValidationReport(errors=list(errors), warnings=list(warnings), questions=list(questions))


def _format_pydantic_error(exc: PydanticValidationError) -> str:
    lines = []
    for err in exc.errors():
        loc = ".".join(str(part) for part in err["loc"])
        lines.append(f"{loc}: {err['msg']}")
    return "; ".join(lines) or str(exc)
