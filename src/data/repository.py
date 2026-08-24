"""Scoped data access — Rule 4: access control lives HERE, in the data layer.

`account_id` is derived from the server-side `Session`, never accepted as a
model/tool parameter. A `customer` session can physically only read its own
account's rows; requesting another account's order/ticket returns None (as if it
does not exist), never another account's data. `internal_ops` has broad read.

Tools call these functions with the trusted Session the server built at auth time.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from .db import connect
from .models import Account, Order, Ticket


class AccessError(PermissionError):
    """Raised when a session attempts an action outside its scope."""


@dataclass(frozen=True)
class Session:
    role: str                 # "customer" | "internal_ops"
    account_id: str | None    # required for customer; None for internal_ops

    def __post_init__(self) -> None:
        if self.role == "customer" and not self.account_id:
            raise AccessError("customer session requires an account_id")
        if self.role not in ("customer", "internal_ops"):
            raise AccessError(f"unknown role: {self.role!r}")

    @property
    def is_internal(self) -> bool:
        return self.role == "internal_ops"


class Repository:
    def __init__(self, conn: sqlite3.Connection | None = None) -> None:
        self._conn = conn or connect()

    # --- scope helper ---------------------------------------------------------
    def _visible_account(self, session: Session, requested: str | None) -> str | None:
        """The account a query is allowed to touch.

        customer: always pinned to their own account (any requested id is ignored,
        so the model can never widen scope). internal_ops: the requested id, or
        None for all-accounts reads.
        """
        if session.role == "customer":
            return session.account_id
        return requested

    # --- accounts -------------------------------------------------------------
    def get_account(self, session: Session, account_id: str | None = None) -> Account | None:
        target = self._visible_account(session, account_id)
        if target is None and not session.is_internal:
            return None
        if target is None:
            return None  # internal must name an account for a single-account read
        row = self._conn.execute(
            "SELECT * FROM accounts WHERE account_id = ?", (target,)
        ).fetchone()
        return _account(row) if row else None

    def list_accounts(self, session: Session) -> list[Account]:
        if not session.is_internal:
            acct = self.get_account(session)
            return [acct] if acct else []
        rows = self._conn.execute("SELECT * FROM accounts ORDER BY account_id").fetchall()
        return [_account(r) for r in rows]

    # --- orders ---------------------------------------------------------------
    def get_order(self, session: Session, order_id: str) -> Order | None:
        row = self._conn.execute(
            "SELECT * FROM orders WHERE order_id = ?", (order_id,)
        ).fetchone()
        if row is None:
            return None
        if session.role == "customer" and row["account_id"] != session.account_id:
            return None  # not found, from this session's perspective
        return _order(row)

    def list_orders(self, session: Session, account_id: str | None = None) -> list[Order]:
        target = self._visible_account(session, account_id)
        if target is not None:
            rows = self._conn.execute(
                "SELECT * FROM orders WHERE account_id = ? ORDER BY order_id", (target,)
            ).fetchall()
        elif session.is_internal:
            rows = self._conn.execute("SELECT * FROM orders ORDER BY order_id").fetchall()
        else:
            rows = []
        return [_order(r) for r in rows]

    # --- tickets --------------------------------------------------------------
    def get_ticket(self, session: Session, ticket_id: str) -> Ticket | None:
        # Real corpus only — synthetic tickets are analytics-only (ops board).
        row = self._conn.execute(
            "SELECT * FROM tickets WHERE ticket_id = ? AND is_synthetic = 0", (ticket_id,)
        ).fetchone()
        if row is None:
            return None
        if session.role == "customer" and row["account_id"] != session.account_id:
            return None
        return _ticket(row)

    def list_tickets(self, session: Session, account_id: str | None = None) -> list[Ticket]:
        target = self._visible_account(session, account_id)
        if target is not None:
            rows = self._conn.execute(
                "SELECT * FROM tickets WHERE account_id = ? AND is_synthetic = 0 "
                "ORDER BY ticket_id", (target,)
            ).fetchall()
        elif session.is_internal:
            rows = self._conn.execute(
                "SELECT * FROM tickets WHERE is_synthetic = 0 ORDER BY ticket_id"
            ).fetchall()
        else:
            rows = []
        return [_ticket(r) for r in rows]


# --- row -> model -------------------------------------------------------------

def _account(r: sqlite3.Row) -> Account:
    return Account(
        r["account_id"], r["account_name"], r["plan"], r["status"], r["csm"],
        r["contract_file"], bool(r["premium_support"]), r["notes"],
    )


def _order(r: sqlite3.Row) -> Order:
    return Order(
        r["order_id"], r["account_id"], r["carrier"], r["status"], r["booked_at"],
        r["pickup_window_start"], r["pickup_window_end"], r["pickup_actual_at"],
        int(r["shipment_fee_inr"]), bool(r["carrier_fault"]), bool(r["customer_fault"]),
        r["cancellation_requested_at"], r["notes"],
    )


def _ticket(r: sqlite3.Row) -> Ticket:
    return Ticket(
        r["ticket_id"], r["account_id"], r["created_at"], r["status"], r["subject"],
        r["description"], r["channel"], r["assigned_to"], r["last_customer_message_at"],
        r["historical_resolution"],
    )
