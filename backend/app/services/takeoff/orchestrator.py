"""Phase 1 takeoff pipeline.

Wires Tasks 4, 5, and 6 together. Pure function over a SQLAlchemy session so it
can be invoked synchronously from tests and asynchronously from the Celery
worker. The function never raises — all failures are recorded on the takeoff
row instead.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Plan, PlanPage, Takeoff, TakeoffElement
from app.services.pdf.classifier import classify_pdf
from app.services.pdf.page_classifier import classify_page_types
from app.services.pdf.schedule_parser import (
    DoorScheduleEntry,
    WindowScheduleEntry,
    extract_schedules,
)

NEEDS_REVIEW_THRESHOLD = Decimal("0.8")
SCHEDULE_ELEMENT_CONFIDENCE = Decimal("0.95")


def _now() -> datetime:
    return datetime.now(UTC)


def _start_step(name: str) -> dict[str, Any]:
    return {"name": name, "status": "running", "started_at": _now().isoformat()}


def _finish_step(step: dict[str, Any], status: str, detail: dict[str, Any] | None = None) -> dict[str, Any]:
    step["status"] = status
    step["finished_at"] = _now().isoformat()
    if detail is not None:
        step["detail"] = detail
    return step


def _append_step(takeoff: Takeoff, step: dict[str, Any]) -> None:
    log = dict(takeoff.processing_log or {})
    steps = list(log.get("steps", []))
    steps.append(step)
    log["steps"] = steps
    takeoff.processing_log = log


def _persist_pages(
    session: Session, plan: Plan, page_classifications: list[Any]
) -> dict[int, UUID]:
    """Insert (or update) plan_pages rows, returning page_number → page_id."""

    existing = {
        p.page_number: p
        for p in session.scalars(
            select(PlanPage).where(PlanPage.plan_id == plan.id)
        ).all()
    }
    page_ids: dict[int, UUID] = {}
    for entry in page_classifications:
        page_no = entry.page_number
        page = existing.get(page_no)
        if page is None:
            page = PlanPage(
                plan_id=plan.id,
                page_number=page_no,
                page_type=entry.page_type,
                page_title=getattr(entry, "detected_title", None),
            )
            session.add(page)
            session.flush()
        else:
            page.page_type = entry.page_type
            page.page_title = getattr(entry, "detected_title", None) or page.page_title
        page_ids[page_no] = page.id
    return page_ids


def _persist_elements(
    session: Session,
    takeoff: Takeoff,
    doors: list[DoorScheduleEntry],
    windows: list[WindowScheduleEntry],
    schedule_page_id: UUID | None,
) -> int:
    n = 0
    for door in doors:
        properties: dict[str, Any] = {"raw_row": door.raw_row}
        for field in ("type_text", "material", "fire_rating", "panel_count", "location"):
            value = getattr(door, field)
            if value is not None:
                properties[field] = value
        session.add(
            TakeoffElement(
                takeoff_id=takeoff.id,
                element_type="door",
                element_subtype=door.match_key.category.split(".", 1)[1],
                schedule_id=door.schedule_id,
                page_id=schedule_page_id,
                properties=properties,
                source="schedule",
                confidence=SCHEDULE_ELEMENT_CONFIDENCE,
                match_key=door.match_key.model_dump(),
            )
        )
        n += 1
    for win in windows:
        properties = {"raw_row": win.raw_row}
        for field in (
            "type_text",
            "glazing",
            "sill_height_mm",
            "energy_u_value",
            "energy_shgc",
            "location",
        ):
            value = getattr(win, field)
            if value is not None:
                properties[field] = value
        session.add(
            TakeoffElement(
                takeoff_id=takeoff.id,
                element_type="window",
                element_subtype=win.match_key.category.split(".", 1)[1],
                schedule_id=win.schedule_id,
                page_id=schedule_page_id,
                properties=properties,
                source="schedule",
                confidence=SCHEDULE_ELEMENT_CONFIDENCE,
                match_key=win.match_key.model_dump(),
            )
        )
        n += 1
    return n


def run_takeoff(session: Session, takeoff_id: UUID) -> None:
    """Execute the Phase 1 pipeline against an existing takeoff row.

    Status transitions: pending → processing → (completed | needs_review | failed).
    """

    takeoff = session.get(Takeoff, takeoff_id)
    if takeoff is None:
        raise ValueError(f"takeoff {takeoff_id} not found")
    plan = session.get(Plan, takeoff.plan_id)
    if plan is None:
        takeoff.status = "failed"
        takeoff.error_message = f"plan {takeoff.plan_id} not found"
        return

    takeoff.status = "processing"
    takeoff.processing_log = {"steps": []}

    # Step 1: classify the PDF.
    step = _start_step("classify_pdf")
    try:
        classification = classify_pdf(Path(plan.storage_path))
        plan.pdf_type = classification.overall_type
        _append_step(takeoff, _finish_step(step, "succeeded", {"overall_type": classification.overall_type}))
    except Exception as exc:
        _append_step(takeoff, _finish_step(step, "failed", {"error": str(exc)}))
        takeoff.status = "failed"
        takeoff.error_message = f"PDF classification failed: {exc}"
        takeoff.completed_at = _now()
        return

    if classification.overall_type == "raster":
        takeoff.status = "failed"
        takeoff.error_message = (
            "Raster PDFs not yet supported — Phase 1 requires vector plans"
        )
        takeoff.completed_at = _now()
        return

    # Step 2: page-type classification.
    step = _start_step("classify_pages")
    try:
        page_classifications = classify_page_types(Path(plan.storage_path))
        page_ids = _persist_pages(session, plan, page_classifications)
        _append_step(
            takeoff,
            _finish_step(step, "succeeded", {"page_count": len(page_classifications)}),
        )
    except Exception as exc:
        _append_step(takeoff, _finish_step(step, "failed", {"error": str(exc)}))
        takeoff.status = "failed"
        takeoff.error_message = f"Page classification failed: {exc}"
        takeoff.completed_at = _now()
        return

    schedule_pages = [p.page_number for p in page_classifications if p.page_type == "schedule"]
    if not schedule_pages:
        takeoff.status = "failed"
        takeoff.error_message = (
            "No schedule pages detected. Phase 1 requires a door or window schedule."
        )
        takeoff.completed_at = _now()
        return

    # Step 3: extract schedules.
    step = _start_step("extract_schedules")
    try:
        result = extract_schedules(Path(plan.storage_path), schedule_pages)
    except Exception as exc:
        _append_step(takeoff, _finish_step(step, "failed", {"error": str(exc)}))
        takeoff.status = "failed"
        takeoff.error_message = f"Schedule extraction failed: {exc}"
        takeoff.completed_at = _now()
        return

    schedule_page_id = page_ids.get(schedule_pages[0])
    inserted = _persist_elements(session, takeoff, result.doors, result.windows, schedule_page_id)
    _append_step(
        takeoff,
        _finish_step(
            step,
            "succeeded",
            {
                "doors": len(result.doors),
                "windows": len(result.windows),
                "elements_inserted": inserted,
                "warnings": result.warnings,
            },
        ),
    )

    takeoff.total_confidence = Decimal(str(result.extraction_confidence))
    if result.status == "no_schedule_found":
        takeoff.status = "failed"
        takeoff.error_message = "Schedule pages were detected but no rows could be parsed."
    elif takeoff.total_confidence < NEEDS_REVIEW_THRESHOLD or result.status == "needs_review":
        takeoff.status = "needs_review"
    else:
        takeoff.status = "completed"
    takeoff.completed_at = _now()
