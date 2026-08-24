"""The frozen clock must match the workbook README, and stay frozen."""

from __future__ import annotations

import csv
from datetime import datetime

from src.config import EXTRACTED, SNAPSHOT_AT, SNAPSHOT_TZ


def test_snapshot_matches_readme():
    """SNAPSHOT_AT must equal the 'Dataset snapshot' value in README.csv."""
    readme = EXTRACTED / "README.csv"
    rows = list(csv.reader(readme.open(encoding="utf-8")))
    snapshot_value = None
    for row in rows:
        if row and row[0].strip().lower() == "dataset snapshot":
            snapshot_value = row[1].strip()
            break
    assert snapshot_value == "2026-08-16 11:00 Asia/Kolkata", snapshot_value

    # Reconstruct from the README string and compare to the config constant.
    expected = datetime.strptime("2026-08-16 11:00", "%Y-%m-%d %H:%M").replace(
        tzinfo=SNAPSHOT_TZ
    )
    assert SNAPSHOT_AT == expected


def test_snapshot_is_tz_aware():
    assert SNAPSHOT_AT.tzinfo is not None
