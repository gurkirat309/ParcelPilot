"""SQLite schema + idempotent ingest from data/extracted/*.csv.

Timestamps are stored as their raw naive strings; parsing to tz-aware datetimes
against the frozen snapshot happens in the domain layer (timeutil.parse_ts).
Booleans and the fee are cast to real types here.
"""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from src.config import DB_PATH, EXTRACTED, ROOT

SYNTHETIC = ROOT / "data" / "synthetic"

SCHEMA = """
CREATE TABLE accounts (
    account_id      TEXT PRIMARY KEY,
    account_name    TEXT NOT NULL,
    plan            TEXT NOT NULL,
    status          TEXT NOT NULL,
    csm             TEXT,
    contract_file   TEXT,
    premium_support INTEGER NOT NULL,
    notes           TEXT
);
CREATE TABLE orders (
    order_id                  TEXT PRIMARY KEY,
    account_id                TEXT NOT NULL REFERENCES accounts(account_id),
    carrier                   TEXT,
    status                    TEXT NOT NULL,
    booked_at                 TEXT,
    pickup_window_start       TEXT,
    pickup_window_end         TEXT,
    pickup_actual_at          TEXT,
    shipment_fee_inr          INTEGER NOT NULL,
    carrier_fault             INTEGER NOT NULL,
    customer_fault            INTEGER NOT NULL,
    cancellation_requested_at TEXT,
    notes                     TEXT
);
CREATE TABLE tickets (
    ticket_id                TEXT PRIMARY KEY,
    account_id               TEXT NOT NULL REFERENCES accounts(account_id),
    created_at               TEXT,
    status                   TEXT NOT NULL,
    subject                  TEXT,
    description              TEXT,
    channel                  TEXT,
    assigned_to              TEXT,
    last_customer_message_at TEXT,
    historical_resolution    TEXT,
    -- 0 = real corpus (authority). 1 = synthetic, ANALYTICS-ONLY (Problem 1 ops
    -- board). The repository (customer/internal agent) only ever reads is_synthetic=0.
    is_synthetic             INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_orders_account ON orders(account_id);
CREATE INDEX idx_tickets_account ON tickets(account_id);
"""


def _clean(value: str) -> str | None:
    v = value.strip()
    return v if v not in ("", "nan", "NaN", "None") else None


def _to_bool(value: str) -> int:
    return 1 if _clean(value) in ("True", "true", "1") else 0


def _rows(name: str) -> list[dict[str, str]]:
    path = EXTRACTED / f"{name}.csv"
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _load_synthetic() -> list[tuple]:
    """Optional synthetic tickets (ANALYTICS ONLY) from data/synthetic/."""
    path = SYNTHETIC / "tickets_synthetic.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    return [
        (
            r["ticket_id"], r["account_id"], _clean(r["created_at"]), r["status"],
            _clean(r["subject"]), _clean(r["description"]), _clean(r["channel"]),
            _clean(r["assigned_to"]), _clean(r["last_customer_message_at"]),
            _clean(r.get("historical_resolution", "")),
        )
        for r in rows
    ]


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def ingest(db_path: Path = DB_PATH) -> dict[str, int]:
    """(Re)build the SQLite DB from the extracted CSVs. Returns row counts."""
    if db_path.exists():
        db_path.unlink()
    conn = connect(db_path)
    try:
        conn.executescript(SCHEMA)

        accounts = [
            (
                r["account_id"], r["account_name"], r["plan"], r["status"],
                _clean(r["csm"]), _clean(r["contract_file"]),
                _to_bool(r["premium_support"]), _clean(r["notes"]),
            )
            for r in _rows("accounts")
        ]
        conn.executemany(
            "INSERT INTO accounts VALUES (?,?,?,?,?,?,?,?)", accounts)

        orders = [
            (
                r["order_id"], r["account_id"], _clean(r["carrier"]), r["status"],
                _clean(r["booked_at"]), _clean(r["pickup_window_start"]),
                _clean(r["pickup_window_end"]), _clean(r["pickup_actual_at"]),
                int(float(r["shipment_fee_inr"])),
                _to_bool(r["carrier_fault"]), _to_bool(r["customer_fault"]),
                _clean(r["cancellation_requested_at"]), _clean(r["notes"]),
            )
            for r in _rows("orders")
        ]
        conn.executemany(
            "INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", orders)

        tickets = [
            (
                r["ticket_id"], r["account_id"], _clean(r["created_at"]),
                r["status"], _clean(r["subject"]), _clean(r["description"]),
                _clean(r["channel"]), _clean(r["assigned_to"]),
                _clean(r["last_customer_message_at"]),
                _clean(r["historical_resolution"]), 0,
            )
            for r in _rows("tickets")
        ]
        conn.executemany(
            "INSERT INTO tickets VALUES (?,?,?,?,?,?,?,?,?,?,?)", tickets)

        synthetic = _load_synthetic()
        if synthetic:
            conn.executemany(
                "INSERT INTO tickets VALUES (?,?,?,?,?,?,?,?,?,?,1)", synthetic)

        conn.commit()
        return {"accounts": len(accounts), "orders": len(orders),
                "tickets": len(tickets), "synthetic_tickets": len(synthetic)}
    finally:
        conn.close()


if __name__ == "__main__":
    counts = ingest()
    print("Ingested:", counts, "->", DB_PATH)
