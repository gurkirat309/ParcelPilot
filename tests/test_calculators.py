"""Deterministic calculators — encodes the worked cases in SOURCE_MAP §5.

Values here are derived from the source clauses, not copied from any example
answer key; the order rows they mirror are loaded at runtime elsewhere.
"""

from __future__ import annotations

from src.domain.calculators import (
    bulk_upload_check,
    cancellation_fee,
    service_credit,
    sla_first_response,
)
from src.domain.policy import Severity
from src.domain.precedence import resolve_cancellation, resolve_credit, resolve_sla
from src.domain.timeutil import parse_ts

# --- Cancellation -------------------------------------------------------------

def test_northstar_waiver_no_fee_even_after_2h():
    terms = resolve_cancellation("ACCT-001").terms
    r = cancellation_fee(
        "BOOKED", parse_ts("2026-08-16 09:00"), terms,
        requested_at=parse_ts("2026-08-16 11:00"),  # 120 min later
    )
    assert r.cancellable and r.fee_inr == 0


def test_default_fee_after_30_min():
    terms = resolve_cancellation("ACCT-002").terms  # no waiver
    r = cancellation_fee(
        "BOOKED", parse_ts("2026-08-16 09:00"), terms,
        requested_at=parse_ts("2026-08-16 10:15"),  # 75 min later
    )
    assert r.cancellable and r.fee_inr == 250


def test_no_fee_within_window():
    terms = resolve_cancellation("ACCT-003").terms
    r = cancellation_fee(
        "BOOKED", parse_ts("2026-08-16 10:25"), terms,
        requested_at=parse_ts("2026-08-16 10:40"),  # 15 min later
    )
    assert r.fee_inr == 0


def test_picked_up_not_cancellable():
    terms = resolve_cancellation("ACCT-001").terms
    r = cancellation_fee("PICKED_UP", parse_ts("2026-08-16 08:10"), terms)
    assert not r.cancellable and r.route == "return_to_origin"


def test_delivered_not_cancellable():
    terms = resolve_cancellation("ACCT-004").terms
    r = cancellation_fee("DELIVERED", parse_ts("2026-08-14 14:00"), terms)
    assert not r.cancellable and r.fee_inr == 0


# --- Service credit -----------------------------------------------------------

def test_lumenworks_flat_credit_over_4h():
    # ORD-2002: window end 06:30, still not picked up at snapshot 11:00 = 4.5h.
    terms = resolve_credit("ACCT-002").terms
    r = service_credit(
        pickup_window_end=parse_ts("2026-08-16 06:30"),
        carrier_fault=True, customer_fault=False, shipment_fee_inr=2400,
        terms=terms, pickup_actual_at=None,
    )
    assert r.eligible and r.amount_inr == 300 and not r.needs_approval


def test_default_pct_capped_credit():
    # Same facts under the DEFAULT SOP: >2h met, min(500, 10% of 2400=240)=240.
    terms = resolve_credit("ACCT-003").terms
    r = service_credit(
        pickup_window_end=parse_ts("2026-08-16 06:30"),
        carrier_fault=True, customer_fault=False, shipment_fee_inr=2400,
        terms=terms,
    )
    assert r.eligible and r.amount_inr == 240


def test_credit_capped_at_500():
    terms = resolve_credit("ACCT-003").terms
    r = service_credit(
        pickup_window_end=parse_ts("2026-08-16 06:30"),
        carrier_fault=True, customer_fault=False, shipment_fee_inr=9000,  # 10%=900>500
        terms=terms,
    )
    assert r.amount_inr == 500


def test_not_eligible_when_carrier_not_at_fault():
    terms = resolve_credit("ACCT-003").terms
    r = service_credit(
        pickup_window_end=parse_ts("2026-08-16 06:30"),
        carrier_fault=False, customer_fault=False, shipment_fee_inr=2400, terms=terms,
    )
    assert not r.eligible and r.amount_inr == 0


def test_credit_needs_verification_when_unknown():
    terms = resolve_credit("ACCT-003").terms
    r = service_credit(
        pickup_window_end=parse_ts("2026-08-16 06:30"),
        carrier_fault=None, customer_fault=False, shipment_fee_inr=2400, terms=terms,
    )
    assert r.needs_verification and not r.eligible


def test_northstar_monthly_cap_clamps():
    terms = resolve_credit("ACCT-001").terms  # default formula + 5000 cap
    r = service_credit(
        pickup_window_end=parse_ts("2026-08-16 06:30"),
        carrier_fault=True, customer_fault=False, shipment_fee_inr=4000,  # 10%=400
        terms=terms, month_to_date_credit_inr=4800,  # only 200 left
    )
    assert r.amount_inr == 200


# --- SLA ----------------------------------------------------------------------

def test_northstar_p1_breached():
    # TKT-501: created 10:30, snapshot 11:00 = 30 min vs 15-min 24x7 target.
    target = resolve_sla("ACCT-001", "Enterprise", Severity.P1).terms
    r = sla_first_response(target, created_at=parse_ts("2026-08-16 10:30"))
    assert r.computable and r.breached is True


def test_business_hours_sla_indeterminate():
    # Growth P3 is in business days -> not exactly computable (calendar undefined).
    target = resolve_sla("ACCT-002", "Growth", Severity.P3).terms
    r = sla_first_response(target, created_at=parse_ts("2026-08-16 09:00"))
    assert not r.computable and r.breached is None


# --- Bulk upload --------------------------------------------------------------

def test_bulk_upload_ki208_advisory():
    r = bulk_upload_check("Growth", 4200)
    assert r.available and r.within_supported and r.ki208_advisory


def test_bulk_upload_standard_not_available():
    r = bulk_upload_check("Standard", 1000)
    assert not r.available


def test_bulk_upload_over_limit():
    r = bulk_upload_check("Enterprise", 6000)
    assert r.available and not r.within_supported
