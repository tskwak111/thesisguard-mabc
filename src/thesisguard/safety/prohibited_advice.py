"""Prohibited financial advice filter (KR + EN, including common euphemisms)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from thesisguard.safety.policy import PROHIBITED_PATTERNS, ProhibitionCategory, is_allowlisted


@dataclass(frozen=True)
class ProhibitedHit:
    category: ProhibitionCategory
    matched_text: str
    line: str


def scan_prohibited_advice(text: str) -> list[ProhibitedHit]:
    hits: list[ProhibitedHit] = []
    for line in text.splitlines():
        if is_allowlisted(line):
            continue
        for category, pattern in PROHIBITED_PATTERNS:
            match = re.search(pattern, line)
            if match:
                hits.append(
                    ProhibitedHit(
                        category=category,
                        matched_text=match.group(0),
                        line=line.strip(),
                    )
                )
    return hits


def assert_no_prohibited_advice(text: str) -> None:
    hits = scan_prohibited_advice(text)
    if hits:
        details = ", ".join(f"{h.category.value}:{h.matched_text!r}" for h in hits[:5])
        raise SafetyViolationError(f"prohibited financial advice detected in output: {details}")


class SafetyViolationError(Exception):
    pass
