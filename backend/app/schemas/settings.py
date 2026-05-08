from typing import Literal, Optional

from pydantic import BaseModel


class SettingsOut(BaseModel):
    ai_provider: str
    imap_poll_interval_minutes: int


class SettingsPatch(BaseModel):
    ai_provider: Optional[Literal["gemini", "claude", "lmstudio"]] = None
    imap_poll_interval_minutes: Optional[int] = None


class TestAIResult(BaseModel):
    provider: str
    status: Literal["ok", "error"]
    latency_ms: int
    transaction_count: int = 0
    error: Optional[str] = None
