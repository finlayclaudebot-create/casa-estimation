"""Tests for PDF vector/raster classification."""

from __future__ import annotations

from pathlib import Path

from app.services.pdf.classifier import classify_pdf
from tests.fixtures.pdf_factory import mixed_pdf, raster_pdf, vector_pdf


def _write(tmp_path: Path, name: str, data: bytes) -> Path:
    p = tmp_path / name
    p.write_bytes(data)
    return p


def test_classify_vector_plan(tmp_path: Path) -> None:
    path = _write(tmp_path, "vec.pdf", vector_pdf(num_pages=3))
    result = classify_pdf(path)
    assert result.overall_type == "vector"
    assert all(p.page_type == "vector" for p in result.per_page)


def test_classify_raster_plan(tmp_path: Path) -> None:
    path = _write(tmp_path, "ras.pdf", raster_pdf(num_pages=2))
    result = classify_pdf(path)
    assert result.overall_type == "raster"
    assert all(p.page_type == "raster" for p in result.per_page)


def test_classify_mixed_plan(tmp_path: Path) -> None:
    path = _write(tmp_path, "mix.pdf", mixed_pdf())
    result = classify_pdf(path)
    assert result.overall_type == "mixed"
    types = {p.page_type for p in result.per_page}
    assert "vector" in types
    assert "raster" in types


def test_classify_empty_pdf(tmp_path: Path) -> None:
    import fitz

    doc = fitz.open()
    doc.new_page()
    p = tmp_path / "empty.pdf"
    p.write_bytes(bytes(doc.tobytes()))
    doc.close()
    result = classify_pdf(p)
    assert result.per_page[0].text_chars == 0
    # An empty page has no images and no vectors → mixed (catch-all)
    assert result.overall_type in {"mixed", "raster"}


def test_classify_performance_under_10s_for_50_pages(tmp_path: Path) -> None:
    import time

    path = _write(tmp_path, "big.pdf", vector_pdf(num_pages=50))
    start = time.perf_counter()
    result = classify_pdf(path)
    elapsed = time.perf_counter() - start
    assert elapsed < 10.0, f"classification too slow: {elapsed:.2f}s"
    assert len(result.per_page) == 50
