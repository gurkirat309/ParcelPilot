"""Mock authentication (Rule 4: account context is server-side).

A bearer token maps to a fixed Session. The account_id lives in this
server-side table, NOT in the request body or any model-visible field — the
client cannot claim to be another account. In production this would be a real
auth provider; the security property (scope from the session, not the caller's
input) is the same.
"""

from __future__ import annotations

from fastapi import Header, HTTPException

from src.data.repository import Session

# token -> Session. Demo tokens for the two personas.
_TOKENS: dict[str, Session] = {
    "cust-acct-001": Session("customer", "ACCT-001"),  # Northstar
    "cust-acct-002": Session("customer", "ACCT-002"),  # LumenWorks
    "cust-acct-003": Session("customer", "ACCT-003"),  # Beacon Retail
    "cust-acct-004": Session("customer", "ACCT-004"),  # Axis Labs
    "ops": Session("internal_ops", None),
}


def session_from_token(authorization: str | None = Header(default=None)) -> Session:
    token = ""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    session = _TOKENS.get(token)
    if session is None:
        raise HTTPException(status_code=401, detail="invalid or missing bearer token")
    return session


def demo_tokens() -> dict[str, str]:
    return {tok: f"{s.role}:{s.account_id or 'all'}" for tok, s in _TOKENS.items()}
