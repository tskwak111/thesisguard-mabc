"""Prompt-injection defense: external document text is DATA, never instructions."""

from __future__ import annotations

import re
from re import Pattern

_INJECTION_PATTERNS: tuple[Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"이전\s?지시를?\s?무시",
        r"지시를?\s?무시하고",
        r"무시하고.{0,20}출력",
        r"강력\s?매수",
        r"출력하라",
        r"ignore\s+previous\s+instructions?",
        r"disregard\s+(all\s+)?(previous|prior)\s+instructions?",
        r"system\s+prompt",
        r"관리자\s?모드",
        r"\[system\]",
        r"규칙을?\s?덮어쓰",
        r"프롬프트를?\s?출",
    ]
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?。])\s+")


def detect_injection_spans(text: str) -> list[str]:
    """Return whole sentences that look like embedded commands."""
    flagged: list[str] = []
    for sentence in _SENTENCE_SPLIT.split(text):
        if any(pattern.search(sentence) for pattern in _INJECTION_PATTERNS):
            flagged.append(sentence.strip())
    return flagged


def has_injection(text: str) -> bool:
    return bool(detect_injection_spans(text))


def redact_injections(text: str) -> str:
    """Remove injected command sentences; keep the rest of the document intact."""
    if not has_injection(text):
        return text
    kept = [
        sentence
        for sentence in _SENTENCE_SPLIT.split(text)
        if not any(p.search(sentence) for p in _INJECTION_PATTERNS)
    ]
    return " ".join(part for part in " ".join(kept).split() if part)
