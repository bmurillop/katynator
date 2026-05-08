from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt

from app.config import settings

_ALGORITHM = "HS256"


def _payload(user_id: str, token_version: int, token_type: str, ttl: timedelta) -> dict[str, Any]:
    return {
        "sub": user_id,
        "token_version": token_version,
        "type": token_type,
        "exp": datetime.now(timezone.utc) + ttl,
    }


def create_access_token(user_id: str, token_version: int) -> str:
    return jwt.encode(
        _payload(user_id, token_version, "access", timedelta(minutes=settings.jwt_access_ttl_minutes)),
        settings.secret_key,
        algorithm=_ALGORITHM,
    )


def create_refresh_token(user_id: str, token_version: int) -> str:
    return jwt.encode(
        _payload(user_id, token_version, "refresh", timedelta(days=settings.jwt_refresh_ttl_days)),
        settings.secret_key,
        algorithm=_ALGORITHM,
    )


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.secret_key, algorithms=[_ALGORITHM])
