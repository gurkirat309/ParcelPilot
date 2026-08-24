"""Agent tools: document search, scoped structured lookups, deterministic
calculators, and proposal-gated state-changing actions.

Every tool runs against the trusted server-side `Session`. `account_id` is NEVER
a tool parameter for a customer — scoping is applied in the repository. The model
chooses tools and passes ids/severities; it never does math or decides eligibility
(the calculators do) and never widens its own data scope.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from src.data.repository import Repository, Session
from src.domain import calculators as calc
from src.domain.policy import Severity
from src.domain.precedence import resolve_cancellation, resolve_credit, resolve_sla
from src.domain.timeutil import parse_ts
from src.llm.client import ToolSpec
from src.retrieval.index import HybridIndex, wants_version_history

from .proposals import STORE


@dataclass
class AgentContext:
    session: Session
    repo: Repository
    index: HybridIndex


def _cite(c) -> dict:
    return {"source_file": c.source_file, "page": c.page, "section": c.section,
            "quote": c.quote}


# --- tool implementations -----------------------------------------------------

def _search_documents(ctx: AgentContext, query: str, include_deprecated: bool = False) -> dict:
    incl = include_deprecated or wants_version_history(query)
    hits = ctx.index.search(
        query, account_id=ctx.session.account_id,
        is_internal=ctx.session.is_internal, include_deprecated=incl, top_k=5)
    return {
        "include_deprecated": incl,
        "results": [
            {"source_file": h.chunk.source_file, "page": h.chunk.page,
             "authority_tier": h.chunk.tier, "status": h.chunk.status,
             "text": h.chunk.text, "score": round(h.score, 3)}
            for h in hits
        ],
        "note": "authority_tier: 1=contract 2=current-policy 3=product-guide "
                "5=deprecated. Lower wins. Never base an answer on a deprecated source.",
    }


def _get_order(ctx: AgentContext, order_id: str) -> dict:
    o = ctx.repo.get_order(ctx.session, order_id)
    return asdict(o) if o else {"error": "not_found_or_out_of_scope", "order_id": order_id}


def _get_account(ctx: AgentContext, account_id: str | None = None) -> dict:
    a = ctx.repo.get_account(ctx.session, account_id)
    return asdict(a) if a else {"error": "not_found_or_out_of_scope"}


def _get_ticket(ctx: AgentContext, ticket_id: str) -> dict:
    t = ctx.repo.get_ticket(ctx.session, ticket_id)
    if not t:
        return {"error": "not_found_or_out_of_scope", "ticket_id": ticket_id}
    d = asdict(t)
    if d.get("historical_resolution"):
        d["_warning"] = ("historical_resolution is CONTEXT ONLY and may be WRONG; "
                         "never cite it as the basis for an answer.")
    return d


def _list_tickets(ctx: AgentContext, account_id: str | None = None) -> dict:
    tickets = ctx.repo.list_tickets(ctx.session, account_id)
    return {"tickets": [asdict(t) for t in tickets]}


def _calc_cancellation_fee(ctx: AgentContext, order_id: str) -> dict:
    o = ctx.repo.get_order(ctx.session, order_id)
    if not o:
        return {"error": "not_found_or_out_of_scope", "order_id": order_id}
    resolved = resolve_cancellation(o.account_id)
    r = calc.cancellation_fee(
        o.status, parse_ts(o.booked_at), resolved.terms,
        requested_at=parse_ts(o.cancellation_requested_at))
    return {"order_id": order_id, "cancellable": r.cancellable, "fee_inr": r.fee_inr,
            "reason": r.reason, "route": r.route,
            "winning_source": resolved.winning_source,
            "citations": [_cite(c) for c in r.citations]}


def _calc_service_credit(ctx: AgentContext, order_id: str) -> dict:
    o = ctx.repo.get_order(ctx.session, order_id)
    if not o:
        return {"error": "not_found_or_out_of_scope", "order_id": order_id}
    resolved = resolve_credit(o.account_id)
    r = calc.service_credit(
        pickup_window_end=parse_ts(o.pickup_window_end),
        carrier_fault=o.carrier_fault, customer_fault=o.customer_fault,
        shipment_fee_inr=o.shipment_fee_inr, terms=resolved.terms,
        pickup_actual_at=parse_ts(o.pickup_actual_at))
    return {"order_id": order_id, "eligible": r.eligible, "amount_inr": r.amount_inr,
            "needs_approval": r.needs_approval, "needs_verification": r.needs_verification,
            "delay_hours": round(r.delay_hours, 2) if r.delay_hours is not None else None,
            "basis": r.basis, "winning_source": resolved.winning_source,
            "citations": [_cite(c) for c in r.citations]}


def _calc_sla(ctx: AgentContext, ticket_id: str, severity: str) -> dict:
    t = ctx.repo.get_ticket(ctx.session, ticket_id)
    if not t:
        return {"error": "not_found_or_out_of_scope", "ticket_id": ticket_id}
    a = ctx.repo.get_account(ctx.session, t.account_id)
    if not a:
        return {"error": "account_out_of_scope"}
    try:
        sev = Severity(severity.upper())
    except ValueError:
        return {"error": "bad_severity", "allowed": ["P1", "P2", "P3"]}
    resolved = resolve_sla(a.account_id, a.plan, sev)
    r = calc.sla_first_response(resolved.terms, parse_ts(t.created_at))
    return {"ticket_id": ticket_id, "severity": sev.value,
            "target_value": r.target_value, "target_unit": r.target_unit,
            "coverage": r.coverage, "elapsed_minutes": round(r.elapsed_minutes),
            "breached": r.breached, "computable": r.computable, "reason": r.reason,
            "winning_source": resolved.winning_source,
            "citations": [_cite(c) for c in r.citations]}


def _check_bulk_upload(ctx: AgentContext, rows: int, account_id: str | None = None) -> dict:
    a = ctx.repo.get_account(ctx.session, account_id)
    if not a:
        return {"error": "account_out_of_scope"}
    r = calc.bulk_upload_check(a.plan, int(rows))
    return {"plan": a.plan, "rows": int(rows), "available": r.available,
            "supported_max_rows": r.supported_max_rows,
            "within_supported": r.within_supported, "ki208_advisory": r.ki208_advisory,
            "message": r.message, "citations": [_cite(c) for c in r.citations]}


def _propose(ctx: AgentContext, kind: str, preview: str, payload: dict) -> dict:
    p = STORE.create(kind, ctx.session.account_id, ctx.session.role, preview, payload)
    return {"proposal_id": p.id, "kind": p.kind, "status": p.status,
            "preview": p.preview,
            "note": "PENDING — requires explicit user confirmation before execution."}


def _create_escalation(ctx: AgentContext, reason: str, ticket_id: str | None = None,
                       priority: str = "P2") -> dict:
    preview = f"Escalate{f' ticket {ticket_id}' if ticket_id else ''} as {priority}: {reason}"
    return _propose(ctx, "escalation", preview,
                    {"reason": reason, "ticket_id": ticket_id, "priority": priority})


def _update_ticket(ctx: AgentContext, ticket_id: str, note: str,
                   new_status: str | None = None) -> dict:
    if not ctx.repo.get_ticket(ctx.session, ticket_id):
        return {"error": "not_found_or_out_of_scope", "ticket_id": ticket_id}
    preview = f"Update ticket {ticket_id}" + (f" -> status {new_status}" if new_status else "") + f": {note}"
    return _propose(ctx, "ticket_update", preview,
                    {"ticket_id": ticket_id, "note": note, "new_status": new_status})


def _create_followup_task(ctx: AgentContext, title: str, details: str = "") -> dict:
    return _propose(ctx, "followup_task", f"Follow-up task: {title}",
                    {"title": title, "details": details})


# --- registry -----------------------------------------------------------------

_IMPL = {
    "search_documents": _search_documents,
    "get_order": _get_order,
    "get_account": _get_account,
    "get_ticket": _get_ticket,
    "list_tickets": _list_tickets,
    "calc_cancellation_fee": _calc_cancellation_fee,
    "calc_service_credit": _calc_service_credit,
    "calc_sla": _calc_sla,
    "check_bulk_upload": _check_bulk_upload,
    "create_escalation": _create_escalation,
    "update_ticket": _update_ticket,
    "create_followup_task": _create_followup_task,
}


def _s(props: dict, required: list[str] | None = None) -> dict:
    return {"type": "object", "properties": props, "required": required or []}


TOOLSPECS: list[ToolSpec] = [
    ToolSpec("search_documents",
             "Search ParcelPilot policies, SOPs, the product guide, and (only for "
             "the caller's own account) their contract. Returns passages with an "
             "authority_tier. Deprecated docs are auto-included only for "
             "version-history questions.",
             _s({"query": {"type": "string", "description": "what to look up"},
                 "include_deprecated": {"type": "boolean"}}, ["query"])),
    ToolSpec("get_order", "Fetch one order by id (scoped to the caller).",
             _s({"order_id": {"type": "string"}}, ["order_id"])),
    ToolSpec("get_account", "Fetch account details. Customers get their own; "
             "internal_ops may pass an account_id.",
             _s({"account_id": {"type": "string"}})),
    ToolSpec("get_ticket", "Fetch one ticket by id (scoped to the caller).",
             _s({"ticket_id": {"type": "string"}}, ["ticket_id"])),
    ToolSpec("list_tickets", "List tickets (own account for customers; all or by "
             "account_id for internal_ops).",
             _s({"account_id": {"type": "string"}})),
    ToolSpec("calc_cancellation_fee",
             "Deterministically compute whether an order can be cancelled and the "
             "fee, applying contract/policy precedence. Do NOT compute this yourself.",
             _s({"order_id": {"type": "string"}}, ["order_id"])),
    ToolSpec("calc_service_credit",
             "Deterministically compute failed-pickup service-credit eligibility and "
             "amount, applying precedence. Do NOT compute this yourself.",
             _s({"order_id": {"type": "string"}}, ["order_id"])),
    ToolSpec("calc_sla",
             "Compute the first-response SLA target and breach status for a ticket at "
             "a given severity (P1/P2/P3). Business-hours targets may be indeterminate.",
             _s({"ticket_id": {"type": "string"},
                 "severity": {"type": "string", "enum": ["P1", "P2", "P3"]}},
                ["ticket_id", "severity"])),
    ToolSpec("check_bulk_upload",
             "Check bulk-upload availability/limit for a row count, incl. KI-208 advisory.",
             _s({"rows": {"type": "integer"}, "account_id": {"type": "string"}}, ["rows"])),
    ToolSpec("create_escalation",
             "PROPOSE an escalation (does not execute; needs user confirmation).",
             _s({"reason": {"type": "string"}, "ticket_id": {"type": "string"},
                 "priority": {"type": "string", "enum": ["P1", "P2", "P3"]}}, ["reason"])),
    ToolSpec("update_ticket",
             "PROPOSE a ticket update (does not execute; needs user confirmation).",
             _s({"ticket_id": {"type": "string"}, "note": {"type": "string"},
                 "new_status": {"type": "string"}}, ["ticket_id", "note"])),
    ToolSpec("create_followup_task",
             "PROPOSE a follow-up task (does not execute; needs user confirmation).",
             _s({"title": {"type": "string"}, "details": {"type": "string"}}, ["title"])),
]


def tools_for(session: Session) -> list[ToolSpec]:
    """Customers don't get the internal-only account_id parameter surfaces, but the
    repository enforces scope regardless, so the same set is safe to expose."""
    return TOOLSPECS


def execute_tool(name: str, args: dict, ctx: AgentContext) -> str:
    impl = _IMPL.get(name)
    if impl is None:
        return json.dumps({"error": f"unknown_tool:{name}"})
    try:
        return json.dumps(impl(ctx, **args), default=str)
    except TypeError as e:
        return json.dumps({"error": "bad_arguments", "detail": str(e)})
    except Exception as e:  # never crash the loop on a tool error
        return json.dumps({"error": "tool_failed", "detail": str(e)})
