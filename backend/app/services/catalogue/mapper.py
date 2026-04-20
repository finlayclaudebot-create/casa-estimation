"""Map free-text schedule rows into controlled-vocabulary categories.

Implements the deterministic rules from PHASE_1_ADDENDUM.md "How Phase 1 populates
match_keys". No fuzzy matching, no LLMs — Phase 1 is rules only.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from app.schemas.match_key import MatchKey
from app.services.catalogue.categories import get_category

ElementKind = Literal["door", "window"]


_DOOR_TYPE_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bcavity[\s\-]?slid", re.I), "door.internal.cavity_slider"),
    (re.compile(r"\bcsd\b", re.I), "door.internal.cavity_slider"),
    (re.compile(r"\bbarn\b", re.I), "door.internal.barn"),
    (re.compile(r"\bbi[\s\-]?fold", re.I), "door.internal.bifold"),
    (re.compile(r"\bfrench\b", re.I), "door.internal.french"),
    (re.compile(r"\bgarage\b", re.I), "door.external.garage"),
    (re.compile(r"\bsectional\b", re.I), "door.external.garage"),
    (re.compile(r"\bsliding\b", re.I), "door.internal.sliding"),
    (re.compile(r"\bslider\b", re.I), "door.internal.sliding"),
    (re.compile(r"\bhinged\b", re.I), "door.internal.hinged"),
    (re.compile(r"\bentry\b", re.I), "door.external.entry"),
)

_DOOR_EXTERNAL_LOCATION = re.compile(
    r"\b(entry|external|outside|alfresco|patio|laundry door to outside|back door|porch)\b",
    re.I,
)

_WINDOW_TYPE_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bawning\b", re.I), "window.awning"),
    (re.compile(r"\bcasement\b", re.I), "window.casement"),
    (re.compile(r"\bsliding\b", re.I), "window.sliding"),
    (re.compile(r"\bdouble[\s\-]?hung\b", re.I), "window.double_hung"),
    (re.compile(r"\bfixed\b", re.I), "window.fixed"),
    (re.compile(r"\bpicture\b", re.I), "window.fixed"),
    (re.compile(r"\blouvre\b|\blouver\b", re.I), "window.louvre"),
    (re.compile(r"\bbi[\s\-]?fold\b", re.I), "window.bifold"),
    (re.compile(r"\bbay\b", re.I), "window.bay"),
    (re.compile(r"\bhighlight\b|\bhilite\b|\bhighlite\b", re.I), "window.highlight"),
    (re.compile(r"\bskylight\b", re.I), "window.skylight"),
)

WIDE_DOOR_THRESHOLD_MM = 2000


def map_schedule_row_to_category(
    element_type: ElementKind,
    schedule_type_text: str,
    location_text: str | None,
    width_mm: int | None,
) -> str:
    """Return a valid element_catalogue category key for *schedule_type_text*."""

    text = (schedule_type_text or "").strip()
    if element_type == "door":
        category = _map_door(text, location_text, width_mm)
        return category or "door.unknown"
    category = _map_window(text)
    return category or "window.unknown"


def _map_door(text: str, location_text: str | None, width_mm: int | None) -> str | None:
    if not text:
        return None
    location = (location_text or "").strip()
    is_external_location = bool(location and _DOOR_EXTERNAL_LOCATION.search(location))

    for pattern, category in _DOOR_TYPE_RULES:
        if not pattern.search(text):
            continue

        # Specialise sliding doors by width / location.
        if category == "door.internal.sliding":
            if (width_mm is not None and width_mm >= WIDE_DOOR_THRESHOLD_MM) or is_external_location:
                return "door.external.sliding"
            return "door.internal.sliding"

        # Specialise hinged doors by location.
        if category == "door.internal.hinged" and is_external_location:
            return "door.external.hinged"

        # Specialise bifold doors by location.
        if category == "door.internal.bifold" and is_external_location:
            return "door.external.bifold"

        return category
    return None


def _map_window(text: str) -> str | None:
    if not text:
        return None
    for pattern, category in _WINDOW_TYPE_RULES:
        if pattern.search(text):
            return category
    return None


def build_match_key(
    category: str,
    width_mm: int | None,
    height_mm: int | None,
    attributes: dict[str, Any],
    quantity_unit: str = "each",
) -> MatchKey:
    """Build and validate a MatchKey against the element_catalogue."""

    cat_def = get_category(category)
    if cat_def is None:
        raise ValueError(f"unknown catalogue category: {category!r}")

    dims: dict[str, int | None] = {}
    if width_mm is not None:
        dims["width_mm"] = width_mm
    if height_mm is not None:
        dims["height_mm"] = height_mm

    for required in cat_def.required_dimensions:
        if dims.get(required) is None:
            raise ValueError(
                f"category {category} requires dimension {required}; got {dims}"
            )

    if quantity_unit != cat_def.quantity_unit:
        raise ValueError(
            f"category {category} expects quantity_unit={cat_def.quantity_unit}, "
            f"got {quantity_unit}"
        )

    return MatchKey.model_validate(
        {
            "category": category,
            "dimensions": dims,
            "attributes": attributes,
            "quantity_unit": quantity_unit,
        }
    )
