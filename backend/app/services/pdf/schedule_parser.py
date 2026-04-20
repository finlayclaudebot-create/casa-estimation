"""Door and window schedule extraction (PHASE_1_SPEC Task 6 + Addendum A2).

We use pdfplumber to pull tables out of pages already classified as 'schedule'.
For each row we:

* Identify the element kind (door vs window) from header keywords or row content.
* Pull schedule_id, dimensions (mm), type text, material/glazing, location.
* Build a MatchKey via app.services.catalogue.mapper.

The result is structured per the addendum so the pricing layer (Phase 4/5) can
join on the canonical category key.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import pdfplumber
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.match_key import MatchKey
from app.services.catalogue.mapper import (
    ElementKind,
    build_match_key,
    map_schedule_row_to_category,
)

# Keep these column-name lists short and intentional. Order matters: more
# specific first, so e.g. "door type" beats "type".
_HEADER_SYNONYMS: dict[str, tuple[str, ...]] = {
    "id": ("id", "mark", "ref", "no", "no.", "code"),
    "width": ("width", "w", "w.", "width (mm)", "width mm"),
    "height": ("height", "h", "h.", "height (mm)", "height mm"),
    "size": ("size", "dimensions", "w x h", "size (mm)", "size w x h"),
    "type": ("type", "door type", "window type", "description", "style"),
    "material": ("material", "finish", "construction"),
    "glazing": ("glazing", "glass", "glass type"),
    "location": ("location", "room", "where", "use"),
    "fire_rating": ("fire", "frl", "fire rating"),
    "panel_count": ("panels", "panel count"),
    "sill_height": ("sill", "sill height", "sill (mm)"),
    "u_value": ("u value", "u-value", "uw", "uw value"),
    "shgc": ("shgc",),
}

_ID_PATTERNS: dict[ElementKind, re.Pattern[str]] = {
    "door": re.compile(r"^(d|dr|door)[\-\s]?\d{1,4}$", re.I),
    "window": re.compile(r"^(w|win|window)[\-\s]?\d{1,4}$", re.I),
}

_DIMENSION_RE = re.compile(
    r"(?P<w>\d{1,5}(?:\.\d+)?)\s*[x\u00d7/]\s*(?P<h>\d{1,5}(?:\.\d+)?)",
    re.I,
)


class DoorScheduleEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schedule_id: str
    width_mm: int | None
    height_mm: int | None
    type_text: str | None
    material: str | None
    location: str | None
    fire_rating: str | None
    panel_count: int | None
    raw_row: dict[str, Any]
    match_key: MatchKey


class WindowScheduleEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schedule_id: str
    width_mm: int | None
    height_mm: int | None
    type_text: str | None
    glazing: str | None
    sill_height_mm: int | None
    energy_u_value: float | None
    energy_shgc: float | None
    location: str | None
    raw_row: dict[str, Any]
    match_key: MatchKey


class ScheduleExtractionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    doors: list[DoorScheduleEntry] = Field(default_factory=list)
    windows: list[WindowScheduleEntry] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    extraction_confidence: float = Field(ge=0, le=1, default=0.95)
    status: Literal["ok", "needs_review", "no_schedule_found"] = "ok"


@dataclass(frozen=True)
class _Header:
    """Normalised header → column index mapping for one extracted table."""

    id_col: int | None
    width_col: int | None
    height_col: int | None
    size_col: int | None
    type_col: int | None
    material_col: int | None
    glazing_col: int | None
    location_col: int | None
    fire_col: int | None
    panel_col: int | None
    sill_col: int | None
    u_col: int | None
    shgc_col: int | None
    raw: list[str]


def _normalise_header_cell(cell: str | None) -> str:
    return (cell or "").strip().lower().replace(":", "").replace("\n", " ")


def _resolve_column(header_cells: Sequence[str], synonyms: tuple[str, ...]) -> int | None:
    for idx, raw in enumerate(header_cells):
        normalised = _normalise_header_cell(raw)
        for syn in synonyms:
            if syn == normalised:
                return idx
        for syn in synonyms:
            if syn in normalised:
                return idx
    return None


def _build_header(row: Sequence[str | None]) -> _Header | None:
    cells = [(c or "") for c in row]
    norm = [_normalise_header_cell(c) for c in cells]
    id_col = _resolve_column(norm, _HEADER_SYNONYMS["id"])
    if id_col is None:
        return None
    return _Header(
        id_col=id_col,
        width_col=_resolve_column(norm, _HEADER_SYNONYMS["width"]),
        height_col=_resolve_column(norm, _HEADER_SYNONYMS["height"]),
        size_col=_resolve_column(norm, _HEADER_SYNONYMS["size"]),
        type_col=_resolve_column(norm, _HEADER_SYNONYMS["type"]),
        material_col=_resolve_column(norm, _HEADER_SYNONYMS["material"]),
        glazing_col=_resolve_column(norm, _HEADER_SYNONYMS["glazing"]),
        location_col=_resolve_column(norm, _HEADER_SYNONYMS["location"]),
        fire_col=_resolve_column(norm, _HEADER_SYNONYMS["fire_rating"]),
        panel_col=_resolve_column(norm, _HEADER_SYNONYMS["panel_count"]),
        sill_col=_resolve_column(norm, _HEADER_SYNONYMS["sill_height"]),
        u_col=_resolve_column(norm, _HEADER_SYNONYMS["u_value"]),
        shgc_col=_resolve_column(norm, _HEADER_SYNONYMS["shgc"]),
        raw=list(cells),
    )


def _normalise_to_mm(raw: str | None) -> int | None:
    """Parse a single dimension; convert metres → mm if value < 20."""

    if raw is None:
        return None
    text = raw.strip().replace(",", "")
    if not text:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)", text)
    if match is None:
        return None
    value = float(match.group(1))
    if value < 20:
        value *= 1000
    return round(value)


def _split_size(raw: str | None) -> tuple[int | None, int | None]:
    if not raw:
        return None, None
    match = _DIMENSION_RE.search(raw)
    if match is None:
        return _normalise_to_mm(raw), None
    return _normalise_to_mm(match.group("w")), _normalise_to_mm(match.group("h"))


def _detect_panel_count(text: str | None) -> int | None:
    if not text:
        return None
    match = re.search(r"(\d+)\s*panel", text, re.I)
    return int(match.group(1)) if match else None


def _classify_id(value: str) -> ElementKind | None:
    cleaned = value.strip()
    for kind, pattern in _ID_PATTERNS.items():
        if pattern.match(cleaned.replace(" ", "").replace("-", "")):
            return kind
        if pattern.match(cleaned):
            return kind
    return None


def _table_kind(header: _Header) -> ElementKind | None:
    """Infer element kind from header text alone."""

    blob = " ".join(header.raw).lower()
    if "door" in blob:
        return "door"
    if "window" in blob or "glaz" in blob:
        return "window"
    return None


def _row_kind(row: Sequence[str | None], header: _Header) -> ElementKind | None:
    if header.id_col is None:
        return None
    schedule_id = (row[header.id_col] or "").strip() if header.id_col < len(row) else ""
    return _classify_id(schedule_id)


def _cell(row: Sequence[str | None], idx: int | None) -> str | None:
    if idx is None or idx >= len(row):
        return None
    return (row[idx] or "").strip() or None


def _build_door_entry(
    row: Sequence[str | None], header: _Header
) -> DoorScheduleEntry | None:
    schedule_id = _cell(row, header.id_col)
    if not schedule_id:
        return None

    width_mm: int | None
    height_mm: int | None
    if header.width_col is not None and header.height_col is not None:
        width_mm = _normalise_to_mm(_cell(row, header.width_col))
        height_mm = _normalise_to_mm(_cell(row, header.height_col))
    else:
        width_mm, height_mm = _split_size(_cell(row, header.size_col))

    type_text = _cell(row, header.type_col)
    material = _cell(row, header.material_col)
    location = _cell(row, header.location_col)
    fire_rating = _cell(row, header.fire_col)
    panel_count = _detect_panel_count(type_text or _cell(row, header.panel_col))

    category = map_schedule_row_to_category(
        "door", type_text or "", location, width_mm
    )
    attributes: dict[str, Any] = {
        "material": material,
        "fire_rating": fire_rating,
        "panel_count": panel_count,
    }
    raw = {h: (row[i] if i < len(row) else None) for i, h in enumerate(header.raw)}
    if category == "door.unknown":
        attributes["raw_type_text"] = type_text

    match_key = build_match_key(
        category=category,
        width_mm=width_mm if not category.endswith(".unknown") else None,
        height_mm=height_mm if not category.endswith(".unknown") else None,
        attributes={k: v for k, v in attributes.items() if v is not None},
    )

    return DoorScheduleEntry(
        schedule_id=schedule_id,
        width_mm=width_mm,
        height_mm=height_mm,
        type_text=type_text,
        material=material,
        location=location,
        fire_rating=fire_rating,
        panel_count=panel_count,
        raw_row=raw,
        match_key=match_key,
    )


def _build_window_entry(
    row: Sequence[str | None], header: _Header
) -> WindowScheduleEntry | None:
    schedule_id = _cell(row, header.id_col)
    if not schedule_id:
        return None

    width_mm: int | None
    height_mm: int | None
    if header.width_col is not None and header.height_col is not None:
        width_mm = _normalise_to_mm(_cell(row, header.width_col))
        height_mm = _normalise_to_mm(_cell(row, header.height_col))
    else:
        width_mm, height_mm = _split_size(_cell(row, header.size_col))

    type_text = _cell(row, header.type_col)
    glazing = _cell(row, header.glazing_col)
    location = _cell(row, header.location_col)
    sill = _normalise_to_mm(_cell(row, header.sill_col))
    u_value = _maybe_float(_cell(row, header.u_col))
    shgc = _maybe_float(_cell(row, header.shgc_col))

    category = map_schedule_row_to_category("window", type_text or "", location, width_mm)
    attributes: dict[str, Any] = {
        "glazing": glazing,
        "sill_height_mm": sill,
        "energy_u_value": u_value,
        "energy_shgc": shgc,
    }
    raw = {h: (row[i] if i < len(row) else None) for i, h in enumerate(header.raw)}
    if category == "window.unknown":
        attributes["raw_type_text"] = type_text

    match_key = build_match_key(
        category=category,
        width_mm=width_mm if not category.endswith(".unknown") else None,
        height_mm=height_mm if not category.endswith(".unknown") else None,
        attributes={k: v for k, v in attributes.items() if v is not None},
    )

    return WindowScheduleEntry(
        schedule_id=schedule_id,
        width_mm=width_mm,
        height_mm=height_mm,
        type_text=type_text,
        glazing=glazing,
        sill_height_mm=sill,
        energy_u_value=u_value,
        energy_shgc=shgc,
        location=location,
        raw_row=raw,
        match_key=match_key,
    )


def _maybe_float(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(re.sub(r"[^0-9.\-]", "", value))
    except ValueError:
        return None


def _process_table(
    rows: Sequence[Sequence[str | None]],
    forced_kind: ElementKind | None,
) -> tuple[list[DoorScheduleEntry], list[WindowScheduleEntry], list[str]]:
    if not rows:
        return [], [], []

    header = _build_header(rows[0])
    if header is None:
        return [], [], ["table skipped: no recognisable header"]

    table_kind = forced_kind or _table_kind(header)

    doors: list[DoorScheduleEntry] = []
    windows: list[WindowScheduleEntry] = []
    warnings: list[str] = []

    for raw_row in rows[1:]:
        if not any((c or "").strip() for c in raw_row):
            continue
        kind = table_kind or _row_kind(raw_row, header)
        if kind is None:
            warnings.append(
                f"row skipped: cannot determine element kind from id "
                f"{(raw_row[header.id_col] or '') if header.id_col is not None else ''!r}"
            )
            continue
        try:
            if kind == "door":
                entry = _build_door_entry(raw_row, header)
                if entry:
                    doors.append(entry)
            else:
                window_entry = _build_window_entry(raw_row, header)
                if window_entry:
                    windows.append(window_entry)
        except ValueError as exc:
            warnings.append(f"row skipped: {exc}")

    return doors, windows, warnings


def extract_schedules(
    pdf_path: Path,
    schedule_pages: Iterable[int],
) -> ScheduleExtractionResult:
    """Extract door and window schedules from the requested 1-indexed pages."""

    pages = sorted(set(schedule_pages))
    if not pages:
        return ScheduleExtractionResult(
            warnings=["no schedule pages provided"],
            status="no_schedule_found",
            extraction_confidence=0.0,
        )

    doors: list[DoorScheduleEntry] = []
    windows: list[WindowScheduleEntry] = []
    warnings: list[str] = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_no in pages:
            if page_no < 1 or page_no > len(pdf.pages):
                warnings.append(f"page {page_no} out of range")
                continue
            page = pdf.pages[page_no - 1]
            page_label = (page.extract_text() or "").lower()
            forced_kind: ElementKind | None = None
            if "window schedule" in page_label and "door schedule" not in page_label:
                forced_kind = "window"
            elif "door schedule" in page_label and "window schedule" not in page_label:
                forced_kind = "door"

            for table in page.extract_tables() or []:
                d, w, warn = _process_table(table, forced_kind)
                doors.extend(d)
                windows.extend(w)
                warnings.extend(warn)

    if not doors and not windows:
        return ScheduleExtractionResult(
            warnings=warnings or ["no schedule rows extracted"],
            status="no_schedule_found",
            extraction_confidence=0.0,
        )

    status: Literal["ok", "needs_review"] = "needs_review" if warnings else "ok"
    confidence = 0.95 if status == "ok" else 0.7
    return ScheduleExtractionResult(
        doors=doors,
        windows=windows,
        warnings=warnings,
        extraction_confidence=confidence,
        status=status,
    )
