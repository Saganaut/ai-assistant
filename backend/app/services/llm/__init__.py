"""LLM provider factory."""

from app.core.config import settings
from app.services.llm.base import BaseLLMProvider


def get_llm_provider() -> BaseLLMProvider:
    """Factory function that returns the configured LLM provider."""
    if settings.llm_provider == "gemini":
        from app.services.llm.gemini import GeminiProvider
        return GeminiProvider()
    else:
        raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")
