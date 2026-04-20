"""HTTP-level checks for /takeoffs endpoints."""

from __future__ import annotations

import io
from pathlib import Path

from fastapi.testclient import TestClient

from app.db.models import Takeoff
from app.services.takeoff.orchestrator import run_takeoff
from tests.fixtures.pdf_factory import schedule_pdf


def test_trigger_then_run_then_get(
    client: TestClient, db_session, isolated_storage: Path, monkeypatch
) -> None:
    # Disable Celery enqueue so the test doesn't require a broker.
    import app.api.v1.takeoffs as takeoffs_module

    monkeypatch.setattr(
        "app.api.v1.takeoffs.get_settings", takeoffs_module.get_settings
    )

    # Upload a schedule PDF.
    upload_resp = client.post(
        "/api/v1/plans",
        files={
            "file": (
                "plan.pdf",
                io.BytesIO(schedule_pdf(page_titles=("FLOOR PLAN", "DOOR SCHEDULE"))),
                "application/pdf",
            )
        },
    )
    assert upload_resp.status_code == 201
    plan_id = upload_resp.json()["plan_id"]

    # Trigger takeoff (Celery .delay() will fail and is silently swallowed).
    trigger_resp = client.post(f"/api/v1/plans/{plan_id}/takeoff")
    assert trigger_resp.status_code == 202
    takeoff_id = trigger_resp.json()["takeoff_id"]

    # Run the orchestrator inline so we have results to inspect.
    from uuid import UUID

    run_takeoff(db_session, UUID(takeoff_id))
    db_session.commit()

    # Fetch the result.
    get_resp = client.get(f"/api/v1/takeoffs/{takeoff_id}")
    assert get_resp.status_code == 200, get_resp.text
    body = get_resp.json()
    assert body["status"] in {"completed", "needs_review"}
    assert body["door_count"] >= 1
    assert all(el["match_key"]["category"] for el in body["elements"])

    # Latest endpoint
    latest = client.get(f"/api/v1/plans/{plan_id}/takeoffs/latest")
    assert latest.status_code == 200
    assert latest.json()["id"] == takeoff_id

    # Cleanup any rows we created via the test client (TestClient runs its own
    # transaction lifecycle; the explicit Takeoff get is just a sanity check).
    from sqlalchemy import select

    found = db_session.scalar(select(Takeoff).where(Takeoff.id == UUID(takeoff_id)))
    assert found is not None
