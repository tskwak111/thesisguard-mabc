"""Analysis engine port. Domain logic never depends on a specific LLM provider."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from thesisguard.domain.events import EventCandidate
from thesisguard.domain.pack import DailyEvidencePack


@runtime_checkable
class AnalysisEngine(Protocol):
    """Extracts structured event candidates from a DailyEvidencePack.

    Implementations: FixtureAnalysisEngine (deterministic reference) and
    PromptAnalysisEngine (LLM-backed, strict JSON contract, opt-in).
    """

    def extract_events(self, pack: DailyEvidencePack) -> list[EventCandidate]: ...
