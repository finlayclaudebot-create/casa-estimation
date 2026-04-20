"""Tests for the Phase 1 element catalogue definitions."""

from __future__ import annotations

from app.services.catalogue.categories import (
    DOOR_CATEGORIES,
    PHASE_1_CATEGORIES,
    WINDOW_CATEGORIES,
    all_category_keys,
    get_category,
)


def test_phase_1_includes_all_addendum_categories() -> None:
    expected = {
        # Doors
        "door.external.entry",
        "door.external.sliding",
        "door.external.hinged",
        "door.external.bifold",
        "door.external.garage",
        "door.internal.hinged",
        "door.internal.cavity_slider",
        "door.internal.sliding",
        "door.internal.bifold",
        "door.internal.french",
        "door.internal.barn",
        "door.unknown",
        # Windows
        "window.awning",
        "window.casement",
        "window.sliding",
        "window.double_hung",
        "window.fixed",
        "window.louvre",
        "window.bifold",
        "window.bay",
        "window.highlight",
        "window.skylight",
        "window.unknown",
    }
    assert all_category_keys() == expected


def test_each_concrete_category_requires_dimensions() -> None:
    for cat in PHASE_1_CATEGORIES:
        if cat.category.endswith(".unknown"):
            continue
        assert cat.required_dimensions, f"{cat.category} should require dimensions"


def test_quantity_unit_each_for_phase_1() -> None:
    for cat in PHASE_1_CATEGORIES:
        assert cat.quantity_unit == "each"


def test_get_category_returns_known_definition() -> None:
    cat = get_category("door.internal.hinged")
    assert cat is not None
    assert cat.display_name == "Internal Hinged Door"


def test_get_category_returns_none_for_unknown_key() -> None:
    assert get_category("door.totally_made_up") is None


def test_door_and_window_lists_are_disjoint() -> None:
    door_keys = {c.category for c in DOOR_CATEGORIES}
    window_keys = {c.category for c in WINDOW_CATEGORIES}
    assert door_keys.isdisjoint(window_keys)
