"""Integration tests for the evaluation harness."""

from __future__ import annotations

from pathlib import Path

import pytest

from thesisguard.evaluation.runner import run_evaluation

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "evaluation" / "dataset"
GOLD = ROOT / "evaluation" / "gold"


@pytest.fixture(scope="module")
def summary():
    return run_evaluation(DATASET, GOLD)


class TestEvaluationHarness:
    def test_sample_count_matches_dataset(self, summary) -> None:
        assert summary.sample_count == 9

    def test_hard_gates_all_pass(self, summary) -> None:
        assert summary.claim_source_linkage_rate == 1.0
        assert summary.fabricated_source_count == 0
        assert summary.prohibited_advice_count == 0
        assert summary.injection_leak_count == 0
        assert summary.state_agreement_rate >= 0.85

    def test_core_event_metrics_meet_prelim_targets(self, summary) -> None:
        assert summary.core_event_precision is not None and summary.core_event_precision >= 0.90
        assert summary.core_event_recall is not None and summary.core_event_recall >= 0.85

    def test_dedup_accuracy(self, summary) -> None:
        assert summary.dedup_case_accuracy == 1.0

    def test_targets_met_report(self, summary) -> None:
        targets = summary.targets_met()
        assert all(targets.values()), targets
