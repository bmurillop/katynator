"""API route smoke tests — verifies status codes, shapes, and auth.

Uses mocked DB so these tests never need a real database.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.enums import (
    AccountType,
    CategorySource,
    Currency,
    EmailStatus,
    EntityType,
    MatchType,
    PatternSource,
    RuleSource,
    TransactionDirection,
    UnresolvedEntityStatus,
)


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_result(rows=None, scalar=None, scalar_all=None):
    """Return a MagicMock that looks like an SQLAlchemy execute() result."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = scalar
    result.scalar_one.return_value = scalar if scalar is not None else (len(rows) if rows else 0)
    result.scalars.return_value.all.return_value = rows or []
    return result


# ── persons ──────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_list_persons_empty(member_client, db_mock):
    db_mock.execute.return_value = _make_result(rows=[])
    resp = await member_client.get("/api/persons")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.anyio
async def test_list_persons_requires_auth(anon_client):
    resp = await anon_client.get("/api/persons")
    assert resp.status_code == 403  # no bearer → HTTPBearer raises 403


# ── accounts ─────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_list_accounts_empty(member_client, db_mock):
    # first call: count, second call: rows
    db_mock.execute.side_effect = [
        _make_result(scalar=0),
        _make_result(rows=[]),
    ]
    resp = await member_client.get("/api/accounts")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.anyio
async def test_get_account_not_found(member_client, db_mock):
    db_mock.execute.return_value = _make_result(scalar=None)
    resp = await member_client.get(f"/api/accounts/{uuid.uuid4()}")
    assert resp.status_code == 404


# ── categories ───────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_list_categories_empty(member_client, db_mock):
    db_mock.execute.return_value = _make_result(rows=[])
    resp = await member_client.get("/api/categories")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.anyio
async def test_create_category_requires_admin(anon_client):
    resp = await anon_client.post("/api/categories", json={"name": "Comida"})
    assert resp.status_code == 403


# ── category rules ───────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_list_rules_empty(member_client, db_mock):
    db_mock.execute.return_value = _make_result(rows=[])
    resp = await member_client.get("/api/category-rules")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.anyio
async def test_create_rule_invalid_neither_entity_nor_memo(admin_client, db_mock):
    resp = await admin_client.post(
        "/api/category-rules",
        json={
            "entity_id": None,
            "memo_pattern": None,
            "match_type": "any",
            "category_id": str(uuid.uuid4()),
        },
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_delete_rule_not_found(admin_client, db_mock):
    db_mock.execute.return_value = _make_result(scalar=None)
    resp = await admin_client.delete(f"/api/category-rules/{uuid.uuid4()}")
    assert resp.status_code == 404


# ── entities ─────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_list_entities_empty(member_client, db_mock):
    db_mock.execute.side_effect = [
        _make_result(scalar=0),
        _make_result(rows=[]),
    ]
    resp = await member_client.get("/api/entities")
    assert resp.status_code == 200
    assert resp.json()["items"] == []


@pytest.mark.anyio
async def test_get_entity_not_found(member_client, db_mock):
    db_mock.execute.return_value = _make_result(scalar=None)
    resp = await member_client.get(f"/api/entities/{uuid.uuid4()}")
    assert resp.status_code == 404


# ── transactions ─────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_list_transactions_empty(member_client, db_mock):
    db_mock.execute.side_effect = [
        _make_result(scalar=0),
        _make_result(rows=[]),
    ]
    resp = await member_client.get("/api/transactions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.anyio
async def test_summary_endpoint_reachable(member_client, db_mock):
    db_mock.execute.return_value = _make_result(rows=[])
    resp = await member_client.get("/api/transactions/summary")
    assert resp.status_code == 200
    assert "summaries" in resp.json()


@pytest.mark.anyio
async def test_get_transaction_not_found(member_client, db_mock):
    db_mock.execute.return_value = _make_result(scalar=None)
    resp = await member_client.get(f"/api/transactions/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_summary_url_doesnt_conflict_with_id_route(member_client, db_mock):
    """GET /transactions/summary must not be treated as a UUID param."""
    db_mock.execute.return_value = _make_result(rows=[])
    resp = await member_client.get("/api/transactions/summary")
    # Should hit the summary route (200), not 422 (invalid UUID)
    assert resp.status_code == 200


# ── unresolved entities ──────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_list_unresolved_empty(member_client, db_mock):
    db_mock.execute.side_effect = [
        _make_result(scalar=0),
        _make_result(rows=[]),
    ]
    resp = await member_client.get("/api/unresolved-entities")
    assert resp.status_code == 200
    assert resp.json()["items"] == []


@pytest.mark.anyio
async def test_resolve_not_found(admin_client, db_mock):
    db_mock.execute.return_value = _make_result(scalar=None)
    resp = await admin_client.post(
        f"/api/unresolved-entities/{uuid.uuid4()}/resolve",
        json={"entity_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_ignore_not_found(admin_client, db_mock):
    db_mock.execute.return_value = _make_result(scalar=None)
    resp = await admin_client.post(f"/api/unresolved-entities/{uuid.uuid4()}/ignore")
    assert resp.status_code == 404


# ── emails (regression — Phase 3 routes still work) ─────────────────────────

@pytest.mark.anyio
async def test_list_emails_empty(member_client, db_mock):
    db_mock.execute.side_effect = [
        _make_result(scalar=0),
        _make_result(rows=[]),
    ]
    resp = await member_client.get("/api/emails")
    assert resp.status_code == 200
    assert resp.json()["items"] == []
