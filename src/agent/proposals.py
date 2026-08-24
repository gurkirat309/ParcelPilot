"""Proposal store — Rule 5: state-changing tools NEVER write on first call.

A state-changing tool returns a pending `Proposal` (id, human-readable preview,
status). Execution happens only through the separate confirm step, enforced here
in code — not by prompting the model. Proposals are scoped to the session that
created them, so one account can't confirm another's action.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field


@dataclass
class Proposal:
    id: str
    kind: str                 # "escalation" | "ticket_update" | "followup_task"
    account_id: str | None
    created_by_role: str
    preview: str              # human-readable summary of what WILL happen
    payload: dict
    status: str = "pending"   # pending | confirmed | cancelled
    result: dict | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ProposalStore:
    _items: dict[str, Proposal] = field(default_factory=dict)

    def create(self, kind: str, account_id: str | None, role: str,
               preview: str, payload: dict) -> Proposal:
        pid = f"PROP-{uuid.uuid4().hex[:8]}"
        p = Proposal(pid, kind, account_id, role, preview, payload)
        self._items[pid] = p
        return p

    def get(self, pid: str) -> Proposal | None:
        return self._items.get(pid)

    def confirm(self, pid: str, *, account_id: str | None, is_internal: bool) -> Proposal:
        p = self._items.get(pid)
        if p is None:
            raise KeyError(pid)
        if not is_internal and p.account_id != account_id:
            raise PermissionError("proposal belongs to another account")
        if p.status != "pending":
            raise ValueError(f"proposal already {p.status}")
        # Mocked execution (Rule: action tool may be mocked locally).
        p.status = "confirmed"
        p.result = {"executed": True, "mock": True, **_execute(p)}
        return p

    def cancel(self, pid: str) -> Proposal:
        p = self._items[pid]
        p.status = "cancelled"
        return p

    def list_for(self, *, account_id: str | None, is_internal: bool) -> list[Proposal]:
        return [
            p for p in self._items.values()
            if is_internal or p.account_id == account_id
        ]


def _execute(p: Proposal) -> dict:
    """Mocked side effect. In production this would create the ticket/task."""
    if p.kind == "escalation":
        return {"escalation_id": f"ESC-{p.id[-6:]}"}
    if p.kind == "ticket_update":
        return {"updated_ticket": p.payload.get("ticket_id")}
    if p.kind == "followup_task":
        return {"task_id": f"TASK-{p.id[-6:]}"}
    return {}


# Single process-wide store (mock actions; fine for the assessment).
STORE = ProposalStore()
