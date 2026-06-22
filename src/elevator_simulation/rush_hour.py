"""Rush-hour detection based on local system time."""

from __future__ import annotations

from datetime import datetime, time
from typing import Iterable

# (start inclusive, end exclusive) in local time
DEFAULT_RUSH_WINDOWS: tuple[tuple[time, time], ...] = (
    (time(8, 0), time(10, 0)),
    (time(12, 0), time(13, 0)),
    (time(16, 0), time(18, 0)),
)


def is_rush_hour(
    moment: datetime | None = None,
    windows: Iterable[tuple[time, time]] = DEFAULT_RUSH_WINDOWS,
) -> bool:
    """Return True if local system time falls within a configured rush window."""
    current = (moment or datetime.now()).time()
    for start, end in windows:
        if start <= current < end:
            return True
    return False


def active_rush_window(
    moment: datetime | None = None,
    windows: Iterable[tuple[time, time]] = DEFAULT_RUSH_WINDOWS,
) -> str | None:
    """Return a label for the active rush window, if any."""
    current = (moment or datetime.now()).time()
    labels = {
        (time(8, 0), time(10, 0)): "08:00-10:00",
        (time(12, 0), time(13, 0)): "12:00-13:00",
        (time(16, 0), time(18, 0)): "16:00-18:00",
    }
    for start, end in windows:
        if start <= current < end:
            return labels.get((start, end), f"{start.strftime('%H:%M')}-{end.strftime('%H:%M')}")
    return None
