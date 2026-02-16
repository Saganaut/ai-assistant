"""Google Gemini LLM provider."""

from typing import AsyncIterator

from google import genai

from app.core.config import settings
from app.services.llm.base import BaseLLMProvider, LLMResponse, Message


class GeminiProvider(BaseLLMProvider):
    def __init__(self):
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = "gemini-2.0-flash"

    async def chat(self, messages: list[Message], tools: list[dict] | None = None) -> LLMResponse:
        contents = [{"role": m.role, "parts": [{"text": m.content}]} for m in messages]
        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
        )
        return LLMResponse(content=response.text)

    async def chat_stream(
        self, messages: list[Message], tools: list[dict] | None = None
    ) -> AsyncIterator[str]:
        contents = [{"role": m.role, "parts": [{"text": m.content}]} for m in messages]
        response = self.client.models.generate_content_stream(
            model=self.model,
            contents=contents,
        )
        for chunk in response:
            if chunk.text:
                yield chunk.text
