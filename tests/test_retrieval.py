"""Retrieval authority gating: deprecated excluded by default; contract passages
scoped to their bound account."""

from __future__ import annotations

import pytest

from src.domain.sources import Tier
from src.retrieval.index import HybridIndex, wants_version_history


@pytest.fixture(scope="module")
def index() -> HybridIndex:
    return HybridIndex()


def test_deprecated_excluded_by_default(index: HybridIndex):
    hits = index.search("what changed between policy versions", top_k=10,
                        account_id="ACCT-004")
    assert all(h.chunk.tier != int(Tier.DEPRECATED) for h in hits)


def test_deprecated_retrievable_when_requested(index: HybridIndex):
    hits = index.search("what changed between v2 and v3", top_k=10,
                        include_deprecated=True, account_id="ACCT-004")
    assert any(h.chunk.tier == int(Tier.DEPRECATED) for h in hits)


def test_contract_scoped_to_owner(index: HybridIndex):
    q = "Northstar cancellation before pickup no fee"
    owner = index.search(q, top_k=10, account_id="ACCT-001")
    other = index.search(q, top_k=10, account_id="ACCT-003")
    assert any(h.chunk.source_file.startswith("05_Northstar") for h in owner)
    assert not any(h.chunk.source_file.startswith("05_Northstar") for h in other)


def test_internal_sees_all_contracts(index: HybridIndex):
    hits = index.search("Northstar enterprise agreement", top_k=10, is_internal=True)
    assert any(h.chunk.source_file.startswith("05_Northstar") for h in hits)


def test_version_query_detection():
    assert wants_version_history("what changed between v2 and v3")
    assert not wants_version_history("can I cancel my order")
