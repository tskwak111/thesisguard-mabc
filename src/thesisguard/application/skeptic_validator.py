"""Skeptic validator (Step 9). Fails loudly instead of quietly passing bad output."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import timedelta

from pydantic import BaseModel, ConfigDict

from thesisguard.domain.briefing import BriefingDraft
from thesisguard.domain.enums import ThesisState
from thesisguard.domain.sources import SourceDocument
from thesisguard.domain.state import StateDecision

_STRONG_STATES = {
    ThesisState.STRENGTHENED,
    ThesisState.WEAKENED,
    ThesisState.REVIEW_REQUIRED,
}
_TIME_CONFLICT_TOLERANCE = timedelta(days=1)


class Finding(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str
    severity: str  # BLOCKER or WARNING
    message: str


class SkepticReview(BaseModel):
    model_config = ConfigDict(frozen=True)

    findings: tuple[Finding, ...] = ()

    @property
    def blockers(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "BLOCKER"]

    @property
    def passed(self) -> bool:
        return not self.blockers


def review_draft(
    draft: BriefingDraft,
    sources: Mapping[str, SourceDocument],
    decisions: list[StateDecision],
    opposing_by_stock: dict[str, list[str]],
    injection_spans: tuple[str, ...],
) -> SkepticReview:
    findings: list[Finding] = []

    def blocker(code: str, message: str) -> None:
        findings.append(Finding(code=code, severity="BLOCKER", message=message))

    def warning(code: str, message: str) -> None:
        findings.append(Finding(code=code, severity="WARNING", message=message))

    for claim in draft.claims:
        if not claim.source_ids:
            blocker("UNSUPPORTED_CLAIM", f"claim {claim.claim_id} has no source ID")
            continue
        for sid in claim.source_ids:
            if sid not in sources:
                blocker(
                    "UNKNOWN_SOURCE",
                    f"claim {claim.claim_id} cites unknown source {sid}",
                )
        cited = [sources[sid] for sid in claim.source_ids if sid in sources]
        if len(cited) >= 2:
            as_of_values = [s.as_of for s in cited]
            if max(as_of_values) - min(as_of_values) > _TIME_CONFLICT_TOLERANCE:
                warning(
                    "TIME_CONFLICT",
                    f"claim {claim.claim_id} cites sources with conflicting data cutoffs",
                )

    seen_keys: set[str] = set()
    for key in draft.cited_event_keys:
        if key in seen_keys:
            blocker(
                "DUPLICATE_EVENT_EVIDENCE",
                f"event {key} counted more than once as independent evidence",
            )
        seen_keys.add(key)

    for decision in decisions:
        if decision.new_state in _STRONG_STATES and not decision.evidence_ids_used:
            blocker(
                "UNBACKED_TRANSITION",
                f"{decision.stock_code} moved to {decision.new_state} without evidence IDs",
            )
        opposing = opposing_by_stock.get(decision.stock_code, [])
        if opposing and decision.new_state in _STRONG_STATES:
            warning(
                "OPPOSING_EVIDENCE_HIDDEN",
                f"{decision.stock_code}: opposing evidence {opposing} must appear in the briefing",
            )

    for span in injection_spans:
        texts = [draft.headline, *(c.statement for c in draft.claims)]
        if any(span in text for text in texts):
            blocker(
                "INJECTION_LEAK",
                "an injected command sentence leaked into the briefing text",
            )

    return SkepticReview(findings=tuple(findings))
