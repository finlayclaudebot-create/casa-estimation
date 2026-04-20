"""Tests for the schedule extraction service."""

from __future__ import annotations

from pathlib import Path

from app.services.pdf.schedule_parser import extract_schedules
from tests.fixtures.pdf_factory import schedule_pdf


def _write(tmp_path: Path, data: bytes, name: str = "plan.pdf") -> Path:
    p = tmp_path / name
    p.write_bytes(data)
    return p


def test_extracts_door_schedule_with_separate_dimension_columns(tmp_path: Path) -> None:
    pdf = _write(
        tmp_path,
        schedule_pdf(
            schedule_title="DOOR SCHEDULE",
            headers=("ID", "Width", "Height", "Type", "Material", "Location"),
            rows=(
                ("D01", "920", "2040", "Hinged", "Solid Core", "Entry"),
                ("D02", "820", "2040", "Hinged", "Solid Core", "Bedroom 1"),
                ("D03", "2400", "2100", "Sliding", "Aluminium/Glass", "Living"),
                ("D04", "820", "2040", "Cavity Slider", "Solid Core", "Ensuite"),
            ),
            page_titles=("FLOOR PLAN", "DOOR SCHEDULE"),
        ),
    )

    result = extract_schedules(pdf, schedule_pages=[2])
    assert result.status == "ok"
    assert len(result.doors) == 4
    by_id = {d.schedule_id: d for d in result.doors}
    assert by_id["D01"].width_mm == 920
    assert by_id["D03"].match_key.category == "door.external.sliding"
    assert by_id["D04"].match_key.category == "door.internal.cavity_slider"


def test_extracts_window_schedule(tmp_path: Path) -> None:
    pdf = _write(
        tmp_path,
        schedule_pdf(
            schedule_title="WINDOW SCHEDULE",
            headers=("ID", "Width", "Height", "Type", "Glazing", "Location"),
            rows=(
                ("W01", "1200", "900", "Sliding", "Double", "Bed 1"),
                ("W02", "600", "600", "Awning", "Single", "Ensuite"),
                ("W03", "2400", "1800", "Fixed", "Double", "Living"),
            ),
            page_titles=("FLOOR PLAN", "WINDOW SCHEDULE"),
        ),
    )

    result = extract_schedules(pdf, schedule_pages=[2])
    assert result.status == "ok"
    assert len(result.windows) == 3
    assert {w.match_key.category for w in result.windows} == {
        "window.sliding",
        "window.awning",
        "window.fixed",
    }


def test_handles_combined_size_column(tmp_path: Path) -> None:
    pdf = _write(
        tmp_path,
        schedule_pdf(
            schedule_title="DOOR SCHEDULE",
            headers=("ID", "Size", "Type", "Material", "Location"),
            rows=(
                ("D01", "920 x 2040", "Hinged", "Solid Core", "Entry"),
                ("D02", "0.82 x 2.04", "Hinged", "Solid Core", "Bedroom"),
            ),
            page_titles=("DOOR SCHEDULE",),
        ),
    )

    result = extract_schedules(pdf, schedule_pages=[1])
    assert result.status == "ok"
    by_id = {d.schedule_id: d for d in result.doors}
    assert by_id["D01"].width_mm == 920
    assert by_id["D02"].width_mm == 820  # converted from 0.82 m
    assert by_id["D02"].height_mm == 2040


def test_handles_unknown_door_type(tmp_path: Path) -> None:
    pdf = _write(
        tmp_path,
        schedule_pdf(
            schedule_title="DOOR SCHEDULE",
            rows=(("D99", "820", "2040", "Mystery", "?", "?"),),
            page_titles=("DOOR SCHEDULE",),
        ),
    )
    result = extract_schedules(pdf, schedule_pages=[1])
    assert len(result.doors) == 1
    assert result.doors[0].match_key.category == "door.unknown"


def test_no_schedule_pages_returns_no_schedule_found(tmp_path: Path) -> None:
    pdf = _write(tmp_path, schedule_pdf(page_titles=("FLOOR PLAN",)))
    result = extract_schedules(pdf, schedule_pages=[])
    assert result.status == "no_schedule_found"
    assert not result.doors
    assert not result.windows


def test_schedule_page_with_no_recognisable_table(tmp_path: Path) -> None:
    pdf = _write(tmp_path, schedule_pdf(page_titles=("FLOOR PLAN",)))
    result = extract_schedules(pdf, schedule_pages=[1])
    assert result.status == "no_schedule_found"
