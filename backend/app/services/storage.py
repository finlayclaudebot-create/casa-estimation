"""File storage helpers (local filesystem; v1)."""

from __future__ import annotations

import shutil
from pathlib import Path
from uuid import UUID, uuid4

from app.core.config import get_settings


def plan_path(plan_id: UUID) -> Path:
    """Return the absolute path where a plan PDF should be stored."""

    settings = get_settings()
    return Path(settings.storage_root) / "plans" / f"{plan_id}.pdf"


def write_plan_bytes(content: bytes, plan_id: UUID | None = None) -> tuple[UUID, Path]:
    """Write *content* to disk under a stable plan id and return (id, path)."""

    pid = plan_id or uuid4()
    path = plan_path(pid)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return pid, path


def remove_plan_file(plan_id: UUID) -> None:
    """Delete the stored PDF for *plan_id*. No-op if it doesn't exist."""

    path = plan_path(plan_id)
    if path.exists():
        path.unlink()


def reset_storage_root() -> None:
    """Test helper: nuke and recreate the storage root."""

    settings = get_settings()
    root = Path(settings.storage_root)
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
