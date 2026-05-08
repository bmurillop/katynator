"""
ProviderFactory — resolves and caches AIProvider instances.

Resolution order (runtime, no restart needed):
  1. app_settings DB key "ai_provider"  (user changed it in UI)
  2. AI_PROVIDER env var                (set at container start)
  3. "gemini"                           (hard default)

Providers are lazily instantiated and cached as singletons keyed by name.
Switching providers in the DB just starts using a different cached instance.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import AIProvider
from app.config import settings
from app.models.app_settings import AppSettings

_cache: dict[str, AIProvider] = {}


def get_provider_by_name(name: str) -> AIProvider:
    """
    Synchronous factory — returns a cached provider by name.
    Used by the parse_pdf CLI and by get_active_provider().
    """
    if name not in _cache:
        _cache[name] = _create(name)
    return _cache[name]


async def get_active_provider(db: AsyncSession) -> AIProvider:
    """
    Async factory — reads the active provider name from the DB (with env fallback)
    then delegates to get_provider_by_name().
    Accepts an existing AsyncSession so the caller's session is reused (no extra connection).
    """
    row = (
        await db.execute(
            select(AppSettings).where(AppSettings.key == "ai_provider")
        )
    ).scalar_one_or_none()

    name = (row.value if row else None) or settings.ai_provider or "gemini"
    return get_provider_by_name(name)


def _create(name: str) -> AIProvider:
    if name == "gemini":
        from app.ai.gemini_provider import GeminiProvider
        return GeminiProvider()
    if name == "claude":
        from app.ai.claude_provider import ClaudeProvider
        return ClaudeProvider()
    if name == "lmstudio":
        from app.ai.lmstudio_provider import LMStudioProvider
        return LMStudioProvider()
    raise ValueError(f"Unknown AI provider: {name!r}. Valid options: gemini, claude, lmstudio")
