"""Integration tests for POST /api/v1/plans."""

from __future__ import annotations

import io
from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import Plan, Project


def _post_pdf(client: TestClient, name: str, data: bytes) -> object:
    return client.post(
        "/api/v1/plans",
        files={"file": (name, io.BytesIO(data), "application/pdf")},
    )


def test_upload_valid_pdf_creates_plan(
    client: TestClient, db_session: Session, vector_pdf_bytes: bytes
) -> None:
    response = _post_pdf(client, "smith.pdf", vector_pdf_bytes)
    assert response.status_code == 201, response.text
    body = response.json()
    plan_id = UUID(body["plan_id"])
    assert body["filename"] == "smith.pdf"
    assert body["page_count"] == 2

    plan = db_session.get(Plan, plan_id)
    assert plan is not None
    assert plan.file_size_bytes == len(vector_pdf_bytes)
    assert plan.page_count == 2
    assert Path(plan.storage_path).exists()
    project = db_session.get(Project, plan.project_id)
    assert project is not None
    assert project.name == "Unassigned Plans"


def test_reject_non_pdf(client: TestClient) -> None:
    response = client.post(
        "/api/v1/plans",
        files={"file": ("notes.txt", io.BytesIO(b"hello world"), "text/plain")},
    )
    assert response.status_code == 400
    assert "%PDF-" in response.json()["detail"]


def test_reject_corrupt_pdf(client: TestClient) -> None:
    # Header looks like a PDF but the rest is garbage; PyMuPDF should fail to open.
    bad = b"%PDF-1.4\n" + b"\x00" * 32
    response = _post_pdf(client, "broken.pdf", bad)
    assert response.status_code == 400
    assert "unable to open PDF" in response.json()["detail"]


def test_reject_oversized(
    client: TestClient, monkeypatch, vector_pdf_bytes: bytes
) -> None:
    from app.core.config import get_settings

    monkeypatch.setenv("MAX_UPLOAD_BYTES", "1000")
    get_settings.cache_clear()
    response = _post_pdf(client, "huge.pdf", vector_pdf_bytes * 50)
    assert response.status_code == 413


def test_no_orphan_files_when_db_insert_fails(
    db_session: Session,
    vector_pdf_bytes: bytes,
    isolated_storage: Path,
    monkeypatch,
) -> None:
    """If the DB insert raises, the stored PDF must be cleaned up."""

    import pytest as _pytest

    from app.services.plans import create_plan_from_upload

    original_flush = db_session.flush
    calls = {"n": 0}

    def failing_flush(*args: object, **kwargs: object) -> None:
        calls["n"] += 1
        if calls["n"] >= 2:  # let the org flush succeed, blow up on project flush
            raise RuntimeError("simulated DB failure")
        return original_flush(*args, **kwargs)

    monkeypatch.setattr(db_session, "flush", failing_flush)

    with _pytest.raises(RuntimeError):
        create_plan_from_upload(
            db_session, filename="x.pdf", content=vector_pdf_bytes
        )

    plans_dir = isolated_storage / "plans"
    plan_files = list(plans_dir.glob("*.pdf")) if plans_dir.exists() else []
    assert plan_files == [], f"orphan files left behind: {plan_files}"
