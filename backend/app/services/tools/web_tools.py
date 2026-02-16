"""Web browsing and search tools for the agent."""

import re
from typing import Any

import httpx

from app.services.tools.base import BaseTool, ToolDefinition, ToolParameter


class WebBrowseTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="web_browse",
            description="Fetch a web page and return its text content. Useful for reading articles, documentation, or any URL.",
            parameters=[
                ToolParameter(name="url", type="string", description="The URL to fetch"),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        url = kwargs["url"]
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
                response = await client.get(url, headers={"User-Agent": "AI-Assistant/0.1"})
                response.raise_for_status()
                content = response.text
        except httpx.HTTPError as e:
            return f"Error fetching {url}: {e}"

        # Strip HTML tags for a rough text extraction
        text = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()

        # Truncate to avoid overwhelming the LLM context
        max_chars = 8000
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n... (content truncated)"

        return f"Content from {url}:\n\n{text}"


class WebSearchTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="web_search",
            description="Search the web using DuckDuckGo and return results. Use this to find current information.",
            parameters=[
                ToolParameter(name="query", type="string", description="The search query"),
                ToolParameter(
                    name="num_results", type="integer",
                    description="Number of results to return (default 5, max 10)",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        query = kwargs["query"]
        num = min(kwargs.get("num_results", 5), 10)

        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
                # Use DuckDuckGo HTML search
                response = await client.get(
                    "https://html.duckduckgo.com/html/",
                    params={"q": query},
                    headers={"User-Agent": "AI-Assistant/0.1"},
                )
                response.raise_for_status()
                html = response.text
        except httpx.HTTPError as e:
            return f"Search error: {e}"

        # Parse results from DuckDuckGo HTML
        results = []
        result_blocks = re.findall(
            r'<a rel="nofollow" class="result__a" href="([^"]+)"[^>]*>(.*?)</a>.*?'
            r'<a class="result__snippet"[^>]*>(.*?)</a>',
            html, re.DOTALL,
        )

        for href, title, snippet in result_blocks[:num]:
            title = re.sub(r'<[^>]+>', '', title).strip()
            snippet = re.sub(r'<[^>]+>', '', snippet).strip()
            results.append(f"- {title}\n  {href}\n  {snippet}")

        if not results:
            return f"No results found for: {query}"

        return f"Search results for '{query}':\n\n" + "\n\n".join(results)


class SaveBookmarkTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="save_bookmark",
            description="Save a URL as a bookmark with a title and optional summary to the bookmarks file.",
            parameters=[
                ToolParameter(name="url", type="string", description="The URL to bookmark"),
                ToolParameter(name="title", type="string", description="Title for the bookmark"),
                ToolParameter(name="summary", type="string", description="Brief summary of the content", required=False),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        from app.core.sandbox import resolve_sandboxed_path

        url = kwargs["url"]
        title = kwargs["title"]
        summary = kwargs.get("summary", "")

        bookmarks_path = resolve_sandboxed_path("bookmarks.md")
        bookmarks_path.parent.mkdir(parents=True, exist_ok=True)

        entry = f"\n## [{title}]({url})\n"
        if summary:
            entry += f"{summary}\n"
        entry += "\n---\n"

        if bookmarks_path.exists():
            existing = bookmarks_path.read_text()
        else:
            existing = "# Bookmarks\n"

        bookmarks_path.write_text(existing + entry)
        return f"Bookmark saved: {title} ({url})"
