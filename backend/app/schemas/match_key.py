"""Pydantic schema for the takeoff_elements.match_key JSONB column.

Mirrors the structure documented in PHASE_1_ADDENDUM.md:

    {
      "category": "door.internal.hinged",
      "dimensions": {"width_mm": 820, "height_mm": 2040},
      "attributes": {"material": "solid_core"},
      "quantity_unit": "each"
    }
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

QuantityUnit = Literal["each", "lm", "m2", "m3"]


class MatchKeyDimensions(BaseModel):
    model_config = ConfigDict(extra="allow")

    width_mm: int | None = None
    height_mm: int | None = None
    length_mm: int | None = None


class MatchKey(BaseModel):
    """Normalised, structured identifier used for downstream price matching."""

    model_config = ConfigDict(extra="forbid")

    category: str = Field(min_length=1)
    dimensions: MatchKeyDimensions = Field(default_factory=MatchKeyDimensions)
    attributes: dict[str, Any] = Field(default_factory=dict)
    quantity_unit: QuantityUnit = "each"
