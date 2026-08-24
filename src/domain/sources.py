"""Source registry and authority tiers.

Encodes SOURCE_MAP.md §2 as data: every source's type, status, authority tier,
and (for contracts) which account it binds. The precedence resolver and the
retrieval layer both consume this so the ranking lives in exactly one place.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class Tier(IntEnum):
    """Authority ranking. LOWER number = HIGHER authority (wins conflicts)."""

    CONTRACT = 1          # customer-specific agreement (only for its own account)
    CURRENT_POLICY = 2    # current global policy / SOP (v3, SOP v4)
    PRODUCT_GUIDE = 3     # product operations guide / known issues
    HISTORICAL = 4        # historical ticket resolutions — CONTEXT ONLY
    DEPRECATED = 5        # deprecated docs — excluded from default retrieval


class Status(str):
    pass


@dataclass(frozen=True)
class Source:
    filename: str
    kind: str            # policy | sop | guide | contract | data
    status: str          # CURRENT | DEPRECATED | CONTRACT | REFERENCE | DATA
    tier: Tier
    effective: str       # ISO-ish human string, as printed in the doc
    account_id: str | None = None   # set only for account-binding contracts
    default_retrieval: bool = True  # deprecated docs are False


# Registry keyed by raw filename. Mirrors SOURCE_MAP.md §1.
SOURCES: dict[str, Source] = {
    "01_Support_Policy_v3_CURRENT.pdf": Source(
        "01_Support_Policy_v3_CURRENT.pdf", "policy", "CURRENT",
        Tier.CURRENT_POLICY, "2026-05-01",
    ),
    "02_Support_Policy_v2_DEPRECATED.pdf": Source(
        "02_Support_Policy_v2_DEPRECATED.pdf", "policy", "DEPRECATED",
        Tier.DEPRECATED, "2025-01-01", default_retrieval=False,
    ),
    "03_Cancellation_and_Service_Credit_SOP_v4.pdf": Source(
        "03_Cancellation_and_Service_Credit_SOP_v4.pdf", "sop", "CURRENT",
        Tier.CURRENT_POLICY, "2026-06-15",
    ),
    "04_Product_Operations_Guide_and_Known_Issues.pdf": Source(
        "04_Product_Operations_Guide_and_Known_Issues.pdf", "guide", "CURRENT",
        Tier.PRODUCT_GUIDE, "2026-08-14",
    ),
    "05_Northstar_Logistics_Enterprise_Agreement.pdf": Source(
        "05_Northstar_Logistics_Enterprise_Agreement.pdf", "contract", "CONTRACT",
        Tier.CONTRACT, "2026-01-01", account_id="ACCT-001",
    ),
    "06_LumenWorks_Service_Agreement.pdf": Source(
        "06_LumenWorks_Service_Agreement.pdf", "contract", "CONTRACT",
        Tier.CONTRACT, "2026-03-01", account_id="ACCT-002",
    ),
}


def contract_for_account(account_id: str) -> Source | None:
    """The binding contract for an account, or None. Scope gate for Tier 1."""
    for src in SOURCES.values():
        if src.tier == Tier.CONTRACT and src.account_id == account_id:
            return src
    return None
