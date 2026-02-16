from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.sandbox import SandboxError, resolve_sandboxed_path

router = APIRouter()


class FileContent(BaseModel):
    path: str
    content: str


@router.get("/list")
async def list_files(path: str = ""):
    try:
        dir_path = resolve_sandboxed_path(path)
    except SandboxError as e:
        raise HTTPException(status_code=403, detail=str(e))

    if not dir_path.exists():
        raise HTTPException(status_code=404, detail="Directory not found")
    if not dir_path.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")

    entries = []
    for item in sorted(dir_path.iterdir()):
        entries.append({
            "name": item.name,
            "is_dir": item.is_dir(),
            "size": item.stat().st_size if item.is_file() else None,
        })
    return {"path": path, "entries": entries}


@router.get("/read")
async def read_file(path: str):
    try:
        file_path = resolve_sandboxed_path(path)
    except SandboxError as e:
        raise HTTPException(status_code=403, detail=str(e))

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")

    return {"path": path, "content": file_path.read_text()}


@router.post("/write")
async def write_file(file: FileContent):
    try:
        file_path = resolve_sandboxed_path(file.path)
    except SandboxError as e:
        raise HTTPException(status_code=403, detail=str(e))

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(file.content)
    return {"path": file.path, "status": "written"}
