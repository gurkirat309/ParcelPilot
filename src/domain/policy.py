"""Structured, CITED policy parameters — the machine-readable transcription of
the source clauses that the deterministic calculators consume.

These are not invented policy (Rule 10). Each parameter is a faithful transcription
of a specific clause, carrying a `Citation` (file, page, section, short quote) back
to the source. The raw document text remains the authority the agent quotes to
users; this module only holds the thresholds/amounts the math needs.

Defaults come from the CURRENT global policy/SOP; per-account entries transcribe
the two customer contracts. Everything is keyed by data loaded at runtime
(plan, account_id) — never by hard-coded order IDs or example answers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


@dataclass(frozen=True)
class Citation:
    source_file: str
    page: int
    section: str
    quote: str


class Severity(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


# --- Cancellation fee (SOP v4 §1; Northstar §2) -------------------------------

@dataclass(frozen=True)
class CancellationTerms:
    free_window_minutes: int
    fee_inr: int
    waive_before_pickup: bool  # contract waives the fee entirely before pickup
    cite: Citation


SOP_FILE = "03_Cancellation_and_Service_Credit_SOP_v4.pdf"
NORTHSTAR_FILE = "05_Northstar_Logistics_Enterprise_Agreement.pdf"
LUMENWORKS_FILE = "06_LumenWorks_Service_Agreement.pdf"
POLICY_V3_FILE = "01_Support_Policy_v3_CURRENT.pdf"

DEFAULT_CANCELLATION = CancellationTerms(
    free_window_minutes=30,
    fee_inr=250,
    waive_before_pickup=False,
    cite=Citation(
        SOP_FILE, 1, "§1 Order cancellation",
        "No fee within 30 minutes of booking. After 30 minutes, charge INR 250 "
        "unless a customer agreement explicitly waives the cancellation fee.",
    ),
)

CONTRACT_CANCELLATION: dict[str, CancellationTerms] = {
    "ACCT-001": CancellationTerms(
        free_window_minutes=30,
        fee_inr=250,
        waive_before_pickup=True,
        cite=Citation(
            NORTHSTAR_FILE, 1, "§2 Shipment cancellation",
            "Northstar may cancel any BOOKED shipment before pickup with no "
            "cancellation fee, regardless of how long ago the shipment was booked.",
        ),
    ),
    # LumenWorks (ACCT-002): §2 explicitly declines any waiver -> use SOP default.
}


# --- Failed-pickup service credit (SOP v4 §2/§3; LumenWorks §3; Northstar §3) --

@dataclass(frozen=True)
class CreditTerms:
    kind: str                       # "pct_capped" | "flat"
    threshold_hours: float          # pickup delay past window end to be eligible
    pct: int | None = None          # for pct_capped: percent of shipment fee
    per_incident_cap_inr: int | None = None   # for pct_capped: the cap
    flat_amount_inr: int | None = None        # for flat
    monthly_cap_inr: int | None = None        # aggregate monthly cap (Northstar)
    manager_approval_over_inr: int = 1000     # SOP §3
    cite: Citation = field(
        default=Citation(SOP_FILE, 1, "§2", "")
    )


DEFAULT_CREDIT = CreditTerms(
    kind="pct_capped",
    threshold_hours=2,
    pct=10,
    per_incident_cap_inr=500,
    manager_approval_over_inr=1000,
    cite=Citation(
        SOP_FILE, 1, "§2 Failed-pickup service credits",
        "more than 2 hours past the end of the scheduled pickup window, the "
        "carrier is at fault ... default credit is the lower of INR 500 or 10% "
        "of the shipment fee.",
    ),
)

CONTRACT_CREDIT: dict[str, CreditTerms] = {
    "ACCT-001": CreditTerms(  # default formula + monthly aggregate cap
        kind="pct_capped",
        threshold_hours=2,
        pct=10,
        per_incident_cap_inr=500,
        monthly_cap_inr=5000,
        manager_approval_over_inr=1000,
        cite=Citation(
            NORTHSTAR_FILE, 1, "§3 Service credits",
            "Monthly aggregate service credits are capped at INR 5,000. Unless "
            "this agreement states otherwise, the current ParcelPilot "
            "service-credit SOP applies.",
        ),
    ),
    "ACCT-002": CreditTerms(  # replaces default threshold AND amount
        kind="flat",
        threshold_hours=4,
        flat_amount_inr=300,
        manager_approval_over_inr=1000,
        cite=Citation(
            LUMENWORKS_FILE, 1, "§3 Failed-pickup credits",
            "more than 4 hours past the end ... LumenWorks receives a fixed INR "
            "300 service credit. This clause replaces the default failed-pickup "
            "credit amount and timing threshold in the SOP.",
        ),
    ),
}


# --- First-response SLA targets (v3 §3; Northstar §1; LumenWorks §1) ----------
# unit: "minutes" | "hours" (clock time) | "business_hours" | "business_days".
# coverage: "24x7" | "business" | "no_weekend_after_hours" | "unspecified".
# Only clock-time + 24x7 targets are exactly computable at the snapshot; business
# units are flagged indeterminate (business-hours calendar is undefined — see
# SOURCE_MAP OPEN QUESTIONS #1).

@dataclass(frozen=True)
class SlaTarget:
    value: int
    unit: str
    coverage: str
    cite: Citation


def _v3(sev: str, value: int, unit: str, coverage: str) -> SlaTarget:
    return SlaTarget(value, unit, coverage, Citation(
        POLICY_V3_FILE, 1, "§3 Default first-response targets", f"{sev} default"))


PLAN_SLA: dict[str, dict[Severity, SlaTarget]] = {
    "Enterprise": {
        Severity.P1: _v3("Enterprise P1", 30, "minutes", "24x7"),
        Severity.P2: _v3("Enterprise P2", 2, "hours", "business"),
        Severity.P3: _v3("Enterprise P3", 1, "business_days", "business"),
    },
    "Growth": {
        Severity.P1: _v3("Growth P1", 2, "business_hours", "business"),
        Severity.P2: _v3("Growth P2", 4, "business_hours", "business"),
        Severity.P3: _v3("Growth P3", 2, "business_days", "business"),
    },
    "Standard": {
        Severity.P1: _v3("Standard P1", 4, "business_hours", "business"),
        Severity.P2: _v3("Standard P2", 1, "business_days", "business"),
        Severity.P3: _v3("Standard P3", 2, "business_days", "business"),
    },
}

CONTRACT_SLA: dict[str, dict[Severity, SlaTarget]] = {
    "ACCT-001": {
        Severity.P1: SlaTarget(15, "minutes", "24x7", Citation(
            NORTHSTAR_FILE, 1, "§1 Support terms", "P1: 15 minutes, 24x7")),
        # Contract states "P2: 1 hour" without a coverage calendar -> unspecified.
        Severity.P2: SlaTarget(1, "hours", "unspecified", Citation(
            NORTHSTAR_FILE, 1, "§1 Support terms", "P2: 1 hour")),
        Severity.P3: SlaTarget(8, "business_hours", "business", Citation(
            NORTHSTAR_FILE, 1, "§1 Support terms", "P3: 8 business hours")),
    },
    "ACCT-002": {
        Severity.P1: SlaTarget(2, "business_hours", "no_weekend_after_hours", Citation(
            LUMENWORKS_FILE, 1, "§1 Support terms", "P1: 2 business hours")),
        Severity.P2: SlaTarget(4, "business_hours", "no_weekend_after_hours", Citation(
            LUMENWORKS_FILE, 1, "§1 Support terms", "P2: 4 business hours")),
        Severity.P3: SlaTarget(2, "business_days", "no_weekend_after_hours", Citation(
            LUMENWORKS_FILE, 1, "§1 Support terms", "P3: 2 business days")),
    },
}


# --- Bulk upload (Product Ops Guide §1; KI-208 §2) ----------------------------

@dataclass(frozen=True)
class BulkUploadPolicy:
    supported_max_rows: int
    plans_with_access: tuple[str, ...]
    ki208_advisory_over_rows: int
    cite: Citation
    ki208_cite: Citation


BULK_UPLOAD = BulkUploadPolicy(
    supported_max_rows=5000,
    plans_with_access=("Growth", "Enterprise"),
    ki208_advisory_over_rows=3000,
    cite=Citation(
        "04_Product_Operations_Guide_and_Known_Issues.pdf", 1, "§1 Plan capabilities",
        "Bulk Upload: Available on Growth and Enterprise. Supported file size is "
        "up to 5,000 rows per CSV.",
    ),
    ki208_cite=Citation(
        "04_Product_Operations_Guide_and_Known_Issues.pdf", 1, "§2 KI-208",
        "intermittent failures on CSV uploads above approximately 3,000 rows, even "
        "though the supported product limit remains 5,000 rows. Workaround: split "
        "the upload into files below 3,000 rows.",
    ),
)
