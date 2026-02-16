"""REST API for quick notes - provides direct access to notes without going through the agent."""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.sandbox import SandboxError, resolve_sandboxed_path

router = APIRouter()


class NoteCreate(BaseModel):
    content: str
    title: str = ""
    category: str = "general"  # For health notes: exercise, nutrition, sleep, etc.


@router.get("/list")
async def list_notes(folder: str = "notes"):
    """List all note files in a folder."""
    if folder not in ("notes", "health"):
        raise HTTPException(status_code=400, detail="Folder must be 'notes' or 'health'")

    try:
        base = resolve_sandboxed_path(folder)
    except SandboxError as e:
        raise HTTPException(status_code=403, detail=str(e))

    if not base.exists():
        return {"folder": folder, "files": []}

    files = []
    for item in sorted(base.rglob("*.md"), reverse=True):
        rel = item.relative_to(base)
        files.append({
            "path": f"{folder}/{rel}",
            "name": str(rel),
            "modified": datetime.fromtimestamp(item.stat().st_mtime, tz=timezone.utc).isoformat(),
        })

    return {"folder": folder, "files": files}


@router.get("/read")
async def read_note(path: str):
    """Read a specific note file."""
    try:
        file_path = resolve_sandboxed_path(path)
    except SandboxError as e:
        raise HTTPException(status_code=403, detail=str(e))

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Note not found")

    return {"path": path, "content": file_path.read_text()}


@router.post("/quick")
async def create_quick_note(note: NoteCreate):
    """Create a quick note in the daily notes file."""
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")

    file_path = resolve_sandboxed_path(f"notes/daily/{date_str}.md")
    file_path.parent.mkdir(parents=True, exist_ok=True)

    title = note.title or "Quick Note"
    entry = f"\n## {title} [{time_str}]\n{note.content}\n"

    if file_path.exists():
        existing = file_path.read_text()
    else:
        existing = f"# Notes - {date_str}\n"

    file_path.write_text(existing + entry)
    return {"status": "saved", "path": f"notes/daily/{date_str}.md"}


@router.post("/health")
async def create_health_note(note: NoteCreate):
    """Create a health/fitness note in the daily health log."""
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")

    file_path = resolve_sandboxed_path(f"health/{date_str}.md")
    file_path.parent.mkdir(parents=True, exist_ok=True)

    entry = f"\n### [{time_str}] {note.category}\n{note.content}\n"

    if file_path.exists():
        existing = file_path.read_text()
    else:
        existing = f"# Health Log - {date_str}\n"

    file_path.write_text(existing + entry)
    return {"status": "saved", "path": f"health/{date_str}.md"}
