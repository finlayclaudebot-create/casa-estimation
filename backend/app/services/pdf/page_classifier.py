"""Page-type classification by title-block keywords.

Per PHASE_1_SPEC Task 5. We're only required to be reliable on SCHEDULE and
FLOOR_PLAN; other types are best-effort. The approach:

  1. Extract every text span on the page with PyMuPDF (with positions).
  2. Score each candidate page-type by summing keyword hits, weighted by how
     close the match is to the page edges (title blocks live near edges).
  3. Pick the highest-scoring type. If no keyword hits, return 'unknown'.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import fitz
from pydantic import BaseModel, ConfigDict, Field

PageType = Literal[
    "floor_plan",
    "schedule",
    "elevation",
    "section",
    "site_plan",
    "detail",
    "unknown",
]


# Keyword → page-type mapping. First-match within a list still adds to the
# score; matches near edges get a multiplier (see _edge_weight).
_KEYWORDS: dict[PageType, tuple[str, ...]] = {
    "schedule": (
        "joinery schedule",
        "door schedule",
        "window schedule",
        "schedule",
    ),
    "floor_plan": (
        "floor plan",
        "ground floor",
        "first floor",
        "second floor",
        "level 1",
        "level 2",
        "lower floor",
        "upper floor",
    ),
    "elevation": (
        "elevation",
        "north elevation",
        "south elevation",
        "east elevation",
        "west elevation",
    ),
    "section": ("section a-a", "section b-b", "section"),
    "site_plan": ("site plan", "site"),
    "detail": ("detail", "details"),
}


class PageClassification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page_number: int = Field(ge=1)
    page_type: PageType
    detected_title: str | None = None
    confidence: float = Field(ge=0, le=1)


def _edge_weight(span_rect: fitz.Rect, page_rect: fitz.Rect) -> float:
    """Higher weight the closer a span sits to a page edge.

    Title blocks usually live in a corner — typically bottom-right on AU plans.
    Returns a value in [1.0, 2.5].
    """

    page_w = float(page_rect.width or 1.0)
    page_h = float(page_rect.height or 1.0)
    cx = (float(span_rect.x0) + float(span_rect.x1)) / 2
    cy = (float(span_rect.y0) + float(span_rect.y1)) / 2
    # Normalised distance from nearest edge: 0 at edge, 0.5 at centre.
    nx = min(cx / page_w, 1 - cx / page_w)
    ny = min(cy / page_h, 1 - cy / page_h)
    edge_proximity = 1.0 - 2.0 * min(nx, ny)  # 1 at edge, 0 at centre
    return float(1.0 + 1.5 * max(0.0, edge_proximity))


def _classify_one_page(page: fitz.Page) -> PageClassification:
    page_rect = page.rect
    spans: list[tuple[str, fitz.Rect]] = []
    text_dict = page.get_text("dict") or {}
    for block in text_dict.get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = (span.get("text") or "").strip()
                if not text:
                    continue
                bbox = span.get("bbox")
                if not bbox or len(bbox) != 4:
                    continue
                spans.append((text.lower(), fitz.Rect(*bbox)))

    scores: dict[PageType, float] = {pt: 0.0 for pt in _KEYWORDS}
    best_title: dict[PageType, str | None] = {pt: None for pt in _KEYWORDS}

    for text, rect in spans:
        for ptype, kws in _KEYWORDS.items():
            for kw in kws:
                if kw in text:
                    weight = _edge_weight(rect, page_rect) * (1.0 + 0.05 * len(kw))
                    scores[ptype] += weight
                    if best_title[ptype] is None:
                        best_title[ptype] = text
                    break  # don't double-count multiple keywords from same list

    if not any(v > 0 for v in scores.values()):
        return PageClassification(
            page_number=page.number + 1,
            page_type="unknown",
            detected_title=None,
            confidence=0.0,
        )

    chosen: PageType = max(scores, key=lambda k: scores[k])
    top_score = scores[chosen]
    runner_up = max((v for k, v in scores.items() if k != chosen), default=0.0)
    spread = top_score - runner_up
    confidence = min(1.0, max(0.4, 0.5 + spread / max(1.0, top_score) / 2))

    return PageClassification(
        page_number=page.number + 1,
        page_type=chosen,
        detected_title=best_title[chosen],
        confidence=confidence,
    )


def classify_page_types(pdf_path: Path) -> list[PageClassification]:
    """Classify every page of *pdf_path*."""

    with fitz.open(pdf_path) as doc:
        return [_classify_one_page(page) for page in doc]
