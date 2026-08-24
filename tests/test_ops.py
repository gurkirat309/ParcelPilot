"""Problem 1 ops signals over real + synthetic tickets."""

from __future__ import annotations

import pytest

from src.domain.policy import Severity
from src.ops.signals import _classify, build_dashboard


@pytest.fixture(scope="module")
def dash() -> dict:
    return build_dashboard()


def test_classifier_maps_known_issues():
    assert _classify("Bulk upload fails for large CSV", "70% then fails")[0] == "bulk_upload"
    assert _classify("All shipment creation is failing", "HTTP 500")[1] == Severity.P1
    assert _classify("Possible API key exposure", "posted a key")[0] == "security_incident"


def test_multi_customer_bulk_upload_detected(dash: dict):
    clusters = {c["issue"]: c for c in dash["issue_clusters"]}
    assert "bulk_upload" in clusters
    assert clusters["bulk_upload"]["distinct_accounts"] >= 2
    assert clusters["bulk_upload"]["known_issue"] == "KI-208"


def test_sla_watch_flags_a_breach(dash: dict):
    # A 24x7 P1 target is exactly computable; at least one open P1 is breached.
    breached = [s for s in dash["sla_watch"] if s["breached"] is True]
    assert any(s["ticket_id"] == "TKT-501" for s in breached)


def test_business_hours_targets_indeterminate(dash: dict):
    assert any(s["breached"] is None for s in dash["sla_watch"])


def test_synthetic_counted_but_isolated(dash: dict):
    assert dash["totals"]["synthetic"] == 10
