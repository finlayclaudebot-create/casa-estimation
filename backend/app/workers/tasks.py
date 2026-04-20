"""Celery task definitions."""

from __future__ import annotations

from uuid import UUID

from app.db.session import get_sessionmaker
from app.services.takeoff.orchestrator import run_takeoff
from app.workers.celery_app import celery_app


@celery_app.task(  # type: ignore[untyped-decorator]
    name="casa.process_takeoff",
    bind=True,
    autoretry_for=(OSError,),  # transient FS/network errors
    retry_kwargs={"max_retries": 2, "countdown": 5},
    acks_late=True,
)
def process_takeoff(self: object, takeoff_id: str) -> dict[str, str]:
    _ = self  # bound task receiver; required by Celery's bind=True
    factory = get_sessionmaker()
    with factory() as session, session.begin():
        run_takeoff(session, UUID(takeoff_id))
    return {"takeoff_id": takeoff_id, "status": "done"}
