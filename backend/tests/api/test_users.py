"""User management API tests."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from app.models.enums import UserRole
from app.schemas.user import AdminResetPassword, UserCreate


# ── schema validation ─────────────────────────────────────────────────────────

class TestUserCreate:
    def test_valid(self):
        u = UserCreate(email="paola@example.com", password="secreta123", role=UserRole.member)
        assert u.role == UserRole.member
        assert u.email == "paola@example.com"

    def test_password_too_short(self):
        with pytest.raises(Exception, match="8 caracteres"):
            UserCreate(email="x@x.com", password="short")

    def test_default_role_member(self):
        u = UserCreate(email="x@x.com", password="longenough")
        assert u.role == UserRole.member

    def test_invalid_email(self):
        with pytest.raises(Exception):
            UserCreate(email="not-an-email", password="longenough")

    def test_no_person_id_by_default(self):
        u = UserCreate(email="x@x.com", password="longenough")
        assert u.person_id is None


class TestAdminResetPassword:
    def test_valid(self):
        r = AdminResetPassword(new_password="nuevaclave1")
        assert r.new_password == "nuevaclave1"

    def test_too_short(self):
        with pytest.raises(Exception, match="8 caracteres"):
            AdminResetPassword(new_password="corta")


# ── route tests ───────────────────────────────────────────────────────────────

def _make_result(scalar=None, rows=None):
    result = MagicMock()
    result.scalar_one_or_none.return_value = scalar
    result.scalar_one.return_value = scalar
    result.scalars.return_value.all.return_value = rows or []
    return result


@pytest.mark.anyio
async def test_list_users_requires_auth(anon_client):
    resp = await anon_client.get("/api/users")
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_list_users_empty(admin_client, db_mock):
    db_mock.execute.return_value = _make_result(rows=[])
    resp = await admin_client.get("/api/users")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.anyio
async def test_get_user_not_found(admin_client, db_mock):
    db_mock.execute.return_value = _make_result(scalar=None)
    resp = await admin_client.get(f"/api/users/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_create_user_duplicate_email(admin_client, db_mock):
    existing_user = MagicMock()
    db_mock.execute.return_value = _make_result(scalar=existing_user)
    resp = await admin_client.post(
        "/api/users",
        json={"email": "paola@example.com", "password": "secreta123"},
    )
    assert resp.status_code == 409


@pytest.mark.anyio
async def test_create_user_short_password(admin_client, db_mock):
    resp = await admin_client.post(
        "/api/users",
        json={"email": "nuevo@example.com", "password": "short"},
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_reset_password_not_found(admin_client, db_mock):
    db_mock.execute.return_value = _make_result(scalar=None)
    resp = await admin_client.post(
        f"/api/users/{uuid.uuid4()}/reset-password",
        json={"new_password": "nuevaclave123"},
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_reset_password_short(admin_client, db_mock):
    resp = await admin_client.post(
        f"/api/users/{uuid.uuid4()}/reset-password",
        json={"new_password": "corta"},
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_update_user_not_found(admin_client, db_mock):
    db_mock.execute.return_value = _make_result(scalar=None)
    resp = await admin_client.patch(
        f"/api/users/{uuid.uuid4()}",
        json={"role": "member"},
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_me_endpoint_requires_auth(anon_client):
    resp = await anon_client.get("/api/users/me")
    assert resp.status_code == 403
