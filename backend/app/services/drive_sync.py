"""Google Drive sync for notes - uploads notes to shared Drive folder and
generates weekly summaries."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Literal

from app.core.sandbox import resolve_sandboxed_path
from app.services.integrations.google import GoogleDriveService, GoogleService

logger = logging.getLogger(__name__)

# Shared service instances (same GoogleService as google_tools.py)
_google_service = GoogleService()
_drive = GoogleDriveService(_google_service)

# Cached root folder ID for the shared "ai-assistant" folder on Drive
_root_folder_id: str | None = None

_NOTE_FILENAMES: dict[str, str] = {
    "daily": "daily-notes.md",
    "health": "health-log.md",
}


async def _get_root_folder_id() -> str:
    """Find the shared 'ai-assistant' root folder on Drive (cached)."""
    global _root_folder_id
    if _root_folder_id:
        return _root_folder_id

    headers = await _drive._google._get_headers()
    import httpx

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{_drive.BASE_URL}/files",
            headers=headers,
            params={
                "q": "name = 'ai-assistant' and mimeType = 'application/vnd.google-apps.folder' and sharedWithMe",
                "fields": "files(id,name)",
                "pageSize": 1,
            },
        )
        resp.raise_for_status()
        files = resp.json().get("files", [])

    if not files:
        raise RuntimeError(
            "Shared 'ai-assistant' folder not found on Google Drive. "
            "Make sure the folder is shared with this account."
        )

    _root_folder_id = files[0]["id"]
    return _root_folder_id


async def sync_note_to_drive(note_type: Literal["daily", "health"], date_str: str) -> None:
    """Sync a local note file to the shared Google Drive folder.

    Creates a day subfolder (YYYY-MM-DD) and uploads/updates the note file within it.
    Failures are logged but do not propagate.
    """
    try:
        if not _google_service.is_configured:
            logger.debug("Google credentials not configured, skipping Drive sync")
            return

        # Determine local file path
        if note_type == "daily":
            local_path = resolve_sandboxed_path(f"notes/daily/{date_str}.md")
        else:
            local_path = resolve_sandboxed_path(f"health/{date_str}.md")

        if not local_path.exists():
            logger.warning(f"Note file not found for sync: {local_path}")
            return

        content = local_path.read_bytes()
        root_id = await _get_root_folder_id()

        # Find or create the day subfolder
        day_folder = await _drive.find_or_create_folder(date_str, parent_id=root_id)
        day_folder_id = day_folder["id"]

        # Check if the file already exists in the day folder
        filename = _NOTE_FILENAMES[note_type]
        existing = await _drive.list_files(query=filename, folder_id=day_folder_id, max_results=1)

        if existing:
            await _drive.update_file(existing[0]["id"], content, "text/markdown")
            logger.info(f"Updated {filename} in Drive folder {date_str}")
        else:
            await _drive.upload_file(filename, content, "text/markdown", folder_id=day_folder_id)
            logger.info(f"Uploaded {filename} to Drive folder {date_str}")

    except Exception:
        logger.exception(f"Failed to sync {note_type} note for {date_str} to Drive")


async def generate_weekly_summary() -> None:
    """Generate LLM summaries of the prior week's notes and upload to Drive."""
    try:
        if not _google_service.is_configured:
            logger.debug("Google credentials not configured, skipping weekly summary")
            return

        now = datetime.now(timezone.utc)
        # Prior week: Monday to Sunday
        last_monday = now - timedelta(days=now.weekday() + 7)
        last_sunday = last_monday + timedelta(days=6)

        # Collect notes for the week
        daily_notes: list[str] = []
        health_notes: list[str] = []

        for i in range(7):
            day = last_monday + timedelta(days=i)
            date_str = day.strftime("%Y-%m-%d")

            daily_path = resolve_sandboxed_path(f"notes/daily/{date_str}.md")
            if daily_path.exists():
                daily_notes.append(daily_path.read_text())

            health_path = resolve_sandboxed_path(f"health/{date_str}.md")
            if health_path.exists():
                health_notes.append(health_path.read_text())

        if not daily_notes and not health_notes:
            logger.info("No notes found for the prior week, skipping weekly summary")
            return

        # Build prompt for the agent
        prompt_parts = [
            "Generate a weekly summary for the week of "
            f"{last_monday.strftime('%Y-%m-%d')} to {last_sunday.strftime('%Y-%m-%d')}. "
            "Produce two sections: '## Notes Summary' and '## Health Summary'. "
            "For each, highlight key themes, patterns, and takeaways. Be concise.\n"
        ]
        if daily_notes:
            prompt_parts.append("### Daily Notes\n" + "\n---\n".join(daily_notes))
        if health_notes:
            prompt_parts.append("### Health Notes\n" + "\n---\n".join(health_notes))

        full_prompt = "\n\n".join(prompt_parts)

        # Run through the agent
        from app.services.agent import Agent

        agent = Agent()
        messages = [{"role": "user", "parts": [{"text": full_prompt}]}]
        summary = ""
        async for token in agent.run(messages):
            summary += token

        if not summary.strip():
            logger.warning("Agent returned empty weekly summary")
            return

        # Determine week number for filename
        iso_year, iso_week, _ = last_monday.isocalendar()
        week_label = f"{iso_year}-W{iso_week:02d}"

        # Save locally
        local_path = resolve_sandboxed_path(f"notes/weekly/{week_label}.md")
        local_path.parent.mkdir(parents=True, exist_ok=True)
        header = f"# Weekly Summary — {week_label}\n\n"
        local_path.write_text(header + summary)
        logger.info(f"Saved weekly summary to {local_path}")

        # Upload to Drive
        root_id = await _get_root_folder_id()
        summaries_folder = await _drive.find_or_create_folder("weekly-summaries", parent_id=root_id)
        filename = f"{week_label}.md"
        content = local_path.read_bytes()

        existing = await _drive.list_files(
            query=filename, folder_id=summaries_folder["id"], max_results=1
        )
        if existing:
            await _drive.update_file(existing[0]["id"], content, "text/markdown")
        else:
            await _drive.upload_file(
                filename, content, "text/markdown", folder_id=summaries_folder["id"]
            )

        logger.info(f"Uploaded weekly summary {filename} to Drive")

    except Exception:
        logger.exception("Failed to generate weekly summary")
