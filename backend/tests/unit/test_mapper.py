"""Tests for the schedule → catalogue category mapper."""

from __future__ import annotations

import pytest

from app.services.catalogue.mapper import (
    build_match_key,
    map_schedule_row_to_category,
)


def test_maps_hinged_internal_door() -> None:
    cat = map_schedule_row_to_category("door", "Hinged", location_text="Bedroom 1", width_mm=820)
    assert cat == "door.internal.hinged"


def test_maps_hinged_external_door_by_location() -> None:
    cat = map_schedule_row_to_category("door", "Hinged", location_text="Entry", width_mm=920)
    assert cat == "door.external.entry" or cat == "door.external.hinged"


def test_maps_sliding_door_external_when_wide() -> None:
    cat = map_schedule_row_to_category(
        "door", "Sliding", location_text="Living", width_mm=2400
    )
    assert cat == "door.external.sliding"


def test_maps_sliding_door_internal_when_narrow() -> None:
    cat = map_schedule_row_to_category(
        "door", "Sliding", location_text="Robe", width_mm=820
    )
    assert cat == "door.internal.sliding"


def test_maps_cavity_slider() -> None:
    cat = map_schedule_row_to_category("door", "Cavity Slider", location_text="Ensuite", width_mm=820)
    assert cat == "door.internal.cavity_slider"


def test_maps_csd_alias() -> None:
    cat = map_schedule_row_to_category("door", "CSD", location_text="Laundry", width_mm=820)
    assert cat == "door.internal.cavity_slider"


def test_maps_garage_door() -> None:
    cat = map_schedule_row_to_category("door", "Sectional garage door", location_text=None, width_mm=2400)
    assert cat == "door.external.garage"


def test_maps_unknown_door_type_to_door_unknown() -> None:
    cat = map_schedule_row_to_category("door", "Vault portcullis", location_text=None, width_mm=900)
    assert cat == "door.unknown"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Awning", "window.awning"),
        ("Casement", "window.casement"),
        ("Sliding", "window.sliding"),
        ("Double Hung", "window.double_hung"),
        ("Fixed", "window.fixed"),
        ("Picture", "window.fixed"),
        ("Louvre", "window.louvre"),
        ("Bi-fold", "window.bifold"),
        ("Bay", "window.bay"),
        ("Highlight", "window.highlight"),
        ("Skylight", "window.skylight"),
    ],
)
def test_maps_all_window_types(text: str, expected: str) -> None:
    assert map_schedule_row_to_category("window", text, location_text=None, width_mm=600) == expected


def test_unknown_window_type_maps_to_window_unknown() -> None:
    cat = map_schedule_row_to_category("window", "Periscope window", location_text=None, width_mm=300)
    assert cat == "window.unknown"


def test_match_key_validation_rejects_missing_required_dimension() -> None:
    with pytest.raises(ValueError, match="requires dimension"):
        build_match_key(
            category="door.internal.hinged",
            width_mm=None,
            height_mm=2040,
            attributes={},
        )


def test_match_key_validation_rejects_unknown_category() -> None:
    with pytest.raises(ValueError, match="unknown catalogue category"):
        build_match_key(
            category="door.totally_made_up",
            width_mm=820,
            height_mm=2040,
            attributes={},
        )


def test_match_key_unknown_category_accepts_missing_dims() -> None:
    mk = build_match_key(
        category="door.unknown", width_mm=None, height_mm=None, attributes={"raw_type_text": "?"}
    )
    assert mk.category == "door.unknown"
