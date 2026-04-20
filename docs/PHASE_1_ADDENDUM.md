# Phase 1 Addendum: Pricing Future-Proofing

**Version:** 1.0
**Depends on:** PROJECT_FOUNDATION.md, PHASE_1_SPEC.md
**Purpose:** Small additions to Phase 1 so that when the pricing database is plugged in (Phase 4/5), matching detected elements to prices is a straightforward database join, not an expensive retrofit.

**When to apply:** BEFORE starting Phase 1 Task 2 (Database Schema). This addendum modifies the schema. If you've already run Phase 1 migrations, you'll need a new migration that adds these fields — not difficult, but cleaner to include them from the start.

---

## What this adds

Three things:

1. A `match_key` field on `takeoff_elements` — a stable, structured identifier that will later be used to look up prices.
2. An `element_catalogue` table — the controlled vocabulary of valid element categories, maintained centrally.
3. A seed script to populate the catalogue with Phase 1 categories (doors and windows).

Nothing about how Phase 1 actually DETECTS elements changes. This is purely about how detected elements are IDENTIFIED and STORED so future pricing matches work.

---

## Why a controlled vocabulary

When a pricing database says "Hinged door 820 solid core $145" and a takeoff says "I detected an internal hinged door, 820×2040, solid core", something has to tell the system that these are the same kind of thing. That "something" is a shared category vocabulary. Both sides need to agree on what `door.internal.hinged` means.

The alternative — free-text matching ("does 'hinged door' contain the word 'door'?") — fails in predictable, embarrassing ways. Controlled vocabulary is slightly more upfront work and massively more reliable downstream.

---

## The category taxonomy (Phase 1 scope)

Phase 1 only detects doors and windows. Here is the complete catalogue for Phase 1:

### Doors
- `door.external.entry` — Front/back entry door, typically 920+ wide, solid
- `door.external.sliding` — External sliding door (typically aluminium/glass, 2400+ wide)
- `door.external.hinged` — Back door, laundry door to outside
- `door.external.bifold` — External bifold door
- `door.external.garage` — Garage panel door (sectional/tilt)
- `door.internal.hinged` — Standard hinged internal door (bedroom, study, etc)
- `door.internal.cavity_slider` — Cavity-sliding door (ensuite, laundry common)
- `door.internal.sliding` — Surface-mounted sliding door
- `door.internal.bifold` — Internal bifold door
- `door.internal.french` — French/double hinged pair
- `door.internal.barn` — Barn-style slider (becoming common)
- `door.unknown` — Catch-all when type cannot be determined

### Windows
- `window.awning` — Hinged at top, opens outward from bottom
- `window.casement` — Hinged at side
- `window.sliding` — Horizontal sliding window
- `window.double_hung` — Vertical sliding sash (rarer in new AU homes, common in heritage)
- `window.fixed` — Non-opening (picture window)
- `window.louvre` — Louvre window
- `window.bifold` — Window bifold (common in servery/kitchen applications)
- `window.bay` — Bay window
- `window.highlight` — Narrow horizontal window above door/at ceiling height
- `window.skylight` — Roof-mounted (technically not a window but schedules sometimes include)
- `window.unknown` — Catch-all

Every detected element MUST resolve to exactly one of these categories. If the schedule text says "Hinged" with no other info, the element is `door.internal.hinged` or `door.external.hinged` — we take our best guess based on location context, and if we can't guess, we use `door.unknown` with low confidence.

Later phases extend this catalogue — walls, skirting, power points, etc. all get their own categories. The system of namespaced dot-separated categories scales arbitrarily: `wall.internal.plasterboard.standard`, `fixture.electrical.power_point.double`, etc.

---

## Schema changes

Add to the `takeoff_elements` table:

