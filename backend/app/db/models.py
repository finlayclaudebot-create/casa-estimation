"""SQLAlchemy ORM models for Phase 1 tables.

Schema mirrors PROJECT_FOUNDATION.md Section 5 plus PHASE_1_ADDENDUM (match_key,
element_catalogue). Phase 1 only includes: organisations, users, projects, plans,
plan_pages, takeoffs, takeoff_elements, element_catalogue.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    ARRAY,
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )


class Organisation(Base):
    __tablename__ = "organisations"

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    users: Mapped[list[User]] = relationship(back_populates="organisation")
    projects: Mapped[list[Project]] = relationship(back_populates="organisation")


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = _uuid_pk()
    organisation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id"), nullable=True
    )
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    role: Mapped[str] = mapped_column(Text, nullable=False, server_default="member")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    organisation: Mapped[Organisation | None] = relationship(back_populates="users")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = _uuid_pk()
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    organisation: Mapped[Organisation] = relationship(back_populates="projects")
    plans: Mapped[list[Plan]] = relationship(back_populates="project")


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[uuid.UUID] = _uuid_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pdf_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    project: Mapped[Project] = relationship(back_populates="plans")
    pages: Mapped[list[PlanPage]] = relationship(
        back_populates="plan", cascade="all, delete-orphan"
    )
    takeoffs: Mapped[list[Takeoff]] = relationship(back_populates="plan")


class PlanPage(Base):
    __tablename__ = "plan_pages"
    __table_args__ = (UniqueConstraint("plan_id", "page_number", name="uq_plan_page"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("plans.id", ondelete="CASCADE"), nullable=False
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    page_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    scale: Mapped[str | None] = mapped_column(Text, nullable=True)
    width_mm: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    height_mm: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)

    plan: Mapped[Plan] = relationship(back_populates="pages")


class Takeoff(Base):
    __tablename__ = "takeoffs"

    id: Mapped[uuid.UUID] = _uuid_pk()
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("plans.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="pending")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # JSONB structure: {steps: [{name, status, started_at, finished_at, detail}]}
    processing_log: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    total_confidence: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)

    plan: Mapped[Plan] = relationship(back_populates="takeoffs")
    elements: Mapped[list[TakeoffElement]] = relationship(
        back_populates="takeoff", cascade="all, delete-orphan"
    )


class TakeoffElement(Base):
    __tablename__ = "takeoff_elements"

    id: Mapped[uuid.UUID] = _uuid_pk()
    takeoff_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("takeoffs.id", ondelete="CASCADE"),
        nullable=False,
    )
    element_type: Mapped[str] = mapped_column(Text, nullable=False)
    element_subtype: Mapped[str | None] = mapped_column(Text, nullable=True)
    schedule_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("plan_pages.id"), nullable=True
    )
    # JSONB: {x: number, y: number, width: number, height: number}
    bounding_box: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    # JSONB: type-specific properties (size, material, raw_row, etc.)
    properties: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="detected")
    verified_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    original_properties: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    # JSONB: see app/schemas/match_key.py (MatchKey schema)
    match_key: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    takeoff: Mapped[Takeoff] = relationship(back_populates="elements")


class ElementCatalogue(Base):
    """Controlled vocabulary of element categories (per PHASE_1_ADDENDUM)."""

    __tablename__ = "element_catalogue"

    category: Mapped[str] = mapped_column(Text, primary_key=True)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    parent_category: Mapped[str | None] = mapped_column(
        Text, ForeignKey("element_catalogue.category"), nullable=True
    )
    quantity_unit: Mapped[str] = mapped_column(Text, nullable=False)
    required_dimensions: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False
    )
    optional_dimensions: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'::text[]")
    )
    required_attributes: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'::text[]")
    )
    optional_attributes: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'::text[]")
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    added_in_phase: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
