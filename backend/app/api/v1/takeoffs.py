"""Takeoff endpoints: trigger processing and read status/results."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Plan, Takeoff, TakeoffElement
from app.db.session import get_db

router = APIRouter(tags=["takeoffs"])


class TriggerResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    takeoff_id: UUID
    status: str
    poll_url: str


class TakeoffElementOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    element_type: str
    element_subtype: str | None
    schedule_id: str | None
    properties: dict[str, Any] | None
    source: str
    confidence: Decimal
    status: str
    match_key: dict[str, Any]


class TakeoffOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    plan_id: UUID
    status: str
    started_at: datetime
    completed_at: datetime | None
    error_message: str | None
    total_confidence: Decimal | None
    processing_log: dict[str, Any] | None
    door_count: int
    window_count: int
    elements: list[TakeoffElementOut] = Field(default_factory=list)


def _serialise(takeoff: Takeoff, elements: list[TakeoffElement]) -> TakeoffOut:
    return TakeoffOut(
        id=takeoff.id,
        plan_id=takeoff.plan_id,
        status=takeoff.status,
        started_at=takeoff.started_at,
        completed_at=takeoff.completed_at,
        error_message=takeoff.error_message,
        total_confidence=takeoff.total_confidence,
        processing_log=takeoff.processing_log,
        door_count=sum(1 for e in elements if e.element_type == "door"),
        window_count=sum(1 for e in elements if e.element_type == "window"),
        elements=[
            TakeoffElementOut(
                id=e.id,
                element_type=e.element_type,
                element_subtype=e.element_subtype,
                schedule_id=e.schedule_id,
                properties=e.properties,
                source=e.source,
                confidence=e.confidence,
                status=e.status,
                match_key=e.match_key,
            )
            for e in elements
        ],
    )


@router.post(
    "/plans/{plan_id}/takeoff",
    response_model=TriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def trigger_takeoff(
    plan_id: UUID, db: Annotated[Session, Depends(get_db)]
) -> TriggerResponse:
    plan = db.get(Plan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="plan not found")

    takeoff = Takeoff(plan_id=plan_id, status="pending", processing_log={"steps": []})
    db.add(takeoff)
    db.flush()
    db.commit()

    settings = get_settings()
    # Enqueue the Celery task. Imported lazily so the API can boot in
    # environments without a running broker (tests).
    try:
        from app.workers.tasks import process_takeoff

        process_takeoff.delay(str(takeoff.id))
    except Exception:  # pragma: no cover - logged, not fatal for the response
        pass

    return TriggerResponse(
        takeoff_id=takeoff.id,
        status=takeoff.status,
        poll_url=f"{settings.api_prefix}/takeoffs/{takeoff.id}",
    )


@router.get("/takeoffs/{takeoff_id}", response_model=TakeoffOut)
def get_takeoff(
    takeoff_id: UUID, db: Annotated[Session, Depends(get_db)]
) -> TakeoffOut:
    takeoff = db.get(Takeoff, takeoff_id)
    if takeoff is None:
        raise HTTPException(status_code=404, detail="takeoff not found")

    elements = list(
        db.scalars(
            select(TakeoffElement)
            .where(TakeoffElement.takeoff_id == takeoff_id)
            .order_by(TakeoffElement.element_type, TakeoffElement.schedule_id)
        )
    )
    return _serialise(takeoff, elements)


@router.get("/plans/{plan_id}/takeoffs/latest", response_model=TakeoffOut)
def get_latest_takeoff_for_plan(
    plan_id: UUID, db: Annotated[Session, Depends(get_db)]
) -> TakeoffOut:
    takeoff = db.scalars(
        select(Takeoff)
        .where(Takeoff.plan_id == plan_id)
        .order_by(Takeoff.started_at.desc())
        .limit(1)
    ).first()
    if takeoff is None:
        raise HTTPException(status_code=404, detail="no takeoffs for plan")
    elements = list(
        db.scalars(
            select(TakeoffElement)
            .where(TakeoffElement.takeoff_id == takeoff.id)
            .order_by(TakeoffElement.element_type, TakeoffElement.schedule_id)
        )
    )
    return _serialise(takeoff, elements)
