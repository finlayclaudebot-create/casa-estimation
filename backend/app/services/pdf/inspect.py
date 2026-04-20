"""Lightweight PDF inspection used at upload time.

Heavier classification (vector/raster) happens later in the pipeline; here we
just validate that the bytes are a parseable PDF and extract the page count.
"""

from __future__ import annotations

from pathlib import Path

import fitz

PDF_MAGIC = b"%PDF-"


class InvalidPdfError(ValueError):
    """Raised when bytes do not represent a valid, openable PDF."""


def looks_like_pdf(content: bytes) -> bool:
    """Return True if *content* starts with the PDF magic header."""

    return content[:5] == PDF_MAGIC


def get_page_count(path: Path) -> int:
    """Open *path* with PyMuPDF and return the number of pages."""

    try:
        with fitz.open(path) as doc:
            return int(doc.page_count)
    except Exception as exc:  # PyMuPDF raises various exceptions for bad files
        raise InvalidPdfError(f"unable to open PDF: {exc}") from exc
