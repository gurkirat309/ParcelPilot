"""Deterministic calculators (Rule 6). The model never does this arithmetic and
never decides eligibility — it calls these and reports the result.

Each function is pure: primitive inputs in, a typed result (with citations) out.
The tool layer fetches DB rows and resolves precedence, then calls these.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .money import pct_of
from .policy import (
    BULK_UPLOAD,
    BulkUploadPolicy,
    CancellationTerms,
    Citation,
    CreditTerms,
    SlaTarget,
)
from .timeutil import hours_between, minutes_between, snapshot

# --- CALC-1: cancellation fee -------------------------------------------------

@dataclass(frozen=True)
class CancellationResult:
    cancellable: bool
    fee_inr: int
    reason: str
    route: str | None                 # e.g. "return_to_origin" for PICKED_UP
    citations: list[Citation] = field(default_factory=list)


def cancellation_fee(
    status: str,
    booked_at: datetime,
    terms: CancellationTerms,
    requested_at: datetime | None = None,
) -> CancellationResult:
    """Fee to cancel an order. `requested_at` defaults to the frozen snapshot."""
    at = requested_at or snapshot()
    status = status.upper()
    cite = [terms.cite]

    if status == "DRAFT":
        return CancellationResult(True, 0, "DRAFT orders cancel free.", None, cite)
    if status == "PICKED_UP":
        return CancellationResult(
            False, 0,
            "Order already PICKED_UP; cannot cancel. Use return-to-origin.",
            "return_to_origin", cite,
        )
    if status == "DELIVERED":
        return CancellationResult(
            False, 0, "Order already DELIVERED; cannot cancel.", None, cite)
    if status != "BOOKED":
        return CancellationResult(
            False, 0, f"Unknown order status {status!r}; escalate.", None, cite)

    # BOOKED, not yet picked up.
    if terms.waive_before_pickup:
        return CancellationResult(
            True, 0,
            "Customer contract waives the cancellation fee for any BOOKED "
            "shipment before pickup, regardless of elapsed time.",
            None, cite,
        )
    elapsed_min = minutes_between(booked_at, at)
    if elapsed_min <= terms.free_window_minutes:
        return CancellationResult(
            True, 0,
            f"Cancelled {elapsed_min:.0f} min after booking, within the "
            f"{terms.free_window_minutes}-min free window.",
            None, cite,
        )
    return CancellationResult(
        True, terms.fee_inr,
        f"Cancelled {elapsed_min:.0f} min after booking, past the "
        f"{terms.free_window_minutes}-min free window; fee applies.",
        None, cite,
    )


# --- CALC-2: failed-pickup service credit -------------------------------------

@dataclass(frozen=True)
class CreditResult:
    eligible: bool
    amount_inr: int
    needs_approval: bool
    needs_verification: bool
    delay_hours: float | None
    basis: str
    citations: list[Citation] = field(default_factory=list)


def service_credit(
    pickup_window_end: datetime,
    carrier_fault: bool | None,
    customer_fault: bool | None,
    shipment_fee_inr: int,
    terms: CreditTerms,
    pickup_actual_at: datetime | None = None,
    month_to_date_credit_inr: int = 0,
) -> CreditResult:
    """Failed-pickup credit. If not yet picked up, delay is measured to snapshot."""
    cite = [terms.cite]

    # Don't promise when fault/timing is unknown (SOP §3).
    if carrier_fault is None or customer_fault is None:
        return CreditResult(
            False, 0, False, True, None,
            "Carrier fault or customer fault is unknown; verify before promising.",
            cite,
        )

    end_ref = pickup_actual_at or snapshot()
    delay_h = hours_between(pickup_window_end, end_ref)

    eligible = delay_h > terms.threshold_hours and carrier_fault and not customer_fault
    if not eligible:
        why = []
        if not (delay_h > terms.threshold_hours):
            why.append(f"delay {delay_h:.2f}h ≤ {terms.threshold_hours}h threshold")
        if not carrier_fault:
            why.append("carrier not at fault")
        if customer_fault:
            why.append("customer at fault")
        return CreditResult(
            False, 0, False, False, delay_h,
            "Not eligible: " + "; ".join(why) + ".", cite,
        )

    if terms.kind == "flat":
        amount = int(terms.flat_amount_inr or 0)
    else:  # pct_capped
        raw = pct_of(shipment_fee_inr, terms.pct or 0)
        cap = terms.per_incident_cap_inr
        amount = min(raw, cap) if cap is not None else raw

    basis = (
        f"Eligible: delay {delay_h:.2f}h > {terms.threshold_hours}h, carrier at "
        f"fault, no customer fault. "
    )
    if terms.kind == "flat":
        basis += f"Flat contract credit {terms.flat_amount_inr}."
    else:
        basis += f"lower of {terms.per_incident_cap_inr} or {terms.pct}% of {shipment_fee_inr}."

    # Monthly aggregate cap (e.g. Northstar).
    if terms.monthly_cap_inr is not None:
        remaining = max(0, terms.monthly_cap_inr - month_to_date_credit_inr)
        if amount > remaining:
            basis += (
                f" Clamped to monthly aggregate cap {terms.monthly_cap_inr} "
                f"(month-to-date {month_to_date_credit_inr}, remaining {remaining})."
            )
            amount = remaining

    needs_approval = amount > terms.manager_approval_over_inr
    return CreditResult(
        eligible=True,
        amount_inr=amount,
        needs_approval=needs_approval,
        needs_verification=False,
        delay_hours=delay_h,
        basis=basis,
        citations=cite,
    )


# --- CALC-3: first-response SLA target + breach -------------------------------

@dataclass(frozen=True)
class SlaResult:
    target_value: int
    target_unit: str
    coverage: str
    elapsed_minutes: float
    breached: bool | None       # None when not exactly computable
    computable: bool
    reason: str
    citations: list[Citation] = field(default_factory=list)


def sla_first_response(
    target: SlaTarget,
    created_at: datetime,
    responded_at: datetime | None = None,
) -> SlaResult:
    """Breach check. Only clock-time 24x7 targets are exactly computable now;
    business-hours targets are flagged indeterminate (calendar undefined)."""
    ref = responded_at or snapshot()
    elapsed_min = minutes_between(created_at, ref)
    cite = [target.cite]

    if target.unit in ("minutes", "hours") and target.coverage == "24x7":
        target_min = target.value * (60 if target.unit == "hours" else 1)
        breached = elapsed_min > target_min
        reason = (
            f"{elapsed_min:.0f} min elapsed vs {target_min} min target "
            f"({'BREACHED' if breached else 'within target'})."
        )
        return SlaResult(target.value, target.unit, target.coverage,
                         elapsed_min, breached, True, reason, cite)

    return SlaResult(
        target.value, target.unit, target.coverage, elapsed_min, None, False,
        "Not exactly computable: target is stated in "
        f"{target.unit} with '{target.coverage}' coverage, and the business-hours "
        "calendar is undefined in the sources (see OPEN QUESTIONS). Elapsed clock "
        f"time is {elapsed_min:.0f} min; escalate for a human SLA judgement.",
        cite,
    )


# --- CALC-4: bulk-upload advisory (lookup, not arithmetic) --------------------

@dataclass(frozen=True)
class BulkUploadResult:
    available: bool
    supported_max_rows: int
    within_supported: bool
    ki208_advisory: bool
    message: str
    citations: list[Citation] = field(default_factory=list)


def bulk_upload_check(
    plan: str, rows: int, policy: BulkUploadPolicy = BULK_UPLOAD
) -> BulkUploadResult:
    cites = [policy.cite]
    if plan not in policy.plans_with_access:
        return BulkUploadResult(
            False, policy.supported_max_rows, False, False,
            f"Bulk Upload is not included on the {plan} plan.", cites,
        )
    within = rows <= policy.supported_max_rows
    ki208 = rows > policy.ki208_advisory_over_rows
    if not within:
        msg = (
            f"{rows} rows exceeds the supported {policy.supported_max_rows}-row limit."
        )
    elif ki208:
        cites.append(policy.ki208_cite)
        msg = (
            f"{rows} rows is within the supported {policy.supported_max_rows}-row "
            f"limit, but above ~{policy.ki208_advisory_over_rows} rows known issue "
            "KI-208 can cause intermittent failures. Workaround: split into files "
            f"below {policy.ki208_advisory_over_rows} rows."
        )
    else:
        msg = f"{rows} rows is fully supported (limit {policy.supported_max_rows})."
    return BulkUploadResult(True, policy.supported_max_rows, within, ki208, msg, cites)
