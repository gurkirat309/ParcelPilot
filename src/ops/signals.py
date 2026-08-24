"""Problem 1 — proactive issue detection for internal ops.

Deterministic analytics over ALL tickets (real + synthetic) and orders:
  - issue classification (maps free text to a known-issue signature),
  - SLA watch (first-response breaches / at-risk open tickets),
  - issue clusters (multiple tickets on the same product issue),
  - spikes (surge vs baseline near the snapshot),
  - multi-customer issues (same signature across >= 2 accounts).

Everything measures against the frozen snapshot (Rule 3). This is analytics, not
policy: it never cites authority or decides customer outcomes — it surfaces what
deserves a human's attention.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import timedelta

from src.config import SNAPSHOT_AT
from src.data.db import connect
from src.domain.calculators import sla_first_response
from src.domain.policy import Severity
from src.domain.precedence import resolve_sla
from src.domain.timeutil import parse_ts

# issue signature -> (matchers, default severity, known_issue)
_RULES: list[tuple[str, re.Pattern, Severity, str | None]] = [
    ("shipment_outage", re.compile(r"http 500|all shipment creation|creation is failing|creation failing|shipment creation failing", re.I), Severity.P1, None),
    ("security_incident", re.compile(r"api key|credential|exposure|exposed|leak", re.I), Severity.P1, None),
    ("bulk_upload", re.compile(r"bulk upload|csv|import", re.I), Severity.P2, "KI-208"),
    ("swiftship_status", re.compile(r"swiftship|still shows booked|status not updated|status lag|booked after", re.I), Severity.P3, "KI-211"),
    ("cancellation", re.compile(r"cancel", re.I), Severity.P3, None),
    ("billing", re.compile(r"billing|contact", re.I), Severity.P3, None),
]

_RECENT_WINDOW = timedelta(hours=24)


@dataclass
class SlaItem:
    ticket_id: str
    account_id: str
    issue: str
    severity: str
    target: str
    coverage: str
    elapsed_minutes: int
    breached: bool | None
    winning_source: str


def _classify(subject: str, description: str) -> tuple[str, Severity, str | None]:
    text = f"{subject or ''} {description or ''}"
    for name, pat, sev, ki in _RULES:
        if pat.search(text):
            return name, sev, ki
    return "other", Severity.P3, None


def _fetch(conn):
    tickets = conn.execute("SELECT * FROM tickets").fetchall()
    accounts = {r["account_id"]: r for r in conn.execute("SELECT * FROM accounts").fetchall()}
    return tickets, accounts


def build_dashboard() -> dict:
    conn = connect()
    try:
        tickets, accounts = _fetch(conn)
    finally:
        conn.close()

    enriched = []
    for t in tickets:
        issue, sev, ki = _classify(t["subject"], t["description"])
        enriched.append({"row": t, "issue": issue, "severity": sev, "ki": ki,
                         "created": parse_ts(t["created_at"])})

    sla_watch = _sla_watch(enriched, accounts)
    clusters = _clusters(enriched)
    spikes = _spikes(enriched)
    multi = [c for c in clusters if c["distinct_accounts"] >= 2]

    return {
        "generated_at": SNAPSHOT_AT.isoformat(),
        "totals": {
            "tickets": len(tickets),
            "open": sum(1 for t in tickets if t["status"] == "open"),
            "synthetic": sum(1 for t in tickets if t["is_synthetic"]),
        },
        "sla_watch": [asdict(s) for s in sla_watch],
        "issue_clusters": clusters,
        "spikes": spikes,
        "multi_customer_issues": multi,
    }


def _sla_watch(enriched: list[dict], accounts: dict) -> list[SlaItem]:
    items: list[SlaItem] = []
    for e in enriched:
        t = e["row"]
        if t["status"] != "open":
            continue
        acct = accounts.get(t["account_id"])
        if not acct:
            continue
        resolved = resolve_sla(acct["account_id"], acct["plan"], e["severity"])
        r = sla_first_response(resolved.terms, e["created"])
        items.append(SlaItem(
            ticket_id=t["ticket_id"], account_id=t["account_id"], issue=e["issue"],
            severity=e["severity"].value,
            target=f"{r.target_value} {r.target_unit}", coverage=r.coverage,
            elapsed_minutes=round(r.elapsed_minutes), breached=r.breached,
            winning_source=resolved.winning_source,
        ))
    # Breached first, then indeterminate, then within-target; each by elapsed desc.
    rank = {True: 0, None: 1, False: 2}
    items.sort(key=lambda s: (rank[s.breached], -s.elapsed_minutes))
    return items


def _clusters(enriched: list[dict]) -> list[dict]:
    groups: dict[str, list[dict]] = {}
    for e in enriched:
        groups.setdefault(e["issue"], []).append(e)
    out = []
    for issue, members in groups.items():
        if issue == "other":
            continue
        accts = sorted({m["row"]["account_id"] for m in members})
        open_ids = [m["row"]["ticket_id"] for m in members if m["row"]["status"] == "open"]
        out.append({
            "issue": issue,
            "known_issue": members[0]["ki"],
            "count": len(members),
            "open_count": len(open_ids),
            "distinct_accounts": len(accts),
            "accounts": accts,
            "ticket_ids": sorted(m["row"]["ticket_id"] for m in members),
        })
    out.sort(key=lambda c: (-c["open_count"], -c["count"]))
    return out


def _spikes(enriched: list[dict]) -> list[dict]:
    cutoff = SNAPSHOT_AT - _RECENT_WINDOW
    per_issue: dict[str, dict] = {}
    for e in enriched:
        if e["issue"] == "other":
            continue
        d = per_issue.setdefault(e["issue"], {"recent": 0, "baseline": 0})
        if e["created"] and e["created"] >= cutoff:
            d["recent"] += 1
        else:
            d["baseline"] += 1
    spikes = []
    for issue, d in per_issue.items():
        # Surge heuristic: >=3 in the last 24h and at least triple the baseline.
        if d["recent"] >= 3 and d["recent"] >= max(1, d["baseline"]) * 3:
            spikes.append({"issue": issue, "recent_24h": d["recent"],
                           "baseline_prior": d["baseline"],
                           "note": "Surge vs baseline in the last 24h before snapshot."})
    spikes.sort(key=lambda s: -s["recent_24h"])
    return spikes
