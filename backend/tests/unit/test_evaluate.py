"""Tests for the Phase 1 evaluation harness."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.evaluate import evaluate
from tests.fixtures.pdf_factory import schedule_pdf


def test_evaluate_perfect_match(tmp_path: Path) -> None:
    pdf_bytes = schedule_pdf(
        schedule_title="DOOR SCHEDULE",
        rows=(
            ("D01", "920", "2040", "Hinged", "Solid Core", "Entry"),
            ("D02", "820", "2040", "Hinged", "Solid Core", "Bedroom"),
        ),
        page_titles=("FLOOR PLAN", "DOOR SCHEDULE"),
    )
    (tmp_path / "plan.pdf").write_bytes(pdf_bytes)
    (tmp_path / "plan.truth.json").write_text(
        json.dumps(
            {
                "doors": {
                    "total": 2,
                    "entries": [{"id": "D01"}, {"id": "D02"}],
                },
                "windows": {"total": 0, "entries": []},
            }
        )
    )

    report = evaluate(tmp_path)
    assert report["total_plans"] == 1
    assert report["passed"] == 1
    assert report["overall_element_accuracy"] == 1.0


def test_evaluate_missing_truth_marks_failed(tmp_path: Path) -> None:
    (tmp_path / "plan.pdf").write_bytes(b"%PDF-1.4\n%fake\n")
    report = evaluate(tmp_path)
    assert report["per_plan"][0]["notes"] == "missing truth file"
    assert report["passed"] == 0
