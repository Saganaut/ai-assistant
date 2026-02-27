"""Note-taking tools for the agent including health/fitness notes."""

from datetime import datetime, timezone
from typing import Any

from app.core.sandbox import resolve_sandboxed_path
from app.services.drive_sync import sync_note_to_drive
from app.services.tools.base import BaseTool, ToolDefinition, ToolParameter


class HealthNoteTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="health_note",
            description="Log a health or fitness note. Notes are organized by date in the health/ folder.",
            parameters=[
                ToolParameter(name="content", type="string", description="The health/fitness note to log"),
                ToolParameter(
                    name="category", type="string",
                    description="Category for the note",
                    required=False,
                    enum=["general", "exercise", "nutrition", "sleep", "weight", "mood", "symptoms"],
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        content = kwargs["content"]
        category = kwargs.get("category", "general")
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M")

        file_path = resolve_sandboxed_path(f"health/{date_str}.md")
        file_path.parent.mkdir(parents=True, exist_ok=True)

        entry = f"\n### [{time_str}] {category}\n{content}\n"

        if file_path.exists():
            existing = file_path.read_text()
        else:
            existing = f"# Health Log - {date_str}\n"

        file_path.write_text(existing + entry)
        await sync_note_to_drive("health", date_str)
        return f"Health note logged ({category}) for {date_str} at {time_str}"


class QuickNoteTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="quick_note",
            description="Save a quick note. Notes are stored in the notes/ folder, organized by date or custom path.",
            parameters=[
                ToolParameter(name="content", type="string", description="The note content"),
                ToolParameter(name="title", type="string", description="Short title for the note"),
                ToolParameter(
                    name="path", type="string",
                    description="Custom path within notes/ folder (e.g., 'projects/ideas.md'). If not provided, saves to daily note.",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        content = kwargs["content"]
        title = kwargs["title"]
        custom_path = kwargs.get("path", "")
        now = datetime.now(timezone.utc)
        time_str = now.strftime("%H:%M")

        if custom_path:
            file_path = resolve_sandboxed_path(f"notes/{custom_path}")
        else:
            date_str = now.strftime("%Y-%m-%d")
            file_path = resolve_sandboxed_path(f"notes/daily/{date_str}.md")

        file_path.parent.mkdir(parents=True, exist_ok=True)

        entry = f"\n## {title} [{time_str}]\n{content}\n"

        if file_path.exists():
            existing = file_path.read_text()
        else:
            header = f"# Notes - {file_path.stem}\n"
            existing = header

        file_path.write_text(existing + entry)
        if not custom_path:
            await sync_note_to_drive("daily", date_str)
        return f"Note saved: {title}"


class ReadNotesTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="read_notes",
            description="Read notes from the notes/ or health/ folder. Can read a specific file or list available notes.",
            parameters=[
                ToolParameter(
                    name="path", type="string",
                    description="Path to read (e.g., 'notes/daily/2026-02-16.md' or 'health/2026-02-16.md'). Leave empty to list available note files.",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        path = kwargs.get("path", "")

        if path:
            file_path = resolve_sandboxed_path(path)
            if not file_path.exists():
                return f"Note not found: {path}"
            return file_path.read_text()

        # List available notes
        entries = []
        for folder in ["notes", "health"]:
            try:
                folder_path = resolve_sandboxed_path(folder)
                if folder_path.exists():
                    for item in sorted(folder_path.rglob("*.md")):
                        rel = item.relative_to(resolve_sandboxed_path(""))
                        entries.append(str(rel))
            except Exception:
                continue

        if not entries:
            return "No notes found"
        return "Available notes:\n" + "\n".join(f"- {e}" for e in entries)
