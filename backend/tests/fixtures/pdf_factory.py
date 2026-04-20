"""Programmatic PDF fixtures for tests.

We synthesise small PDFs with PyMuPDF rather than checking large binary blobs into
the repo. Each builder returns raw bytes so tests can write them to tmp paths.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

import fitz

A4_WIDTH = 595
A4_HEIGHT = 842


def vector_pdf(num_pages: int = 1, text_per_page: str = "Sample vector text") -> bytes:
    doc = fitz.open()
    for i in range(num_pages):
        page = doc.new_page(width=A4_WIDTH, height=A4_HEIGHT)
        page.insert_text((72, 72), f"{text_per_page} (p{i + 1})")
        # Some lines so the vector-area heuristic also fires.
        for y in range(120, 600, 30):
            page.draw_line((72, y), (A4_WIDTH - 72, y))
    data = bytes(doc.tobytes())
    doc.close()
    return data


def raster_pdf(num_pages: int = 1) -> bytes:
    """Each page is a single rendered image (no extractable text)."""

    # Render a one-page vector source, rasterise it, then embed as image.
    src = fitz.open()
    src_page = src.new_page(width=A4_WIDTH, height=A4_HEIGHT)
    src_page.draw_rect(fitz.Rect(50, 50, A4_WIDTH - 50, A4_HEIGHT - 50), fill=(0.8, 0.8, 0.8))
    pix = src_page.get_pixmap(dpi=72)
    img_bytes = pix.tobytes("png")
    src.close()

    doc = fitz.open()
    for _ in range(num_pages):
        page = doc.new_page(width=A4_WIDTH, height=A4_HEIGHT)
        page.insert_image(page.rect, stream=img_bytes)
    data = bytes(doc.tobytes())
    doc.close()
    return data


def mixed_pdf() -> bytes:
    """One vector page, one raster page."""

    doc = fitz.open()
    # Vector page
    p1 = doc.new_page(width=A4_WIDTH, height=A4_HEIGHT)
    p1.insert_text((72, 72), "Vector page with extractable text")
    for y in range(120, 600, 30):
        p1.draw_line((72, y), (A4_WIDTH - 72, y))

    # Raster page
    src = fitz.open()
    src_page = src.new_page(width=A4_WIDTH, height=A4_HEIGHT)
    src_page.draw_rect(fitz.Rect(50, 50, A4_WIDTH - 50, A4_HEIGHT - 50), fill=(0.5, 0.5, 0.5))
    pix = src_page.get_pixmap(dpi=72)
    img_bytes = pix.tobytes("png")
    src.close()

    p2 = doc.new_page(width=A4_WIDTH, height=A4_HEIGHT)
    p2.insert_image(p2.rect, stream=img_bytes)

    data = bytes(doc.tobytes())
    doc.close()
    return data


def schedule_pdf(
    schedule_title: str = "DOOR SCHEDULE",
    rows: Sequence[Sequence[str]] | None = None,
    headers: Sequence[str] | None = None,
    page_titles: Iterable[str] = ("FLOOR PLAN", "DOOR SCHEDULE"),
) -> bytes:
    """Build a simple multi-page PDF with a title block and a tabular schedule."""

    headers = headers or ("ID", "Width", "Height", "Type", "Material", "Location")
    rows = rows or (
        ("D01", "920", "2040", "Hinged", "Solid Core", "Entry"),
        ("D02", "820", "2040", "Hinged", "Solid Core", "Bedroom 1"),
        ("D03", "2400", "2100", "Sliding", "Aluminium/Glass", "Living"),
    )

    doc = fitz.open()
    titles = list(page_titles)
    for idx, title in enumerate(titles):
        page = doc.new_page(width=A4_WIDTH, height=A4_HEIGHT)
        # Title block (bottom-right) — strong signal for page classification.
        page.insert_text(
            (A4_WIDTH - 250, A4_HEIGHT - 60),
            title,
            fontsize=14,
        )
        if idx == titles.index(schedule_title) if schedule_title in titles else False:
            _draw_table(page, headers, list(rows))

    # If schedule_title wasn't in page_titles, add a dedicated schedule page.
    if schedule_title not in titles:
        page = doc.new_page(width=A4_WIDTH, height=A4_HEIGHT)
        page.insert_text(
            (A4_WIDTH - 250, A4_HEIGHT - 60), schedule_title, fontsize=14
        )
        _draw_table(page, headers, list(rows))

    data = bytes(doc.tobytes())
    doc.close()
    return data


def _draw_table(page: fitz.Page, headers: Sequence[str], rows: Sequence[Sequence[str]]) -> None:
    """Render a simple table by drawing grid lines + text cells.

    pdfplumber recognises tables based on lines, so we draw an explicit grid.
    """

    left = 50.0
    top = 100.0
    col_w = (A4_WIDTH - 2 * left) / len(headers)
    row_h = 24.0
    n_rows = len(rows) + 1  # plus header

    # Vertical lines
    for c in range(len(headers) + 1):
        x = left + c * col_w
        page.draw_line((x, top), (x, top + n_rows * row_h))
    # Horizontal lines
    for r in range(n_rows + 1):
        y = top + r * row_h
        page.draw_line((left, y), (left + len(headers) * col_w, y))

    # Header text
    for c, h in enumerate(headers):
        page.insert_text((left + c * col_w + 4, top + row_h - 8), h, fontsize=10)
    # Data rows
    for r, row in enumerate(rows, start=1):
        for c, cell in enumerate(row):
            page.insert_text(
                (left + c * col_w + 4, top + (r + 1) * row_h - 8),
                str(cell),
                fontsize=10,
            )
