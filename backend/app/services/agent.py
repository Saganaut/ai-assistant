"""Agent orchestration - handles multi-step tool use with the LLM."""

import asyncio
import json
import logging
from pathlib import Path
from typing import AsyncIterator

from google import genai
from google.genai import types

from app.core.config import settings
from app.services.tools.registry import ToolRegistry, create_default_registry

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_BASE = """You are a helpful personal AI assistant running on a home server.
You have access to various tools to help the user manage their life.

Available capabilities:
- Read, write, list, and search files in a sandboxed data directory
- Take health and fitness notes organized by date
- Take quick notes on any topic
- Browse the web and fetch page content
- Search the web for current information
- Save bookmarks with summaries
- Google Calendar: list upcoming events, create new events, delete events
- Google Drive: list files, search for files
- Gmail: list recent emails, read specific emails, send emails
- GitHub: list repositories, list/create issues, read repo files, list/manage projects and project items

IMPORTANT RULES:
- When the user asks you to do something, IMMEDIATELY use the appropriate tool. Do NOT ask clarifying questions if you can figure it out from context or by calling a tool first.
- Do NOT fabricate or make up data — always call the relevant tool to get real information.
- Do NOT ask the user for project IDs, owner names, or other details you can look up yourself. Call github_projects_list or github_projects_items to find the information.
- You can chain multiple tools together to accomplish complex tasks.
- Always be concise and helpful. When you use a tool, briefly explain what you did."""

_SOURCES_FILE = settings.data_dir / "github_project_sources.json"


async def _build_system_prompt() -> str:
    """Build the system prompt with dynamic context about known projects."""
    prompt = SYSTEM_PROMPT_BASE

    # Load and resolve known projects so the LLM has direct access
    sources: list[str] = []
    if _SOURCES_FILE.exists():
        try:
            sources = json.loads(_SOURCES_FILE.read_text())
        except Exception:
            pass

    if settings.github_token:
        try:
            import httpx
            from app.services.integrations.github import GitHubService
            github = GitHubService()

            # Fetch the authenticated user's GitHub username
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.github.com/user",
                    headers=github._headers(),
                    timeout=5.0,
                )
                if resp.status_code == 200:
                    gh_username = resp.json().get("login", "")
                    if gh_username:
                        prompt += f"\n\nThe user's GitHub username is: {gh_username}"
                        prompt += (
                            f"\nWhen checking for issues assigned to the user, look for assignee \"{gh_username}\". "
                            "Items in a project board that are assigned to this user are the user's tasks."
                        )

            # Fetch accessible projects
            if sources:
                projects = await github.list_accessible_projects(extra_owners=sources)
                if projects:
                    prompt += "\n\nKnown GitHub Projects the user has access to:"
                    for p in projects:
                        if p.get("closed"):
                            continue
                        owner = (p.get("owner") or {}).get("login", "unknown")
                        title = p.get("title", "?")
                        number = p.get("number", "?")
                        node_id = p.get("id", "")
                        prompt += f'\n- "{title}" (owner: {owner}, project_number: {number}, node_id: {node_id})'
                    prompt += (
                        "\n\nWhen the user asks about their project, tasks, issues, or board, "
                        "use the projects listed above. Call github_projects_items with "
                        "owner and project_number from the list — do NOT ask the user for these details."
                    )
        except Exception as e:
            logger.debug(f"Failed to pre-fetch GitHub context for system prompt: {e}")

    return prompt


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
        system_prompt = await _build_system_prompt()
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
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
