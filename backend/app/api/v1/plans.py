"""Plan upload endpoint."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.plan import PlanCreatedResponse
from app.services.plans import (
    CorruptPdfError,
    FileTooLargeError,
    NotAPdfError,
    UploadError,
    create_plan_from_upload,
)

router = APIRouter(prefix="/plans", tags=["plans"])


@router.post(
    "",
    response_model=PlanCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_plan(
    file: Annotated[UploadFile, File(...)],
    db: Annotated[Session, Depends(get_db)],
    project_id: Annotated[UUID | None, Form()] = None,
) -> PlanCreatedResponse:
    """Accept a PDF, persist it, and create a plans row."""

    settings = get_settings()
    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="file too large",
        )

    try:
        with db.begin():
            created = create_plan_from_upload(
                db,
                filename=file.filename or "plan.pdf",
                content=content,
                project_id=project_id,
            )
    except FileTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail=str(exc)
        ) from exc
    except (NotAPdfError, CorruptPdfError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except UploadError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    return PlanCreatedResponse(
        plan_id=created.plan_id,
        filename=created.filename,
        page_count=created.page_count,
        uploaded_at=datetime.now(UTC),
    )
