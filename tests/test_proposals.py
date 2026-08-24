"""Proposal store: pending on create, executes only on confirm, scoped by account."""

from __future__ import annotations

import pytest

from src.agent.proposals import ProposalStore


def test_create_is_pending_then_confirm_executes():
    store = ProposalStore()
    p = store.create("escalation", "ACCT-001", "customer", "Escalate X", {"reason": "x"})
    assert p.status == "pending" and p.result is None
    confirmed = store.confirm(p.id, account_id="ACCT-001", is_internal=False)
    assert confirmed.status == "confirmed" and confirmed.result["executed"] is True


def test_cannot_confirm_another_accounts_proposal():
    store = ProposalStore()
    p = store.create("ticket_update", "ACCT-001", "customer", "Update", {})
    with pytest.raises(PermissionError):
        store.confirm(p.id, account_id="ACCT-002", is_internal=False)


def test_double_confirm_rejected():
    store = ProposalStore()
    p = store.create("followup_task", "ACCT-002", "customer", "Task", {})
    store.confirm(p.id, account_id="ACCT-002", is_internal=False)
    with pytest.raises(ValueError):
        store.confirm(p.id, account_id="ACCT-002", is_internal=False)


def test_internal_can_confirm_any():
    store = ProposalStore()
    p = store.create("escalation", "ACCT-003", "customer", "Escalate", {})
    confirmed = store.confirm(p.id, account_id=None, is_internal=True)
    assert confirmed.status == "confirmed"
