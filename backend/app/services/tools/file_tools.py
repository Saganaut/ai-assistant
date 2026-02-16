"""Sandboxed file operation tools for the agent."""

from typing import Any

from app.core.sandbox import SandboxError, resolve_sandboxed_path
from app.services.tools.base import BaseTool, ToolDefinition, ToolParameter


class ReadFileTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="read_file",
            description="Read the contents of a text file from the sandboxed data directory.",
            parameters=[
                ToolParameter(name="path", type="string", description="Relative file path within the data directory"),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        path = kwargs["path"]
        try:
            file_path = resolve_sandboxed_path(path)
        except SandboxError as e:
            return f"Error: {e}"

        if not file_path.exists():
            return f"Error: File not found: {path}"
        if not file_path.is_file():
            return f"Error: Not a file: {path}"

        try:
            return file_path.read_text()
        except UnicodeDecodeError:
            return f"Error: {path} is not a text file"


class WriteFileTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="write_file",
            description="Write content to a file in the sandboxed data directory. Creates parent directories if needed.",
            parameters=[
                ToolParameter(name="path", type="string", description="Relative file path within the data directory"),
                ToolParameter(name="content", type="string", description="Content to write to the file"),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        path = kwargs["path"]
        content = kwargs["content"]
        try:
            file_path = resolve_sandboxed_path(path)
        except SandboxError as e:
            return f"Error: {e}"

        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        return f"Successfully wrote to {path}"


class ListFilesTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="list_files",
            description="List files and directories in the sandboxed data directory.",
            parameters=[
                ToolParameter(
                    name="path", type="string",
                    description="Relative directory path within the data directory. Empty string for root.",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        path = kwargs.get("path", "")
        try:
            dir_path = resolve_sandboxed_path(path)
        except SandboxError as e:
            return f"Error: {e}"

        if not dir_path.exists():
            return f"Error: Directory not found: {path}"
        if not dir_path.is_dir():
            return f"Error: Not a directory: {path}"

        entries = []
        for item in sorted(dir_path.iterdir()):
            prefix = "[DIR] " if item.is_dir() else ""
            size = f" ({item.stat().st_size} bytes)" if item.is_file() else ""
            entries.append(f"{prefix}{item.name}{size}")

        if not entries:
            return "Directory is empty"
        return "\n".join(entries)


class SearchFilesTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="search_files",
            description="Search for files by name pattern or search within file contents in the sandboxed data directory.",
            parameters=[
                ToolParameter(name="query", type="string", description="Text to search for in file names or contents"),
                ToolParameter(
                    name="search_type", type="string",
                    description="Whether to search file names or file contents",
                    enum=["name", "content"],
                ),
                ToolParameter(
                    name="path", type="string",
                    description="Subdirectory to search in. Empty for root.",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        query = kwargs["query"].lower()
        search_type = kwargs.get("search_type", "name")
        path = kwargs.get("path", "")

        try:
            base = resolve_sandboxed_path(path)
        except SandboxError as e:
            return f"Error: {e}"

        if not base.exists():
            return f"Error: Directory not found: {path}"

        results = []
        for item in base.rglob("*"):
            if search_type == "name":
                if query in item.name.lower():
                    rel = item.relative_to(resolve_sandboxed_path(""))
                    results.append(str(rel))
            elif search_type == "content" and item.is_file():
                try:
                    content = item.read_text()
                    if query in content.lower():
                        rel = item.relative_to(resolve_sandboxed_path(""))
                        # Find matching lines
                        lines = content.split("\n")
                        matches = [
                            f"  L{i + 1}: {line.strip()}"
                            for i, line in enumerate(lines)
                            if query in line.lower()
                        ][:5]  # Max 5 matches per file
                        results.append(f"{rel}\n" + "\n".join(matches))
                except (UnicodeDecodeError, PermissionError):
                    continue

            if len(results) >= 20:
                results.append("... (truncated, too many results)")
                break

        if not results:
            return "No results found"
        return "\n".join(results)
