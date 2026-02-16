"""Base tool interface. All tools the agent can use implement this."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolParameter:
    name: str
    type: str  # "string" | "integer" | "boolean" | "number"
    description: str
    required: bool = True
    enum: list[str] | None = None


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: list[ToolParameter] = field(default_factory=list)

    def to_gemini_schema(self) -> dict:
        """Convert to Gemini function declaration format."""
        properties = {}
        required = []
        for param in self.parameters:
            prop: dict[str, Any] = {"type": param.type, "description": param.description}
            if param.enum:
                prop["enum"] = param.enum
            properties[param.name] = prop
            if param.required:
                required.append(param.name)

        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }


class BaseTool(ABC):
    @abstractmethod
    def definition(self) -> ToolDefinition:
        """Return the tool's definition for LLM function calling."""
        ...

    @abstractmethod
    async def execute(self, **kwargs: Any) -> str:
        """Execute the tool with the given arguments. Returns a string result."""
        ...