```sql
ALTER TABLE takeoff_elements ADD COLUMN match_key JSONB NOT NULL DEFAULT '{}';
-- match_key structure:
-- {
--   "category": "door.internal.hinged",        -- Required, from element_catalogue
--   "dimensions": {                             -- Optional, type-specific
--     "width_mm": 820,
--     "height_mm": 2040
--   },
--   "attributes": {                             -- Optional, type-specific
--     "material": "solid_core",
--     "fire_rating": null,
--     "panel_count": null
--   },
--   "quantity_unit": "each"                    -- Required: each, lm, m2, m3
-- }

CREATE INDEX idx_takeoff_elements_category
  ON takeoff_elements ((match_key->>'category'));
```

Add a new table:

```sql
CREATE TABLE element_catalogue (
    category TEXT PRIMARY KEY,                 -- e.g., 'door.internal.hinged'
    display_name TEXT NOT NULL,                -- e.g., 'Internal Hinged Door'
    parent_category TEXT REFERENCES element_catalogue(category),
    quantity_unit TEXT NOT NULL,               -- each, lm, m2, m3
    required_dimensions TEXT[] NOT NULL,       -- e.g., ['width_mm', 'height_mm']
    optional_dimensions TEXT[] NOT NULL DEFAULT '{}',
    required_attributes TEXT[] NOT NULL DEFAULT '{}',
    optional_attributes TEXT[] NOT NULL DEFAULT '{}',
    description TEXT,
    added_in_phase INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

The catalogue is schema-like: it defines what fields a given category must have. For `door.internal.hinged`, `width_mm` and `height_mm` are required; for `wall.internal` (future phase), `length_mm` and `height_mm` are required with `quantity_unit = 'lm'`. The matching engine (Phase 5) uses these rules to validate incoming elements and to build price-matching queries.

---

## How Phase 1 populates match_keys

Every element that Task 6 (Schedule Parser) inserts into `takeoff_elements` must now have a complete `match_key`. The rules:

1. **Category mapping from schedule text.** When parsing a row, map the "type" column to a catalogue category. Examples:
   - Schedule type "Hinged" on a door → `door.internal.hinged` (default) OR `door.external.hinged` (if location column contains "entry", "back", "external")
   - Schedule type "Sliding" on a door → `door.external.sliding` if width ≥ 2000, else `door.internal.sliding`
   - Schedule type "Cavity slider" or "CSD" → `door.internal.cavity_slider`
   - Schedule type "Awning" on a window → `window.awning`
   - Schedule type "Sliding" on a window → `window.sliding`
   - Schedule type "Louvre" → `window.louvre`
   - Unmapped text → `door.unknown` or `window.unknown` (record raw text in attributes)

2. **Dimensions.** Always record `width_mm` and `height_mm` as integers in millimetres. If only one dimension is given, record the known one and leave the other null. If the schedule uses metres (values < 20), multiply by 1000.

3. **Attributes.** Best-effort extraction:
   - For doors: `material` (solid_core, hollow_core, glazed, timber, aluminium), `fire_rating` (FRL values like "-/60/30" if present), `panel_count` (for sliding/bifold)
   - For windows: `glazing` (single, double, triple, obscure), `sill_height_mm`, `energy_u_value`, `energy_shgc`

4. **Quantity unit.** Always `each` for doors and windows in Phase 1.

The raw schedule row stays in `properties.raw_row` as before — match_key is the NORMALISED, STRUCTURED extract. Raw row is for audit and re-processing.

---

## Task A1: Seed the element catalogue

### Claude Code Prompt Template

```
Read PROJECT_FOUNDATION.md and docs/PHASE_1_ADDENDUM.md.

Task: Create the element_catalogue table and seed it with Phase 1 categories.

Steps:
1. Add an Alembic migration that creates the element_catalogue table per the schema in
   the addendum.
2. Add the match_key JSONB column to takeoff_elements (nullable during migration, made
   NOT NULL after seeding existing rows — which is zero rows for a fresh install).
3. Create the GIN-style index on match_key->>'category' per the addendum.
4. Create scripts/seed_catalogue.py that inserts every Phase 1 door and window category
   listed in the addendum.
