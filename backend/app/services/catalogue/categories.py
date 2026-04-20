"""Phase 1 element catalogue definitions.

Single source of truth for the door and window categories listed in
PHASE_1_ADDENDUM.md. Both the seed script and the schedule mapper import from here
so category strings are never hardcoded in multiple places.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CategoryDef:
    category: str
    display_name: str
    quantity_unit: str
    required_dimensions: tuple[str, ...]
    optional_dimensions: tuple[str, ...] = ()
    required_attributes: tuple[str, ...] = ()
    optional_attributes: tuple[str, ...] = ()
    parent_category: str | None = None
    description: str = ""
    added_in_phase: int = 1
    aliases: tuple[str, ...] = field(default_factory=tuple)


_DOOR_DIMS = ("width_mm", "height_mm")
_WINDOW_DIMS = ("width_mm", "height_mm")
_DOOR_ATTRS = ("material", "fire_rating", "panel_count")
_WINDOW_ATTRS = ("glazing", "sill_height_mm", "energy_u_value", "energy_shgc")


DOOR_CATEGORIES: tuple[CategoryDef, ...] = (
    CategoryDef(
        category="door.external.entry",
        display_name="External Entry Door",
        quantity_unit="each",
        required_dimensions=_DOOR_DIMS,
        optional_attributes=_DOOR_ATTRS,
        description="Front/back entry door, typically 920+ wide, solid",
    ),
    CategoryDef(
        category="door.external.sliding",
        display_name="External Sliding Door",
        quantity_unit="each",
        required_dimensions=_DOOR_DIMS,
        optional_attributes=_DOOR_ATTRS,
        description="External sliding door (typically aluminium/glass, 2400+ wide)",
    ),
    CategoryDef(
        category="door.external.hinged",
        display_name="External Hinged Door",
        quantity_unit="each",
        required_dimensions=_DOOR_DIMS,
        optional_attributes=_DOOR_ATTRS,
        description="Back door, laundry door to outside",
    ),
    CategoryDef(
        category="door.external.bifold",
        display_name="External Bifold Door",
        quantity_unit="each",
        required_dimensions=_DOOR_DIMS,
        optional_attributes=_DOOR_ATTRS,
        description="External bifold door",
    ),
    CategoryDef(
        category="door.external.garage",
        display_name="Garage Door",
        quantity_unit="each",
        required_dimensions=_DOOR_DIMS,
        optional_attributes=_DOOR_ATTRS,
        description="Garage panel door (sectional/tilt)",
    ),
    CategoryDef(
        category="door.internal.hinged",
        display_name="Internal Hinged Door",
        quantity_unit="each",
        required_dimensions=_DOOR_DIMS,
        optional_attributes=_DOOR_ATTRS,
        description="Standard hinged internal door (bedroom, study, etc)",
    ),
    CategoryDef(
        category="door.internal.cavity_slider",
        display_name="Internal Cavity Slider",
        quantity_unit="each",
        required_dimensions=_DOOR_DIMS,
        optional_attributes=_DOOR_ATTRS,
        description="Cavity-sliding door (ensuite, laundry common)",
    ),
    CategoryDef(
        category="door.internal.sliding",
        display_name="Internal Sliding Door",
        quantity_unit="each",
        required_dimensions=_DOOR_DIMS,
        optional_attributes=_DOOR_ATTRS,
        description="Surface-mounted sliding door",
    ),
    CategoryDef(
        category="door.internal.bifold",
        display_name="Internal Bifold Door",
        quantity_unit="each",
        required_dimensions=_DOOR_DIMS,
        optional_attributes=_DOOR_ATTRS,
        description="Internal bifold door",
    ),
    CategoryDef(
        category="door.internal.french",
        display_name="Internal French Door",
        quantity_unit="each",
        required_dimensions=_DOOR_DIMS,
        optional_attributes=_DOOR_ATTRS,
        description="French/double hinged pair",
    ),
    CategoryDef(
        category="door.internal.barn",
        display_name="Internal Barn Door",
        quantity_unit="each",
        required_dimensions=_DOOR_DIMS,
        optional_attributes=_DOOR_ATTRS,
        description="Barn-style slider (becoming common)",
    ),
    CategoryDef(
        category="door.unknown",
        display_name="Door (Unknown Type)",
        quantity_unit="each",
        required_dimensions=(),
        optional_dimensions=_DOOR_DIMS,
        optional_attributes=_DOOR_ATTRS,
        description="Catch-all when type cannot be determined",
    ),
)

WINDOW_CATEGORIES: tuple[CategoryDef, ...] = (
    CategoryDef(
        category="window.awning",
        display_name="Awning Window",
        quantity_unit="each",
        required_dimensions=_WINDOW_DIMS,
        optional_attributes=_WINDOW_ATTRS,
        description="Hinged at top, opens outward from bottom",
    ),
    CategoryDef(
        category="window.casement",
        display_name="Casement Window",
        quantity_unit="each",
        required_dimensions=_WINDOW_DIMS,
        optional_attributes=_WINDOW_ATTRS,
        description="Hinged at side",
    ),
    CategoryDef(
        category="window.sliding",
        display_name="Sliding Window",
        quantity_unit="each",
        required_dimensions=_WINDOW_DIMS,
        optional_attributes=_WINDOW_ATTRS,
        description="Horizontal sliding window",
    ),
    CategoryDef(
        category="window.double_hung",
        display_name="Double-Hung Window",
        quantity_unit="each",
        required_dimensions=_WINDOW_DIMS,
        optional_attributes=_WINDOW_ATTRS,
        description="Vertical sliding sash (rarer in new AU homes, common in heritage)",
    ),
    CategoryDef(
        category="window.fixed",
        display_name="Fixed Window",
        quantity_unit="each",
        required_dimensions=_WINDOW_DIMS,
        optional_attributes=_WINDOW_ATTRS,
        description="Non-opening (picture window)",
    ),
    CategoryDef(
        category="window.louvre",
        display_name="Louvre Window",
        quantity_unit="each",
        required_dimensions=_WINDOW_DIMS,
        optional_attributes=_WINDOW_ATTRS,
        description="Louvre window",
    ),
    CategoryDef(
        category="window.bifold",
        display_name="Bifold Window",
        quantity_unit="each",
        required_dimensions=_WINDOW_DIMS,
        optional_attributes=_WINDOW_ATTRS,
        description="Window bifold (common in servery/kitchen applications)",
    ),
    CategoryDef(
        category="window.bay",
        display_name="Bay Window",
        quantity_unit="each",
        required_dimensions=_WINDOW_DIMS,
        optional_attributes=_WINDOW_ATTRS,
        description="Bay window",
    ),
    CategoryDef(
        category="window.highlight",
        display_name="Highlight Window",
        quantity_unit="each",
        required_dimensions=_WINDOW_DIMS,
        optional_attributes=_WINDOW_ATTRS,
        description="Narrow horizontal window above door/at ceiling height",
    ),
    CategoryDef(
        category="window.skylight",
        display_name="Skylight",
        quantity_unit="each",
        required_dimensions=_WINDOW_DIMS,
        optional_attributes=_WINDOW_ATTRS,
        description="Roof-mounted (technically not a window but schedules sometimes include)",
    ),
    CategoryDef(
        category="window.unknown",
        display_name="Window (Unknown Type)",
        quantity_unit="each",
        required_dimensions=(),
        optional_dimensions=_WINDOW_DIMS,
        optional_attributes=_WINDOW_ATTRS,
        description="Catch-all when type cannot be determined",
    ),
)

PHASE_1_CATEGORIES: tuple[CategoryDef, ...] = DOOR_CATEGORIES + WINDOW_CATEGORIES

CATEGORY_INDEX: dict[str, CategoryDef] = {c.category: c for c in PHASE_1_CATEGORIES}


def get_category(key: str) -> CategoryDef | None:
    return CATEGORY_INDEX.get(key)


def all_category_keys() -> set[str]:
    return set(CATEGORY_INDEX.keys())
