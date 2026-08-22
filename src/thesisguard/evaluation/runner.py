"""Evaluation runner: run every dataset pack, compare with gold labels, compute metrics."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from thesisguard.adapters.fixture_analysis_engine import FixtureAnalysisEngine
from thesisguard.application.input_validation import parse_pack
from thesisguard.application.orchestrator import run_analysis
from thesisguard.errors import ThesisGuardError
from thesisguard.evaluation.metrics import MetricSummary
from thesisguard.safety.prohibited_advice import scan_prohibited_advice
from thesisguard.safety.prompt_injection import has_injection

_STRONG = {"STRENGTHENED", "WEAKENED", "REVIEW_REQUIRED"}


def _load_gold(gold_dir: Path, case: str) -> dict[str, Any]:
    path = gold_dir / f"{case}.gold.json"
    if not path.exists():
        return {}
    loaded: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return loaded


def run_evaluation(dataset_dir: Path, gold_dir: Path) -> MetricSummary:
    packs = sorted(dataset_dir.glob("*.json"))
    if not packs:
        raise ThesisGuardError(f"no dataset packs found in {dataset_dir}")

    state_hits = 0
    reasonable_holds = 0
    total_claims = 0
    linked_claims = 0
    fabricated = 0
    prohibited_total = 0
    injection_leaks = 0

    precision_parts: list[tuple[int, int]] = []
    recall_parts: list[tuple[int, int]] = []
    dedup_cases: list[bool] = []
    reduction_rates: list[float] = []
    reading_times: list[float] = []

    for pack_path in packs:
        data = json.loads(pack_path.read_text(encoding="utf-8"))
        gold = _load_gold(gold_dir, pack_path.stem.replace(".daily_evidence_pack", ""))
        result = run_analysis(parse_pack(data), FixtureAnalysisEngine())
        report = result.report.model_dump(mode="json")
        known_sources = {s["source_id"] for s in data.get("today_sources", [])}

        # state agreement (match OR reasonable HOLD on a strong expected state)
        actual_states = {
            sb["stock_code"]: sb["state"] for sb in report["holdings"] + report["watchlist"]
        }
        expected_states: dict[str, str] = gold.get("expected_states", {})
        for code, expected in expected_states.items():
            actual = actual_states.get(code)
            if actual == expected:
                state_hits += 1
            elif actual == "HOLD" and expected in _STRONG:
                state_hits += 1
                reasonable_holds += 1

        # claim linkage / fabricated sources
        claims = report["claims"]
        total_claims += len(claims)
        linked_claims += sum(1 for c in claims if c["source_ids"])
        fabricated += sum(1 for c in claims for sid in c["source_ids"] if sid not in known_sources)

        md = result.markdown
        prohibited_total += len(scan_prohibited_advice(md))
        if has_injection(md):
            injection_leaks += 1

        # core event precision/recall via action substrings
        core_actions: list[str] = gold.get("core_event_actions", [])
        if core_actions:
            descriptions = [kc["description"] for kc in report["key_changes"]]
            matched = sum(1 for d in descriptions if any(action in d for action in core_actions))
            precision_parts.append((matched, len(descriptions)))
            recalled = sum(1 for action in core_actions if any(action in d for d in descriptions))
            recall_parts.append((recalled, len(core_actions)))

        # dedup accuracy
        if "expected_event_count" in gold:
            actual_events = len(result.audit.events_created)
            dedup_cases.append(actual_events == gold["expected_event_count"])

        # repetition reduction proxy: key changes vs input documents
        docs = len(data.get("today_sources", []))
        if docs:
            reduction_rates.append(1.0 - len(report["key_changes"]) / docs)

        reading_times.append(max(len(md) / 1000.0, 0.1))

    def ratio(parts: list[tuple[int, int]]) -> float | None:
        tp = sum(p[0] for p in parts)
        n = sum(p[1] for p in parts)
        return round(tp / n, 4) if n else None

    samples = len(packs)
    expected_total = sum(
        len(
            _load_gold(gold_dir, p.stem.replace(".daily_evidence_pack", "")).get(
                "expected_states", {}
            )
        )
        for p in packs
    )
    return MetricSummary(
        sample_count=samples,
        state_agreement_rate=(round(state_hits / expected_total, 4) if expected_total else 1.0),
        reasonable_hold_accepted=reasonable_holds,
        claim_source_linkage_rate=round(linked_claims / total_claims, 4) if total_claims else 1.0,
        fabricated_source_count=fabricated,
        prohibited_advice_count=prohibited_total,
        injection_leak_count=injection_leaks,
        core_event_precision=ratio(precision_parts),
        core_event_recall=ratio(recall_parts),
        dedup_case_accuracy=(
            round(sum(dedup_cases) / len(dedup_cases), 4) if dedup_cases else None
        ),
        repetition_reduction_rate=(
            round(sum(reduction_rates) / len(reduction_rates), 4) if reduction_rates else None
        ),
        avg_reading_time_minutes=(
            round(sum(reading_times) / len(reading_times), 2) if reading_times else None
        ),
    )
