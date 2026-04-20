"""Schema for the takeoffs.processing_log JSONB column."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

StepStatus = Literal["pending", "running", "succeeded", "failed", "skipped"]


class ProcessingStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    status: StepStatus
    started_at: datetime | None = None
    finished_at: datetime | None = None
    detail: dict[str, Any] | None = None


class ProcessingLog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    steps: list[ProcessingStep] = Field(default_factory=list)
