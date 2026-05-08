import time
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import AIParseError
from app.ai.factory import get_active_provider
from app.auth.deps import get_current_user, require_admin
from app.config import settings
from app.db import get_db
from app.models.app_settings import AppSettings
from app.models.user import User
from app.schemas.settings import SettingsOut, SettingsPatch, TestAIResult

logger = logging.getLogger(__name__)
router = APIRouter()

_TEST_DOCUMENT = (
    "Estado de cuenta de prueba. "
    "Fecha: 01/01/2025. Monto: 1000 CRC. Débito. Comercio: PRUEBA SA."
)


@router.get("/settings", response_model=SettingsOut)
async def get_settings(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SettingsOut:
    rows = (await db.execute(
        select(AppSettings).where(AppSettings.key.in_(["ai_provider", "imap_poll_interval_minutes"]))
    )).scalars().all()
    overrides = {r.key: r.value for r in rows}

    return SettingsOut(
        ai_provider=overrides.get("ai_provider") or settings.ai_provider or "gemini",
        imap_poll_interval_minutes=int(
            overrides.get("imap_poll_interval_minutes") or settings.imap_poll_interval_minutes
        ),
    )


@router.patch("/settings", response_model=SettingsOut)
async def update_settings(
    body: SettingsPatch,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> SettingsOut:
    updates: dict[str, str] = {}
    if body.ai_provider is not None:
        updates["ai_provider"] = body.ai_provider
    if body.imap_poll_interval_minutes is not None:
        updates["imap_poll_interval_minutes"] = str(body.imap_poll_interval_minutes)

    if not updates:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No fields to update")

    for key, value in updates.items():
        stmt = pg_insert(AppSettings).values(key=key, value=value, updated_at=func.now())
        stmt = stmt.on_conflict_do_update(
            index_elements=["key"],
            set_={"value": value, "updated_at": func.now()},
        )
        await db.execute(stmt)

    await db.commit()
    return await get_settings(db=db, _=_)


@router.post("/settings/test-ai", response_model=TestAIResult)
async def test_ai(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TestAIResult:
    provider = await get_active_provider(db)
    provider_name = type(provider).__name__.replace("Provider", "").lower()

    start = time.monotonic()
    try:
        result = await provider.parse_financial_document(_TEST_DOCUMENT)
        latency_ms = int((time.monotonic() - start) * 1000)
        return TestAIResult(
            provider=provider_name,
            status="ok",
            latency_ms=latency_ms,
            transaction_count=len(result.transactions),
        )
    except AIParseError as exc:
        latency_ms = int((time.monotonic() - start) * 1000)
        logger.warning("test-ai failed for provider %s: %s", provider_name, exc)
        return TestAIResult(
            provider=provider_name,
            status="error",
            latency_ms=latency_ms,
            error=str(exc),
        )
    except Exception as exc:
        latency_ms = int((time.monotonic() - start) * 1000)
        logger.warning("test-ai failed for provider %s: %s", provider_name, exc)
        return TestAIResult(
            provider=provider_name,
            status="error",
            latency_ms=latency_ms,
            error=str(exc),
        )
