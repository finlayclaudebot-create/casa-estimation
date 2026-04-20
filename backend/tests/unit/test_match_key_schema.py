"""Tests for the MatchKey Pydantic schema."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.match_key import MatchKey


def test_minimal_match_key_validates() -> None:
    mk = MatchKey(category="door.internal.hinged")
    assert mk.category == "door.internal.hinged"
    assert mk.quantity_unit == "each"


def test_dimensions_round_trip() -> None:
    mk = MatchKey.model_validate(
        {
            "category": "window.awning",
            "dimensions": {"width_mm": 600, "height_mm": 900},
            "attributes": {"glazing": "double"},
        }
    )
    assert mk.dimensions.width_mm == 600
    assert mk.attributes["glazing"] == "double"


def test_unknown_top_level_field_rejected() -> None:
    with pytest.raises(ValidationError):
        MatchKey.model_validate({"category": "door.unknown", "bogus": True})


def test_invalid_quantity_unit_rejected() -> None:
    with pytest.raises(ValidationError):
        MatchKey.model_validate({"category": "door.unknown", "quantity_unit": "kg"})
