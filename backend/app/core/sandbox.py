"""Sandboxed file access - ensures all file operations stay within the data directory."""

from pathlib import Path

from app.core.config import settings


class SandboxError(Exception):
    pass


def resolve_sandboxed_path(relative_path: str) -> Path:
    """Resolve a relative path within the sandbox. Raises SandboxError if path escapes."""
    data_dir = settings.data_dir.resolve()
    resolved = (data_dir / relative_path).resolve()

    if not resolved.is_relative_to(data_dir):
        raise SandboxError(f"Path '{relative_path}' escapes the sandbox")

    return resolved


def validate_sandbox_path(absolute_path: Path) -> None:
    """Validate that an absolute path is within the sandbox."""
    data_dir = settings.data_dir.resolve()
    if not absolute_path.resolve().is_relative_to(data_dir):
        raise SandboxError(f"Path '{absolute_path}' is outside the sandbox")
