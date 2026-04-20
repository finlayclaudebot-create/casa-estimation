"""PDF classification: vector vs raster vs mixed.

Per PHASE_1_SPEC Task 4. Classification is per-page first, then aggregated.
Phase 1 only acts on vector PDFs; raster PDFs are rejected by the orchestrator.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import fitz
from pydantic import BaseModel, ConfigDict, Field

PageType = Literal["vector", "raster", "mixed"]
PdfType = Literal["vector", "raster", "mixed"]

MIN_TEXT_CHARS = 20
MIN_VECTOR_AREA_RATIO = 0.05
MIN_IMAGE_AREA_RATIO = 0.80
OVERALL_MAJORITY = 0.90


class PageClassification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page_number: int = Field(ge=1)
    page_type: PageType
    text_chars: int = Field(ge=0)
    vector_area_ratio: float = Field(ge=0, le=1)
    image_area_ratio: float = Field(ge=0, le=1)


class PdfClassification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    overall_type: PdfType
    per_page: list[PageClassification]


def _bbox_area(rect: fitz.Rect) -> float:
    return float(max(0.0, rect.width) * max(0.0, rect.height))


def _vector_coverage_ratio(page: fitz.Page) -> float:
    """Sum of bounding boxes of vector drawings, clamped to page area, as ratio."""

    page_area = _bbox_area(page.rect)
    if page_area <= 0:
        return 0.0
    total = 0.0
    page_rect = page.rect
    for drawing in page.get_drawings():
        rect = drawing.get("rect")
        if rect is None:
            continue
        clipped = rect & page_rect
        total += _bbox_area(clipped)
    return min(1.0, total / page_area)


def _image_coverage_ratio(page: fitz.Page) -> float:
    page_area = _bbox_area(page.rect)
    if page_area <= 0:
        return 0.0
    total = 0.0
    for img in page.get_images(full=True):
        xref = img[0]
        for rect in page.get_image_rects(xref):
            total += _bbox_area(rect & page.rect)
    return min(1.0, total / page_area)


def _classify_page(page: fitz.Page) -> PageClassification:
    text = page.get_text("text") or ""
    text_chars = len(text.strip())
    vec_ratio = _vector_coverage_ratio(page)
    img_ratio = _image_coverage_ratio(page)

    if text_chars > MIN_TEXT_CHARS and vec_ratio > MIN_VECTOR_AREA_RATIO:
        ptype: PageType = "vector"
    elif img_ratio > MIN_IMAGE_AREA_RATIO and text_chars < MIN_TEXT_CHARS:
        ptype = "raster"
    elif img_ratio > MIN_IMAGE_AREA_RATIO and vec_ratio > MIN_VECTOR_AREA_RATIO:
        ptype = "mixed"
    elif text_chars > MIN_TEXT_CHARS:
        # Text but little vector geometry — still vector-extractable.
        ptype = "vector"
    elif img_ratio > 0:
        ptype = "raster"
    else:
        ptype = "mixed"

    return PageClassification(
        page_number=page.number + 1,
        page_type=ptype,
        text_chars=text_chars,
        vector_area_ratio=vec_ratio,
        image_area_ratio=img_ratio,
    )


def _aggregate(per_page: list[PageClassification]) -> PdfType:
    if not per_page:
        return "mixed"
    n = len(per_page)
    vector = sum(1 for p in per_page if p.page_type == "vector") / n
    raster = sum(1 for p in per_page if p.page_type == "raster") / n
    if vector >= OVERALL_MAJORITY:
        return "vector"
    if raster >= OVERALL_MAJORITY:
        return "raster"
    return "mixed"


def classify_pdf(pdf_path: Path) -> PdfClassification:
    """Classify each page of *pdf_path* and aggregate to an overall verdict."""

    with fitz.open(pdf_path) as doc:
        per_page = [_classify_page(page) for page in doc]
    return PdfClassification(overall_type=_aggregate(per_page), per_page=per_page)
