"""The deterministic source-precedence resolver.

Given an account (and, for SLA, its plan + a severity), returns the EFFECTIVE
terms the calculators must use, plus the winning source and its citation. This is
the single place the authority ranking (SOURCE_MAP §2) is applied:

    1. account-binding contract (scope-gated to that account)   [Tier 1]
    2. current global policy / SOP                              [Tier 2]

Contracts are scope-gated: an account only ever sees its own contract. An account
with no contract falls through to the current global default.
"""

from __future__ import annotations

from dataclasses import dataclass

from .policy import (
    CONTRACT_CANCELLATION,
    CONTRACT_CREDIT,
    CONTRACT_SLA,
    DEFAULT_CANCELLATION,
    DEFAULT_CREDIT,
    PLAN_SLA,
    CancellationTerms,
    CreditTerms,
    Severity,
    SlaTarget,
)


@dataclass(frozen=True)
class Resolved:
    """A resolved term set plus provenance for transparent answers."""

    terms: object
    winning_source: str      # "contract" | "current_policy"
    account_scoped: bool     # True if a contract override applied to this account


def resolve_cancellation(account_id: str) -> Resolved:
    override = CONTRACT_CANCELLATION.get(account_id)
    if override is not None:
        return Resolved(override, "contract", True)
    return Resolved(DEFAULT_CANCELLATION, "current_policy", False)


def resolve_credit(account_id: str) -> Resolved:
    override = CONTRACT_CREDIT.get(account_id)
    if override is not None:
        return Resolved(override, "contract", True)
    return Resolved(DEFAULT_CREDIT, "current_policy", False)


def resolve_sla(account_id: str, plan: str, severity: Severity) -> Resolved:
    contract = CONTRACT_SLA.get(account_id)
    if contract is not None and severity in contract:
        return Resolved(contract[severity], "contract", True)
    plan_targets = PLAN_SLA.get(plan)
    if plan_targets is None:
        raise ValueError(f"Unknown plan: {plan!r}")
    return Resolved(plan_targets[severity], "current_policy", False)


# Convenience typed getters (help callers/tests read clearly).
def cancellation_terms(account_id: str) -> tuple[CancellationTerms, Resolved]:
    r = resolve_cancellation(account_id)
    return r.terms, r  # type: ignore[return-value]


def credit_terms(account_id: str) -> tuple[CreditTerms, Resolved]:
    r = resolve_credit(account_id)
    return r.terms, r  # type: ignore[return-value]


def sla_target(account_id: str, plan: str, severity: Severity) -> tuple[SlaTarget, Resolved]:
    r = resolve_sla(account_id, plan, severity)
    return r.terms, r  # type: ignore[return-value]
