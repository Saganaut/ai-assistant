import shutil
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel

from app.core.sandbox import SandboxError, resolve_sandboxed_path

router = APIRouter()


class FileContent(BaseModel):
    path: str
    content: str


class CreateDir(BaseModel):
    path: str


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
        stat = item.stat()
        entries.append({
            "name": item.name,
            "is_dir": item.is_dir(),
            "size": stat.st_size if item.is_file() else None,
            "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
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

    try:
        content = file_path.read_text()
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File is not a text file")

    return {"path": path, "content": content}


@router.post("/write")
async def write_file(file: FileContent):
    try:
        file_path = resolve_sandboxed_path(file.path)
    except SandboxError as e:
        raise HTTPException(status_code=403, detail=str(e))

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(file.content)
    return {"path": file.path, "status": "written"}


@router.post("/upload")
async def upload_file(path: str, file: UploadFile):
    try:
        file_path = resolve_sandboxed_path(path)
    except SandboxError as e:
        raise HTTPException(status_code=403, detail=str(e))

    file_path.parent.mkdir(parents=True, exist_ok=True)
    content = await file.read()
    file_path.write_bytes(content)
    return {"path": path, "status": "uploaded", "size": len(content)}


@router.post("/mkdir")
async def make_directory(body: CreateDir):
    try:
        dir_path = resolve_sandboxed_path(body.path)
    except SandboxError as e:
        raise HTTPException(status_code=403, detail=str(e))

    dir_path.mkdir(parents=True, exist_ok=True)
    return {"path": body.path, "status": "created"}


@router.delete("/delete")
async def delete_path(path: str):
    try:
        target = resolve_sandboxed_path(path)
    except SandboxError as e:
        raise HTTPException(status_code=403, detail=str(e))

    if not target.exists():
        raise HTTPException(status_code=404, detail="Path not found")

    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()

    return {"path": path, "status": "deleted"}
