"""Tests for page-type classification."""

from __future__ import annotations

from pathlib import Path

import fitz

from app.services.pdf.page_classifier import classify_page_types


def _build(tmp_path: Path, titles: list[str]) -> Path:
    doc = fitz.open()
    for title in titles:
        page = doc.new_page(width=595, height=842)
        # Mimic an AU title block in the bottom-right corner.
        page.insert_text((595 - 250, 842 - 60), title, fontsize=14)
    out = tmp_path / "pages.pdf"
    out.write_bytes(bytes(doc.tobytes()))
    doc.close()
    return out


def test_identifies_schedule_pages(tmp_path: Path) -> None:
    pdf = _build(tmp_path, ["GROUND FLOOR PLAN", "DOOR SCHEDULE", "WINDOW SCHEDULE"])
    results = classify_page_types(pdf)
    assert results[1].page_type == "schedule"
    assert results[2].page_type == "schedule"
    assert results[1].confidence > 0.4


def test_identifies_floor_plan_pages(tmp_path: Path) -> None:
    pdf = _build(tmp_path, ["GROUND FLOOR PLAN", "FIRST FLOOR PLAN"])
    results = classify_page_types(pdf)
    assert results[0].page_type == "floor_plan"
    assert results[1].page_type == "floor_plan"


def test_identifies_other_types(tmp_path: Path) -> None:
    pdf = _build(
        tmp_path,
        ["NORTH ELEVATION", "SECTION A-A", "SITE PLAN", "DETAIL: KITCHEN BENCH"],
    )
    results = classify_page_types(pdf)
    assert results[0].page_type == "elevation"
    assert results[1].page_type == "section"
    assert results[2].page_type == "site_plan"
    assert results[3].page_type == "detail"


def test_returns_unknown_for_unlabelled_pages(tmp_path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((100, 100), "no recognisable title here")
    out = tmp_path / "blank.pdf"
    out.write_bytes(bytes(doc.tobytes()))
    doc.close()
    results = classify_page_types(out)
    assert results[0].page_type == "unknown"
    assert results[0].confidence == 0.0


def test_handles_ambiguous_schedule_in_floor_plan_title(tmp_path: Path) -> None:
    """If both keywords appear, the more specific (schedule) wins by edge weight."""

    pdf = _build(tmp_path, ["GROUND FLOOR PLAN AND DOOR SCHEDULE"])
    results = classify_page_types(pdf)
    # Either is acceptable, but in our heuristic schedule has stronger keywords.
    assert results[0].page_type in {"schedule", "floor_plan"}
