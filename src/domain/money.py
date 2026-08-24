"""Deterministic money helpers. All amounts are whole INR (Rule 6).

The model never does arithmetic; these functions are the only place fees/credits
are computed, and they are unit-tested.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal


def pct_of(amount_inr: int, pct: int) -> int:
    """`pct` percent of `amount_inr`, rounded half-up to whole INR."""
    result = (Decimal(amount_inr) * Decimal(pct) / Decimal(100)).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    )
    return int(result)


def inr(amount: int) -> str:
    """Human-readable INR string, e.g. 5000 -> 'INR 5,000'."""
    return f"INR {amount:,}"
