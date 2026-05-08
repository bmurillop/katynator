from __future__ import annotations

import google.generativeai as genai

from app.ai.base import AIProvider, FinancialParseResult, parse_llm_response, render_prompt
from app.config import settings

_MODEL = "gemini-1.5-flash"

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


class GeminiProvider(AIProvider):

    def __init__(self) -> None:
        genai.configure(api_key=settings.gemini_api_key)
        self._model = genai.GenerativeModel(_MODEL)

    async def parse_financial_document(self, text: str) -> FinancialParseResult:
        prompt = render_prompt(text)
        response = await self._model.generate_content_async(
            prompt,
            generation_config=genai.GenerationConfig(temperature=0),
        )
        return parse_llm_response(response.text)

    async def suggest_entity_match(
        self, raw_name: str, candidates: list[str]
    ) -> str | None:
        if not candidates:
            return None
        prompt = _ENTITY_PROMPT.format(
            raw_name=raw_name,
            candidates="\n".join(f"- {c}" for c in candidates),
        )
        response = await self._model.generate_content_async(
            prompt,
            generation_config=genai.GenerationConfig(temperature=0),
        )
        answer = response.text.strip()
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
        response = await self._model.generate_content_async(
            prompt,
            generation_config=genai.GenerationConfig(temperature=0),
        )
        answer = response.text.strip()
        return answer if answer in available_categories else None
