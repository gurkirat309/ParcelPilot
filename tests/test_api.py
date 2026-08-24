"""API auth + proposal endpoints (no LLM calls — /chat is exercised separately)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.agent.proposals import STORE
from src.api.app import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health_ok(client: TestClient):
    assert client.get("/health").json()["status"] == "ok"


def test_missing_token_401(client: TestClient):
    assert client.get("/me").status_code == 401
    assert client.post("/chat", json={"message": "hi"}).status_code == 401


def test_me_reflects_token(client: TestClient):
    r = client.get("/me", headers={"Authorization": "Bearer cust-acct-002"})
    assert r.json() == {"role": "customer", "account_id": "ACCT-002"}


def test_confirm_scoping_via_api(client: TestClient):
    # Seed a pending proposal for ACCT-001 directly (bypassing the LLM).
    p = STORE.create("escalation", "ACCT-001", "customer", "Escalate", {"reason": "x"})
    # ACCT-002 cannot confirm it.
    bad = client.post(f"/proposals/{p.id}/confirm",
                      headers={"Authorization": "Bearer cust-acct-002"})
    assert bad.status_code == 403
    # Owner can, and it executes.
    ok = client.post(f"/proposals/{p.id}/confirm",
                     headers={"Authorization": "Bearer cust-acct-001"})
    assert ok.status_code == 200 and ok.json()["status"] == "confirmed"


def test_customer_only_sees_own_proposals(client: TestClient):
    STORE.create("followup_task", "ACCT-004", "customer", "T", {})
    r = client.get("/proposals", headers={"Authorization": "Bearer cust-acct-002"})
    assert all(p["account_id"] == "ACCT-002" for p in r.json()["proposals"])
