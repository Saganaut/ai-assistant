"""Agent orchestration - handles multi-step tool use with the LLM."""

import json
import logging
from typing import AsyncIterator

from google import genai
from google.genai import types

from app.core.config import settings
from app.services.tools.registry import ToolRegistry, create_default_registry

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a helpful personal AI assistant running on a home server.
You have access to various tools to help the user manage their life.

Available capabilities:
- Read, write, list, and search files in a sandboxed data directory
- Take health and fitness notes organized by date
- Take quick notes on any topic
- Browse the web and fetch page content
- Search the web for current information
- Save bookmarks with summaries

When the user asks you to do something that requires a tool, use the appropriate tool.
You can chain multiple tools together to accomplish complex tasks.
Always be concise and helpful. When you use a tool, briefly explain what you did."""


class Agent:
    """Agent that orchestrates LLM + tools for multi-step interactions."""

    def __init__(self, registry: ToolRegistry | None = None):
        self.registry = registry or create_default_registry()
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = "gemini-2.0-flash"

    def _build_tools(self) -> list[types.Tool]:
        declarations = self.registry.gemini_declarations()
        return [types.Tool(function_declarations=declarations)]

    async def run(self, messages: list[dict]) -> AsyncIterator[str]:
        """Run the agent with tool use. Yields text tokens as they stream.

        Messages should be in Gemini format: [{"role": "user", "parts": [{"text": "..."}]}]
        """
        tools = self._build_tools()
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=tools,
        )

        contents = [types.Content(**m) for m in messages]

        max_iterations = 10
        for iteration in range(max_iterations):
            # Log request details before API call
            msg_summary = []
            for c in contents:
                role = c.role if hasattr(c, 'role') else '?'
                parts_text = []
                if hasattr(c, 'parts') and c.parts:
                    for p in c.parts:
                        if hasattr(p, 'text') and p.text:
                            parts_text.append(p.text[:200])
                        elif hasattr(p, 'function_call') and p.function_call:
                            parts_text.append(f"[call:{p.function_call.name}]")
                        elif hasattr(p, 'function_response') and p.function_response:
                            parts_text.append(f"[result:{p.function_response.name}]")
                msg_summary.append(f"  {role}: {' | '.join(parts_text)}")

            tool_names = [d["name"] for d in self.registry.gemini_declarations()]
            logger.info(
                f"=== LLM API Call (iteration {iteration + 1}/{max_iterations}) ===\n"
                f"  Model: {self.model}\n"
                f"  Tools: {len(tool_names)} ({', '.join(tool_names)})\n"
                f"  Messages ({len(contents)}):\n" + "\n".join(msg_summary)
            )

            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )

            # Log response token usage
            usage = response.usage_metadata
            if usage:
                logger.info(
                    f"=== LLM Response ===\n"
                    f"  Prompt tokens: {usage.prompt_token_count}\n"
                    f"  Response tokens: {usage.candidates_token_count}\n"
                    f"  Total tokens: {usage.total_token_count}"
                )

            # Check if the response has function calls
            has_function_calls = False
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if part.function_call:
                        has_function_calls = True

            if not has_function_calls:
                # No tool calls - yield the text response
                if response.text:
                    logger.info(f"  Response text: {response.text[:300]}")
                    yield response.text
                return

            # Process function calls
            contents.append(response.candidates[0].content)
            function_responses = []

            for part in response.candidates[0].content.parts:
                if part.function_call:
                    fc = part.function_call
                    tool_name = fc.name
                    tool_args = dict(fc.args) if fc.args else {}

                    logger.info(f"Tool call: {tool_name}({tool_args})")
                    yield f"\n[Using tool: {tool_name}]\n"

                    tool = self.registry.get(tool_name)
                    if tool:
                        try:
                            result = await tool.execute(**tool_args)
                        except Exception as e:
                            result = f"Error executing {tool_name}: {e}"
                    else:
                        result = f"Unknown tool: {tool_name}"

                    function_responses.append(
                        types.Part(function_response=types.FunctionResponse(
                            name=tool_name,
                            response={"result": result},
                        ))
                    )

            # Add tool results back to the conversation
            contents.append(types.Content(role="function", parts=function_responses))

        yield "\n[Agent reached maximum iterations]"

    async def run_stream(self, messages: list[dict]) -> AsyncIterator[str]:
        """Alias for run() - both support streaming."""
        async for token in self.run(messages):
            yield token
