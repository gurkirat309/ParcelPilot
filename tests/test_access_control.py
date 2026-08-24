"""Rule 4: a customer session can physically only see its own account's rows,
and the model cannot widen scope by supplying an account_id."""

from __future__ import annotations

import pytest

from src.data.repository import AccessError, Repository, Session


@pytest.fixture
def repo() -> Repository:
    return Repository()


def test_customer_cannot_read_other_account_order(repo: Repository):
    cust1 = Session("customer", "ACCT-001")
    # ORD-2001 belongs to ACCT-002 -> invisible to ACCT-001 (returns None).
    assert repo.get_order(cust1, "ORD-2001") is None
    # Own order is visible.
    assert repo.get_order(cust1, "ORD-1001") is not None


def test_customer_listing_is_pinned_to_own_account(repo: Repository):
    cust2 = Session("customer", "ACCT-002")
    # Even asking for another account's orders returns only the session's own.
    orders = repo.list_orders(cust2, account_id="ACCT-001")
    assert orders and all(o.account_id == "ACCT-002" for o in orders)


def test_customer_cannot_read_other_account_ticket(repo: Repository):
    cust3 = Session("customer", "ACCT-003")
    assert repo.get_ticket(cust3, "TKT-501") is None  # ACCT-001's ticket
    # Asking for another account's record returns the caller's OWN account,
    # never the requested one — the model cannot widen scope.
    acct = repo.get_account(cust3, "ACCT-001")
    assert acct is not None and acct.account_id == "ACCT-003"


def test_internal_ops_has_broad_read(repo: Repository):
    ops = Session("internal_ops", None)
    assert len(repo.list_orders(ops)) == 6
    assert len(repo.list_tickets(ops)) == 7
    assert repo.get_order(ops, "ORD-2001") is not None


def test_customer_session_requires_account():
    with pytest.raises(AccessError):
        Session("customer", None)
