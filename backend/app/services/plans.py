"""Plan service: orchestrates PDF upload validation, storage, and DB insert."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Organisation, Plan, Project, User
from app.services.pdf.inspect import (
    InvalidPdfError,
    get_page_count,
    looks_like_pdf,
)
from app.services.storage import plan_path, remove_plan_file, write_plan_bytes


class UploadError(Exception):
    """Base class for plan upload errors."""


class NotAPdfError(UploadError):
    """Raised when the upload is not a PDF (by magic bytes)."""


class FileTooLargeError(UploadError):
    """Raised when the upload exceeds the configured size limit."""

    def __init__(self, size: int, limit: int):
        super().__init__(f"file size {size} exceeds limit {limit}")
        self.size = size
        self.limit = limit


class CorruptPdfError(UploadError):
    """Raised when the upload is a PDF by header but cannot be parsed."""


@dataclass(frozen=True)
class CreatedPlan:
    plan_id: UUID
    filename: str
    page_count: int


def _ensure_project(session: Session, project_id: UUID | None) -> Project:
    if project_id is not None:
        project = session.get(Project, project_id)
        if project is None:
            raise UploadError(f"project {project_id} not found")
        return project

    org = session.scalars(select(Organisation).order_by(Organisation.created_at)).first()
    if org is None:
        org = Organisation(name="Default Organisation")
        session.add(org)
        session.flush()

    placeholder = Project(organisation_id=org.id, name="Unassigned Plans")
    session.add(placeholder)
    session.flush()
    return placeholder


def _resolve_user(session: Session, user_id: UUID | None) -> UUID | None:
    if user_id is None:
        return None
    user = session.get(User, user_id)
    return user.id if user else None


def create_plan_from_upload(
    session: Session,
    *,
    filename: str,
    content: bytes,
    project_id: UUID | None = None,
    uploaded_by: UUID | None = None,
) -> CreatedPlan:
    """Validate, persist, and record a plan PDF in a single transaction."""

    settings = get_settings()
    if not looks_like_pdf(content):
        raise NotAPdfError("file does not start with %PDF- magic header")
    if len(content) > settings.max_upload_bytes:
        raise FileTooLargeError(len(content), settings.max_upload_bytes)

    plan_id = uuid4()
    _, path = write_plan_bytes(content, plan_id=plan_id)
    try:
        page_count = get_page_count(path)
    except InvalidPdfError as exc:
        remove_plan_file(plan_id)
        raise CorruptPdfError(str(exc)) from exc

    try:
        project = _ensure_project(session, project_id)
        plan = Plan(
            id=plan_id,
            project_id=project.id,
            filename=filename,
            storage_path=str(path),
            file_size_bytes=len(content),
            page_count=page_count,
            uploaded_by=_resolve_user(session, uploaded_by),
        )
        session.add(plan)
        session.flush()
    except Exception:
        remove_plan_file(plan_id)
        raise

    return CreatedPlan(plan_id=plan_id, filename=filename, page_count=page_count)


def get_storage_path(plan_id: UUID) -> str:
    return str(plan_path(plan_id))
