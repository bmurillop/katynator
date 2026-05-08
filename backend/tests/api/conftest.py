"""Shared fixtures for API route tests.

Uses httpx AsyncClient + FastAPI dependency overrides to avoid a real DB.
Auth is bypassed by overriding require_member / require_admin with stubs.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.auth.deps import get_current_user, require_admin, require_member
from app.db import get_db
from app.models.enums import UserRole
from app.models.user import User

# ── stub users ──────────────────────────────────────────────────────────────

def _stub_user(role: UserRole) -> User:
    u = MagicMock(spec=User)
    u.id = uuid.uuid4()
    u.role = role
    return u


_MEMBER = _stub_user(UserRole.member)
_ADMIN = _stub_user(UserRole.admin)


def _member_override():
    return _MEMBER


def _admin_override():
    return _ADMIN


# ── async client fixture ─────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def db_mock() -> AsyncMock:
    """A thin AsyncMock of AsyncSession that routes can call."""
    mock = AsyncMock()
    # .execute() returns a result object; callers chain .scalar_one_or_none() etc.
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    result.scalar_one.return_value = 0
    result.scalars.return_value.all.return_value = []
    mock.execute.return_value = result
    mock.flush = AsyncMock()
    mock.delete = AsyncMock()
    return mock


@pytest_asyncio.fixture
async def member_client(db_mock: AsyncMock) -> AsyncGenerator[AsyncClient, None]:
    """Authenticated as a regular member."""
    app.dependency_overrides[get_db] = lambda: db_mock
    app.dependency_overrides[require_member] = _member_override
    app.dependency_overrides[require_admin] = _admin_override
    app.dependency_overrides[get_current_user] = _member_override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_client(db_mock: AsyncMock) -> AsyncGenerator[AsyncClient, None]:
    """Authenticated as admin."""
    app.dependency_overrides[get_db] = lambda: db_mock
    app.dependency_overrides[require_member] = _member_override
    app.dependency_overrides[require_admin] = _admin_override
    app.dependency_overrides[get_current_user] = _admin_override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def anon_client() -> AsyncGenerator[AsyncClient, None]:
    """Unauthenticated client — no dependency overrides."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