5. The seed must be idempotent — running twice does not duplicate rows (use
   ON CONFLICT DO NOTHING or equivalent).
6. Add a make target: make seed-catalogue

Do not:
- Add categories that aren't in the Phase 1 list in the addendum
- Add pricing-related tables (those are Phase 4)
- Change anything about the schedule extraction logic (Task A2 does that)

Verify: after running `make migrate && make seed-catalogue`, querying element_catalogue
returns all door and window categories from the addendum and no others.
```

---

## Task A2: Populate match_keys in the schedule parser

### Claude Code Prompt Template

```
Read PROJECT_FOUNDATION.md, docs/PHASE_1_SPEC.md Task 6, and docs/PHASE_1_ADDENDUM.md.

Task: Extend the schedule extraction logic (Phase 1 Task 6) so that every inserted
takeoff_element has a complete match_key.

Steps:
1. Create a category-mapping module at app/services/catalogue/mapper.py
2. Implement:
   def map_schedule_row_to_category(
       element_type: Literal['door', 'window'],
       schedule_type_text: str,
       location_text: str | None,
       width_mm: int | None,
   ) -> str:
       """Return a valid element_catalogue category key for the given schedule row.

       Uses the mapping rules in PHASE_1_ADDENDUM.md section 'How Phase 1 populates
       match_keys'. Returns 'door.unknown' or 'window.unknown' when no confident mapping
       exists.
       """

3. Implement:
   def build_match_key(
       category: str,
       width_mm: int | None,
       height_mm: int | None,
       attributes: dict[str, Any],
       quantity_unit: str = 'each',
   ) -> MatchKey:
       """Build a MatchKey Pydantic model validated against the element_catalogue."""

4. Update the schedule parser to call these for every row and store the resulting
   match_key on the inserted takeoff_element.

5. Validation: before inserting an element, verify its match_key.category exists in the
   element_catalogue. If not, raise a clear error — this means the mapper produced a
   category that isn't seeded, which is a bug.

Tests:
- test_maps_hinged_internal_door
- test_maps_hinged_external_door_by_location
- test_maps_sliding_door_external_when_wide
- test_maps_sliding_door_internal_when_narrow
- test_maps_cavity_slider
- test_maps_unknown_door_type_to_door_unknown
- test_maps_all_window_types
- test_match_key_validation_rejects_missing_required_dimension
- test_match_key_validation_rejects_unknown_category

Do not:
- Try to map anything that isn't a door or window (those are future phases)
- Hardcode category strings in multiple places — use a constants module or enum
- Add fuzzy matching or LLM-based mapping yet (Phase 4 handles the hard mapping cases;
  Phase 1 uses deterministic rules only)
```

---

## Updated Phase 1 Completion Checklist

In addition to the Phase 1 completion criteria already in PHASE_1_SPEC.md, add:

- [ ] `element_catalogue` table exists and is seeded with all Phase 1 door/window categories
- [ ] Every row inserted into `takeoff_elements` has a valid, complete `match_key`
- [ ] `match_key.category` always references a valid catalogue entry (foreign-key-style validation, even if not enforced by DB)
- [ ] The evaluation script (Task 9) reports per-category counts, not just total door/window counts

---

## Why this matters

When Phase 4 (Pricing Ingestion) and Phase 5 (Pricing Matching) arrive, every element in the database already has a category, dimensions, and unit. A price match becomes a query like:

```sql
SELECT * FROM price_items
WHERE match_rules->>'category' = $1           -- element's category
  AND price_list_id IN (                      -- builder's lists
    SELECT id FROM price_lists WHERE organisation_id = $2
  )
  AND (
    match_rules->'width_mm_range'->>'min')::int <= $3  -- tolerance check
    AND (match_rules->'width_mm_range'->>'max')::int >= $3
  );
```

Without the match_key foundation, you'd be parsing "hinged door" out of free text at pricing time, for every element, every time. With it, pricing integration is a clean join on structured data.

---

*End of Phase 1 Addendum.*
