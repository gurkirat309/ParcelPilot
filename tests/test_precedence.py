"""Precedence resolver: contracts scope-gate to their own account; everyone else
falls through to current global policy."""

from __future__ import annotations

from src.domain.policy import Severity
from src.domain.precedence import (
    resolve_cancellation,
    resolve_credit,
    resolve_sla,
)


def test_contract_scope_gated_to_owning_account():
    # Northstar waiver applies only to ACCT-001.
    assert resolve_cancellation("ACCT-001").terms.waive_before_pickup is True
    assert resolve_cancellation("ACCT-003").terms.waive_before_pickup is False
    assert resolve_cancellation("ACCT-004").terms.waive_before_pickup is False


def test_credit_overrides():
    # LumenWorks flat 300 @ 4h; default pct-capped @ 2h; Northstar default + cap.
    assert resolve_credit("ACCT-002").terms.kind == "flat"
    assert resolve_credit("ACCT-002").terms.threshold_hours == 4
    assert resolve_credit("ACCT-003").terms.kind == "pct_capped"
    assert resolve_credit("ACCT-003").terms.monthly_cap_inr is None
    assert resolve_credit("ACCT-001").terms.monthly_cap_inr == 5000


def test_sla_contract_vs_plan():
    # Northstar P1 = 15 min (contract) beats Enterprise v3 default 30 min.
    r = resolve_sla("ACCT-001", "Enterprise", Severity.P1)
    assert r.winning_source == "contract" and r.terms.value == 15
    # Axis Labs (ACCT-004, Enterprise, no contract) -> v3 default 30 min.
    r2 = resolve_sla("ACCT-004", "Enterprise", Severity.P1)
    assert r2.winning_source == "current_policy" and r2.terms.value == 30
    # LumenWorks coverage restriction present even though numbers match v3.
    r3 = resolve_sla("ACCT-002", "Growth", Severity.P1)
    assert r3.winning_source == "contract"
    assert r3.terms.coverage == "no_weekend_after_hours"
