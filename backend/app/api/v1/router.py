"""Aggregated v1 API router."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import health, plans, takeoffs

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(plans.router)
api_router.include_router(takeoffs.router)
