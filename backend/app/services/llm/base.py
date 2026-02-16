"""Abstract LLM provider interface. All providers must implement this."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator


@dataclass
class Message:
    role: str  # "user" | "assistant" | "system"
    content: str


@dataclass
class ToolCall:
    name: str
    arguments: dict


@dataclass
class LLMResponse:
    content: str
    tool_calls: list[ToolCall] | None = None


class BaseLLMProvider(ABC):
    @abstractmethod
    async def chat(self, messages: list[Message], tools: list[dict] | None = None) -> LLMResponse:
        """Send messages and get a response. Optionally with tool definitions."""
        ...

    @abstractmethod
    async def chat_stream(
        self, messages: list[Message], tools: list[dict] | None = None
    ) -> AsyncIterator[str]:
        """Stream a chat response token by token."""
        ...
