"""Novelty classification (Step 4): NEW / UPDATE / REPEAT / RESURFACED.

REPEAT and RESURFACED events are excluded from core changes downstream.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from thesisguard.domain.enums import Novelty
from thesisguard.domain.events import NormalizedEvent
from thesisguard.domain.state import PreviousState

RESURFACE_WINDOW_DAYS = 3


def classify_novelty(
    event: NormalizedEvent,
    previous_state: PreviousState | None,
    briefing_as_of: datetime,
) -> Novelty:
    known = previous_state.known_event_keys if previous_state else ()
    if event.event_key in known:
        return Novelty.REPEAT
    base_keys = {key.split(":")[0] for key in known}
    if event.base_key in base_keys:
        return Novelty.UPDATE
    last_briefing = previous_state.last_briefing_at if previous_state else None
    if (
        last_briefing is not None
        and event.event_date <= briefing_as_of - timedelta(days=RESURFACE_WINDOW_DAYS)
        and event.event_date <= last_briefing
    ):
        return Novelty.RESURFACED
    return Novelty.NEW
