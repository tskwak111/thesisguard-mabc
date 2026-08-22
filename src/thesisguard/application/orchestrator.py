"""Daily pipeline orchestrator: Steps 1-10, deterministic, fully audited."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict

from thesisguard.adapters.fixture_analysis_engine import FixtureAnalysisEngine
from thesisguard.application.audit_ledger import (
    AuditLedger,
    EventAudit,
    ExclusionRecord,
)
from thesisguard.application.briefing_composer import NO_CHANGE_HEADLINE, make_briefing_id
from thesisguard.application.event_normalizer import normalize_events
from thesisguard.application.evidence_mapper import EvidenceMapper
from thesisguard.application.input_validation import parse_pack, validate_pack
from thesisguard.application.novelty_detector import classify_novelty
from thesisguard.application.risk_mapper import KOREAN_LEVEL, map_common_risks
from thesisguard.application.skeptic_validator import review_draft
from thesisguard.domain.briefing import (
    BriefingDraft,
    BriefingReport,
    FactClaim,
    InfoQuality,
    KeyChange,
    RiskBrief,
    StockBriefing,
)
from thesisguard.domain.enums import (
    EvidenceDirection,
    Novelty,
    PolarityHint,
    PositionKind,
    Relevance,
    SourceTier,
)
from thesisguard.domain.events import NormalizedEvent
from thesisguard.domain.pack import DailyEvidencePack
from thesisguard.domain.sources import SourceDocument
from thesisguard.domain.state import PreviousState
from thesisguard.ports.analysis_engine import AnalysisEngine
from thesisguard.safety.prompt_injection import detect_injection_spans, redact_injections

_DIRECTION_KOREAN = {
    EvidenceDirection.STRENGTHEN: "강화",
    EvidenceDirection.WEAKEN: "약화",
    EvidenceDirection.MIXED: "혼합",
    EvidenceDirection.NEUTRAL: "중립",
    EvidenceDirection.UNKNOWN: "판단 불가",
}


class OrchestratorError(Exception):
    pass


@dataclass(frozen=True)
class OrchestratorResult:
    report: BriefingReport
    markdown: str
    audit: AuditLedger
    used_sources: list[SourceDocument]
    validation_issues: tuple[str, ...]


class RunArtifacts(BaseModel):
    model_config = ConfigDict(frozen=True)

    payload_json: str
    payload_md: str


def _prev_state_for(pack: DailyEvidencePack, stock_code: str) -> PreviousState | None:
    for prev in pack.previous_states:
        if prev.stock_code == stock_code:
            return prev
    return None


def _novelty_resolver(pack: DailyEvidencePack) -> Callable[[NormalizedEvent], Novelty]:
    name_to_code = {name: code for code, name in pack.stocks().items()}

    def resolve(event: NormalizedEvent) -> Novelty:
        target_code = None
        for entity in event.entities:
            code = name_to_code.get(entity)
            if code:
                target_code = code
                break
        prev = None
        if target_code:
            prev = _prev_state_for(pack, target_code)
        elif pack.previous_states:
            prev = pack.previous_states[0]
        return classify_novelty(event, prev, pack.briefing_as_of)

    return resolve


def run(
    pack_data: dict[str, Any],
    engine: AnalysisEngine | None = None,
) -> OrchestratorResult:
    return run_analysis(parse_pack(pack_data), engine or FixtureAnalysisEngine())


def run_analysis(pack: DailyEvidencePack, engine: AnalysisEngine) -> OrchestratorResult:
    validation = validate_pack(pack)
    if validation.errors:
        raise OrchestratorError("입력 오류: " + "; ".join(validation.errors))

    sources_by_id = {s.source_id: s for s in pack.today_sources}
    cards = pack.thesis_by_code()

    # Step 2-3: extraction + dedup
    candidates = engine.extract_events(pack)
    events = normalize_events(candidates)

    # Step 4: novelty
    resolver = _novelty_resolver(pack)
    novelty_by_key = {event.event_key: resolver(event) for event in events}

    # Step 5-6: evidence mapping
    links = EvidenceMapper().map_events(events, list(cards.values()), resolver)
    relevant_links = [link for link in links if link.relevance is not Relevance.UNRELATED]

    # Step 7: deterministic state decisions
    from thesisguard.application.state_transition import decide_state

    decisions = []
    for card in pack.thesis_cards:
        card_links = [link for link in relevant_links if link.stock_code == card.stock_code]
        prev = _prev_state_for(pack, card.stock_code)
        decisions.append(decide_state(prev, card_links, pack.briefing_as_of))

    # Skeptic gate: blockers downgrade strong transitions to HOLD (fail loud, not quiet)
    injection_flags: tuple[str, ...] = tuple(
        flag for source in pack.today_sources for flag in detect_injection_spans(source.body)
    )
    draft_claims: list[FactClaim] = []
    cited_keys: list[str] = []
    key_changes: list[KeyChange] = []
    ranked = sorted(
        [
            link
            for link in relevant_links
            if link.novelty in {Novelty.NEW, Novelty.UPDATE}
            and link.direction
            in {EvidenceDirection.STRENGTHEN, EvidenceDirection.WEAKEN, EvidenceDirection.MIXED}
        ],
        key=lambda link: (
            link.tier.value,
            0 if link.directness.value == "DIRECT" else 1,
            -len(link.source_ids),
            link.evidence_id,
        ),
    )
    event_by_key = {e.event_key: e for e in events}
    for link in ranked[:3]:
        event = event_by_key[link.event_key]
        statement = redact_injections(f"{event.issuer}: {event.action}")
        claim = FactClaim(
            claim_id=f"C-{link.evidence_id}",
            statement=statement,
            source_ids=(event.representative_source_id,),
            event_keys=(link.event_key,),
            kind="FACT",
        )
        draft_claims.append(claim)
        cited_keys.append(link.event_key)
        key_changes.append(
            KeyChange(
                description=f"{statement} — 논지 {_DIRECTION_KOREAN[link.direction]} 신호",
                stock_code=link.stock_code,
                event_key=link.event_key,
                source_ids=(event.representative_source_id,)
                + tuple(s for s in link.source_ids if s != event.representative_source_id)[:2],
                direction_korean=_DIRECTION_KOREAN[link.direction],
            )
        )

    opposing_by_stock: dict[str, list[str]] = {}
    for link in relevant_links:
        if link.direction is EvidenceDirection.WEAKEN:
            opposing_by_stock.setdefault(link.stock_code, []).append(link.evidence_id)

    draft = BriefingDraft(
        as_of=pack.briefing_as_of,
        headline=key_changes[0].description if key_changes else NO_CHANGE_HEADLINE,
        claims=tuple(draft_claims),
        cited_event_keys=tuple(cited_keys),
    )
    review = review_draft(
        draft=draft,
        sources=sources_by_id,
        decisions=decisions,
        opposing_by_stock=opposing_by_stock,
        injection_spans=injection_flags,
    )

    final_decisions = []
    if not review.passed:
        blocker_codes = {f.code for f in review.blockers}
        for decision in decisions:
            if decision.new_state in {"STRENGTHENED", "WEAKENED", "REVIEW_REQUIRED"}:
                final_decisions.append(
                    decision.model_copy(
                        update={
                            "new_state": __import__(
                                "thesisguard.domain.enums", fromlist=["ThesisState"]
                            ).ThesisState.HOLD,
                            "hold_reasons": tuple(decision.hold_reasons)
                            + ("skeptic: " + ",".join(sorted(blocker_codes)),),
                        }
                    )
                )
            else:
                final_decisions.append(decision)
    else:
        final_decisions = decisions

    # Step 8: portfolio common risks
    context_links = [link for link in relevant_links if link.relevance is Relevance.CONTEXT]
    exposures = map_common_risks(
        list(pack.portfolio), list(cards.values()), context_links, pack.briefing_as_of
    )
    risk_briefs = [
        RiskBrief(
            factor=e.factor,
            level_korean=KOREAN_LEVEL[e.level],
            rationale=e.rationale,
            deteriorating_today=e.deteriorating_today,
        )
        for e in exposures
    ]

    def stock_briefing(card_stock: str, kind: PositionKind) -> StockBriefing:
        item = next((p for p in pack.portfolio if p.stock_code == card_stock), None)
        decision = next((d for d in final_decisions if d.stock_code == card_stock), None)
        state = decision.new_state if decision else None
        if state is None:
            from thesisguard.domain.enums import ThesisState

            state = ThesisState.MAINTAIN
        card = cards.get(card_stock)
        facts = [
            c.statement
            for c in draft_claims
            if any(
                link.stock_code == card_stock and c.claim_id.endswith(link.evidence_id)
                for link in ranked
            )
        ]
        impact = None
        if state.value == "STRENGTHENED":
            impact = "핵심 가정을 지지하는 신규 증거가 확인되었습니다."
        elif state.value == "WEAKENED":
            impact = "핵심 가정에 반하는 직접 증거가 확인되었습니다."
        elif state.value == "REVIEW_REQUIRED":
            impact = "사용자가 설정한 재검토 조건 충족 가능성이 확인되었습니다. 재검토 필요는 매도 신호가 아닙니다."
        elif state.value == "WATCH":
            impact = "관찰이 필요한 초기 신호입니다."
        elif state.value == "HOLD":
            impact = "증거 충돌 또는 정보 부족으로 판단을 보류합니다."
        opposing = opposing_by_stock.get(card_stock, [])
        next_checks = ([el.text for el in card.tracked_indicators] if card else []) or [
            "기존 추적 항목 재확인"
        ]
        return StockBriefing(
            stock_code=card_stock,
            stock_name=item.stock_name if item else card_stock,
            kind=kind.value,
            state=state,
            facts=tuple(redact_injections(f) for f in facts),
            thesis_impact=impact,
            opposing_notes=(tuple(f"반대 증거 존재: {', '.join(opposing)}") if opposing else ()),
            next_check_items=tuple(next_checks),
            source_ids=tuple(
                dict.fromkeys(
                    sid
                    for kc in key_changes
                    if kc.stock_code == card_stock
                    for sid in kc.source_ids
                )
            ),
        )

    holdings = [
        stock_briefing(p.stock_code, p.kind)
        for p in pack.portfolio
        if p.kind == PositionKind.HOLDING and p.stock_code in cards
    ]
    watchlist = [
        stock_briefing(p.stock_code, p.kind)
        for p in pack.portfolio
        if p.kind == PositionKind.WATCH and p.stock_code in cards
    ]

    hold_items = list(validation.questions)
    for d in final_decisions:
        if d.new_state.value == "HOLD":
            hold_items.append(f"{d.stock_code}: " + ("; ".join(d.hold_reasons) or "판단 보류"))

    unconfirmed = [s.source_id for s in pack.today_sources if s.tier == SourceTier.D]
    tier_d_texts = [
        f"source {sid}의 미확인 정보는 상태 판정에서 제외되었습니다." for sid in unconfirmed
    ]

    official = sum(1 for s in pack.today_sources if s.tier == SourceTier.A)
    secondary = sum(1 for s in pack.today_sources if s.tier == SourceTier.B)
    total_docs = sum(len(e.member_source_ids) for e in events)
    duplicates_merged = max(total_docs - len(events), 0)

    info_quality = InfoQuality(
        official_sources=official,
        trusted_secondary=secondary,
        duplicates_merged=duplicates_merged,
        excluded_unconfirmed=len(unconfirmed),
        data_as_of=pack.briefing_as_of,
    )

    report = BriefingReport(
        briefing_id=make_briefing_id(pack.briefing_as_of.isoformat(), draft.headline),
        as_of=pack.briefing_as_of,
        headline=draft.headline,
        no_change=not key_changes,
        key_changes=tuple(key_changes),
        holdings=tuple(holdings),
        watchlist=tuple(watchlist),
        common_risks=tuple(risk_briefs),
        hold_items=tuple(hold_items),
        unconfirmed_trends=tuple(tier_d_texts),
        info_quality=info_quality,
        claims=tuple(draft_claims),
    )

    from thesisguard.application.briefing_composer import render_markdown

    markdown = render_markdown(report)

    excluded: list[ExclusionRecord] = []
    for event in events:
        novelty = novelty_by_key.get(event.event_key, Novelty.NEW)
        if novelty in {Novelty.REPEAT, Novelty.RESURFACED}:
            excluded.append(
                ExclusionRecord(
                    subject=event.event_key,
                    reason=f"{novelty.value}: 핵심 변화에서 제외",
                )
            )
        related_links = [link for link in links if link.event_key == event.event_key]
        if all(link.relevance is Relevance.UNRELATED for link in related_links) and related_links:
            excluded.append(
                ExclusionRecord(subject=event.event_key, reason="UNRELATED: 투자논지와 무관")
            )

    ledger = AuditLedger(
        briefing_as_of=pack.briefing_as_of,
        sources_used=tuple(dict.fromkeys(s.source_id for s in pack.today_sources)),
        issues=tuple(validation.errors) or (),
        questions=tuple(validation.questions),
        events_created=tuple(
            EventAudit(
                event_key=e.event_key,
                representative_source_id=e.representative_source_id,
                member_source_ids=e.member_source_ids,
                novelty=novelty_by_key.get(e.event_key, Novelty.NEW).value,
                issuer=e.issuer,
                action=e.action,
            )
            for e in events
        ),
        excluded=tuple(excluded),
        mappings=tuple(link.model_dump(mode="json") for link in links),
        state_changes=tuple(d.model_dump(mode="json") for d in final_decisions),
        skeptic_passed=review.passed,
        skeptic_findings=tuple(f.model_dump() for f in review.findings),
        injection_flags=injection_flags,
    )

    return OrchestratorResult(
        report=report,
        markdown=markdown,
        audit=ledger,
        used_sources=list(pack.today_sources),
        validation_issues=tuple(validation.errors) + tuple(validation.questions),
    )


class Orchestrator:
    def __init__(self, engine: AnalysisEngine | None = None) -> None:
        self.engine = engine or FixtureAnalysisEngine()

    def run(self, pack: DailyEvidencePack) -> OrchestratorResult:
        return run_analysis(pack, self.engine)


_POLARITY_FALLBACK = PolarityHint.UNKNOWN
