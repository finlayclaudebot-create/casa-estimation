"""End-to-end test of the Phase 1 takeoff pipeline."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Plan, Project, Takeoff, TakeoffElement
from app.services.takeoff.orchestrator import run_takeoff
from tests.fixtures.pdf_factory import (
    raster_pdf,
    schedule_pdf,
    vector_pdf,
)


def _seed_plan(session: Session, storage_root: Path, name: str, content: bytes) -> Plan:
    project = Project(organisation_id=uuid4(), name="Test")
    # ensure parent org exists for FK
    from app.db.models import Organisation

    org = Organisation(name="Test Org")
    session.add(org)
    session.flush()
    project.organisation_id = org.id
    session.add(project)
    session.flush()

    plans_dir = storage_root / "plans"
    plans_dir.mkdir(parents=True, exist_ok=True)
    pid = uuid4()
    path = plans_dir / f"{pid}.pdf"
    path.write_bytes(content)
    plan = Plan(
        id=pid,
        project_id=project.id,
        filename=name,
        storage_path=str(path),
        file_size_bytes=len(content),
        page_count=1,
    )
    session.add(plan)
    session.flush()
    return plan


def test_happy_path_completes_with_elements(
    db_session: Session, isolated_storage: Path
) -> None:
    pdf_bytes = schedule_pdf(
        schedule_title="DOOR SCHEDULE",
        page_titles=("FLOOR PLAN", "DOOR SCHEDULE"),
    )
    plan = _seed_plan(db_session, isolated_storage, "happy.pdf", pdf_bytes)
    takeoff = Takeoff(plan_id=plan.id, status="pending")
    db_session.add(takeoff)
    db_session.flush()

    run_takeoff(db_session, takeoff.id)
    db_session.flush()

    refreshed = db_session.get(Takeoff, takeoff.id)
    assert refreshed is not None
    assert refreshed.status in {"completed", "needs_review"}
    elements = list(
        db_session.scalars(select(TakeoffElement).where(TakeoffElement.takeoff_id == takeoff.id))
    )
    assert elements, "expected at least one element"
    assert all(e.match_key.get("category") for e in elements)


def test_raster_plan_fails_gracefully(
    db_session: Session, isolated_storage: Path
) -> None:
    plan = _seed_plan(
        db_session, isolated_storage, "raster.pdf", raster_pdf(num_pages=2)
    )
    takeoff = Takeoff(plan_id=plan.id, status="pending")
    db_session.add(takeoff)
    db_session.flush()

    run_takeoff(db_session, takeoff.id)
    db_session.flush()

    refreshed = db_session.get(Takeoff, takeoff.id)
    assert refreshed is not None
    assert refreshed.status == "failed"
    assert refreshed.error_message is not None
    assert "Raster" in refreshed.error_message


def test_no_schedule_fails_gracefully(
    db_session: Session, isolated_storage: Path
) -> None:
    plan = _seed_plan(
        db_session,
        isolated_storage,
        "no_sched.pdf",
        vector_pdf(num_pages=2, text_per_page="Floor plan only"),
    )
    takeoff = Takeoff(plan_id=plan.id, status="pending")
    db_session.add(takeoff)
    db_session.flush()

    run_takeoff(db_session, takeoff.id)
    db_session.flush()

    refreshed = db_session.get(Takeoff, takeoff.id)
    assert refreshed is not None
    assert refreshed.status == "failed"
    assert "schedule" in (refreshed.error_message or "").lower()


def test_corrupt_pdf_marked_failed_not_stuck(
    db_session: Session, isolated_storage: Path
) -> None:
    bad = b"%PDF-1.4\n" + b"\x00" * 64
    plan = _seed_plan(db_session, isolated_storage, "broken.pdf", bad)
    takeoff = Takeoff(plan_id=plan.id, status="pending")
    db_session.add(takeoff)
    db_session.flush()

    run_takeoff(db_session, takeoff.id)
    db_session.flush()

    refreshed = db_session.get(Takeoff, takeoff.id)
    assert refreshed is not None
    assert refreshed.status == "failed"
    assert refreshed.completed_at is not None
