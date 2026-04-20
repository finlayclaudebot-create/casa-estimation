"""Pydantic schemas for plan API responses."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PlanCreatedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_id: UUID
    filename: str
    page_count: int
    uploaded_at: datetime
