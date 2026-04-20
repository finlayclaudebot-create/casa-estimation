"""Idempotent seed for the element_catalogue table (Phase 1 doors + windows).

Runs the full Phase 1 category list defined in
app/services/catalogue/categories.py via INSERT ... ON CONFLICT DO NOTHING.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.models import ElementCatalogue
from app.db.session import get_sessionmaker
from app.services.catalogue.categories import PHASE_1_CATEGORIES


def seed() -> None:
    factory = get_sessionmaker()
    rows = [
        {
            "category": c.category,
            "display_name": c.display_name,
            "parent_category": c.parent_category,
            "quantity_unit": c.quantity_unit,
            "required_dimensions": list(c.required_dimensions),
            "optional_dimensions": list(c.optional_dimensions),
            "required_attributes": list(c.required_attributes),
            "optional_attributes": list(c.optional_attributes),
            "description": c.description,
            "added_in_phase": c.added_in_phase,
        }
        for c in PHASE_1_CATEGORIES
    ]

    with factory() as session, session.begin():
        before = session.query(ElementCatalogue).count()
        stmt = pg_insert(ElementCatalogue).values(rows)
        stmt = stmt.on_conflict_do_nothing(index_elements=["category"])
        session.execute(stmt)
        session.flush()
        after = session.query(ElementCatalogue).count()
        print(
            f"[seed-catalogue] {after - before} new categories inserted "
            f"({after} total in element_catalogue)"
        )


if __name__ == "__main__":
    seed()
