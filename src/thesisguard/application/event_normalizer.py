"""Deterministic event fingerprinting and deduplication (Step 3 of the pipeline).

A syndicated press release reprinted by N outlets is ONE event with N documents.
Article counts are never treated as independent evidence.
"""

from __future__ import annotations

import hashlib
import re

from thesisguard.domain.enums import PolarityHint, SourceTier
from thesisguard.domain.events import EventCandidate, NormalizedEvent

_TIER_ORDER: dict[SourceTier, int] = {
    SourceTier.A: 0,
    SourceTier.B: 1,
    SourceTier.C: 2,
    SourceTier.D: 3,
}

_WS = re.compile(r"\s+")


def _norm(text: str) -> str:
    return _WS.sub(" ", text.strip()).lower()


def _figure_digest(figures: tuple[str, ...]) -> str:
    digits = "".join("".join(ch for ch in fig if ch.isdigit()) for fig in sorted(figures))
    return hashlib.sha256(digits.encode("utf-8")).hexdigest()[:12]


def _fingerprint_parts(candidate: EventCandidate) -> list[str]:
    return [
        _norm(candidate.issuer),
        candidate.event_type.upper(),
        "|".join(sorted(_norm(e) for e in candidate.entities)),
        candidate.event_date.date().isoformat(),
    ]


def compute_fingerprint(candidate: EventCandidate) -> str:
    return "::".join(_fingerprint_parts(candidate)) + f"::{_figure_digest(candidate.key_figures)}"


def compute_base_key(candidate: EventCandidate) -> str:
    return hashlib.sha256("::".join(_fingerprint_parts(candidate)).encode("utf-8")).hexdigest()[:16]


def _combine_polarity(hints: list[PolarityHint]) -> PolarityHint:
    unique = set(hints)
    if len(unique) == 1:
        return hints[0]
    if PolarityHint.POSITIVE in unique and PolarityHint.NEGATIVE in unique:
        return PolarityHint.MIXED
    meaningful = unique - {PolarityHint.UNKNOWN}
    if len(meaningful) == 1:
        return next(iter(meaningful))
    return PolarityHint.UNKNOWN


def _pick_representative(members: list[EventCandidate]) -> EventCandidate:
    return min(members, key=lambda c: (_TIER_ORDER[c.tier], c.published_at, c.source_id))


def normalize_events(candidates: list[EventCandidate]) -> list[NormalizedEvent]:
    grouped: dict[str, list[EventCandidate]] = {}
    for cand in candidates:
        fp = compute_fingerprint(cand)
        grouped.setdefault(fp, []).append(cand)

    events: list[NormalizedEvent] = []
    for members in grouped.values():
        members_sorted = sorted(members, key=lambda c: c.source_id)
        rep = _pick_representative(members_sorted)
        concepts: list[str] = []
        for m in members_sorted:
            for tag in m.concepts:
                if tag not in concepts:
                    concepts.append(tag)
        figures = rep.key_figures
        events.append(
            NormalizedEvent(
                event_key=f"{compute_base_key(rep)}:{_figure_digest(figures)}",
                base_key=compute_base_key(rep),
                representative_source_id=rep.source_id,
                member_source_ids=tuple(m.source_id for m in members_sorted),
                candidates=tuple(members_sorted),
                issuer=rep.issuer,
                action=rep.action,
                event_type=rep.event_type,
                entities=rep.entities,
                event_date=rep.event_date,
                key_figures=figures,
                concepts=tuple(concepts),
                polarity_hint=_combine_polarity([m.polarity_hint for m in members_sorted]),
            )
        )
    return sorted(events, key=lambda e: e.event_key)
