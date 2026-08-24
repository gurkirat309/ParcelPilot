"""Timestamp parsing against the frozen clock.

Workbook timestamps are naive strings (no offset); we interpret them as
Asia/Kolkata to match the snapshot (DATA_SCHEMA data-quality note #4). "Now" is
always the frozen snapshot — never the wall clock (Rule 3).
"""

from __future__ import annotations

from datetime import datetime

from src.config import SNAPSHOT_AT, SNAPSHOT_TZ

_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M")


def parse_ts(value: str | datetime | None) -> datetime | None:
    """Parse a workbook timestamp to a tz-aware datetime (Asia/Kolkata)."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=SNAPSHOT_TZ)
    text = str(value).strip()
    for fmt in _FORMATS:
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=SNAPSHOT_TZ)
        except ValueError:
            continue
    raise ValueError(f"Unrecognised timestamp: {value!r}")


def hours_between(start: datetime, end: datetime) -> float:
    """Signed hours from start to end."""
    return (end - start).total_seconds() / 3600.0


def minutes_between(start: datetime, end: datetime) -> float:
    return (end - start).total_seconds() / 60.0


def snapshot() -> datetime:
    """The frozen 'now'."""
    return SNAPSHOT_AT
