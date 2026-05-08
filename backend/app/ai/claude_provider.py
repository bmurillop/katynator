"""
Claude provider with prompt caching.

The static extraction instructions (system prompt) are cached via cache_control
so repeated document parses only bill tokens for the document text itself.
The system prompt is rebuilt once per process lifetime; the cache TTL is 5 minutes
on Anthropic's side, refreshed on each use.
"""
from __future__ import annotations

import anthropic

from app.ai.base import (
    AIProvider,
    FinancialParseResult,
    parse_llm_response,
    render_system_prompt,
)
from app.config import settings

_MODEL = "claude-haiku-4-5-20251001"
_MAX_TOKENS = 4096

_ENTITY_PROMPT = """\
Given the raw merchant or entity name below, which of the listed known entities is the best match?
Reply with ONLY the exact name from the list. If none match well, reply with the single word: none

Raw name: {raw_name}

Known entities:
{candidates}"""

_CATEGORY_PROMPT = """\
Categorize the following bank transaction description into one of the listed categories.
Reply with ONLY the exact category name from the list. If unsure, reply with the single word: none

Transaction: {description}

Categories:
{categories}"""


class ClaudeProvider(AIProvider):

    def __init__(self) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=settings.claude_api_key)
        # Render system prompt once; Anthropic caches it server-side for 5 min.
        self._system_prompt = render_system_prompt()

    async def parse_financial_document(self, text: str) -> FinancialParseResult:
        response = await self._client.messages.create(
            model=_MODEL,
            max_tokens=_MAX_TOKENS,
            system=[
                {
                    "type": "text",
                    "text": self._system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": text}],
        )
        return parse_llm_response(response.content[0].text)

    async def suggest_entity_match(
        self, raw_name: str, candidates: list[str]
    ) -> str | None:
        if not candidates:
            return None
        prompt = _ENTITY_PROMPT.format(
            raw_name=raw_name,
            candidates="\n".join(f"- {c}" for c in candidates),
        )
        response = await self._client.messages.create(
            model=_MODEL,
            max_tokens=64,
            messages=[{"role": "user", "content": prompt}],
        )
        answer = response.content[0].text.strip()
        return answer if answer in candidates else None

    async def suggest_category(
        self, description: str, available_categories: list[str]
    ) -> str | None:
        if not available_categories:
            return None
        prompt = _CATEGORY_PROMPT.format(
            description=description,
            categories="\n".join(f"- {c}" for c in available_categories),
        )
        response = await self._client.messages.create(
            model=_MODEL,
            max_tokens=64,
            messages=[{"role": "user", "content": prompt}],
        )
        answer = response.content[0].text.strip()
        return answer if answer in available_categories else None
