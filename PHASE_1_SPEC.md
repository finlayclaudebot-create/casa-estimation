# Phase 1 Build Specification
## Schedule Reader MVP

**Version:** 1.0
**Depends on:** PROJECT_FOUNDATION.md
**Target timeline:** 1-2 weeks of focused development
**Goal:** Ship the smallest possible end-to-end system that delivers real value to a builder.

---

## How to Use This Document

This is a sequential build spec. Each section below is designed to be given to Claude Code as a discrete, testable task. Do not attempt to build multiple sections in parallel or collapse them into one prompt. Work section by section, verify each, then proceed.

Each section includes:
- **Context:** What's being built and why
- **Inputs:** What data flows in
- **Outputs:** What must be produced
- **Acceptance criteria:** How we know it's done
- **Claude Code prompt template:** Copy-paste starting point

---

## Phase 1 Scope

### What we are building
A web service where a user can:
1. Upload a PDF architectural plan
2. See the system identify whether it's a vector or raster PDF
3. Have door and window schedules automatically detected and parsed
4. View the extracted doors and windows in a clean interface
5. Export the results as CSV

### What we are NOT building in Phase 1
- User accounts (single hardcoded user)
- Floor plan visual detection
- Pricing
- Area/linear measurements
- Anything involving computer vision training
- Multi-organisation support
- Mobile UI

### Success definition
When a builder uploads one of our 30 test plans with a schedule, we extract the correct count and list of doors and windows within 60 seconds, and they can download a CSV. Accuracy target: 95% on plans that have schedules; graceful "schedule not found" message on plans that don't.

---

## Task 1: Project Scaffolding

### Context
Set up the monorepo structure defined in PROJECT_FOUNDATION.md section 4. This is foundational; get it right before writing any feature code.

### Inputs
- PROJECT_FOUNDATION.md (must be present in repo root)

### Outputs
- Backend scaffold with FastAPI, dependencies installed, `/health` endpoint working
- Frontend scaffold with Next.js 14 + TypeScript + Tailwind + shadcn/ui
- Database setup with Alembic migrations initialised
- Docker Compose file for local development (Postgres + Redis)
- Makefile with common commands: `make dev`, `make test`, `make migrate`
- README with setup instructions

### Acceptance criteria
- [ ] `make dev` starts backend on :8000 and frontend on :3000
- [ ] `curl http://localhost:8000/api/v1/health` returns `{"status": "ok"}`
- [ ] Frontend renders at http://localhost:3000 with a placeholder page
- [ ] `make test` runs (empty) test suites for both backend and frontend without errors
- [ ] `mypy --strict backend/app` passes with zero errors
- [ ] `pnpm typecheck` in frontend passes with zero errors
- [ ] All secrets are in `.env.example`, never committed

### Claude Code Prompt Template

```
Read PROJECT_FOUNDATION.md in full before starting.

Task: Scaffold the Australian Building Takeoff project per Section 4 of the foundation
document. Use the exact stack specified in Section 3 — do not substitute libraries.

Scope for this session:
1. Create the full directory structure from Section 4
2. Initialise backend with FastAPI, pyproject.toml using uv, ruff, mypy strict config
3. Initialise frontend with Next.js 14 App Router + TypeScript strict + Tailwind + shadcn/ui
4. Set up docker-compose.yml with Postgres 15 and Redis
5. Create Makefile with: dev, test, migrate, lint, format targets
6. Write README.md with local setup instructions
7. Add a /api/v1/health endpoint returning {"status": "ok"}
8. Add a placeholder homepage in frontend

Do not:
- Add any features beyond what's listed
- Substitute any library from the stack in Section 3
- Create database models yet (that's Task 2)
- Add authentication (Phase 1 uses a hardcoded user)

After completing, run through the acceptance criteria list and report status on each.
```

---

## Task 2: Database Schema and Migrations

### Context
Implement the database schema from PROJECT_FOUNDATION.md Section 5, but only the tables needed for Phase 1: `organisations`, `users`, `projects`, `plans`, `plan_pages`, `takeoffs`, `takeoff_elements`.

### Inputs
- PROJECT_FOUNDATION.md Section 5

### Outputs
- SQLAlchemy models matching the schema exactly
- Alembic migration that creates the tables
- A seed script that inserts one hardcoded organisation and one hardcoded user for development

### Acceptance criteria
- [ ] `make migrate` applies the migration cleanly to an empty database
- [ ] Running the seed script twice is idempotent (no duplicate users)
- [ ] All foreign keys, constraints, and defaults match Section 5 exactly
- [ ] Migration is reversible (`alembic downgrade -1` works)
- [ ] All columns have explicit types; no untyped JSONB without a Pydantic schema documented next to it

### Claude Code Prompt Template

```
Read PROJECT_FOUNDATION.md, especially Section 5 (Database Schema) and Section 7 (Coding
Standards). Also read docs/PHASE_1_SPEC.md Task 2.

Task: Create SQLAlchemy models and an Alembic migration for the Phase 1 tables only:
organisations, users, projects, plans, plan_pages, takeoffs, takeoff_elements.

Requirements:
- Match the SQL schema in Section 5 exactly; do not add or remove columns
- Use SQLAlchemy 2.0 declarative syntax with Mapped[] type annotations
- For each JSONB column, document the expected structure in a comment and create a
  corresponding Pydantic schema in app/schemas/
- Create a seed script at scripts/seed_dev.py that inserts one org and one user; it must
  be idempotent
- The migration must include reversible downgrades

Do not:
- Add any tables not listed for Phase 1 (no price_lists etc in this task)
- Use raw SQL — use SQLAlchemy models
- Add indexes beyond what's needed for the foreign keys (performance tuning is later)

Verify: run `make migrate` on a fresh database, then run seed twice, then query to confirm
one org and one user exist.
```

---

## Task 3: PDF Upload and Storage

### Context
Accept PDF uploads via the API, store them on disk (local filesystem for v1), and create a `plans` record with metadata.

### Inputs
- An authenticated request (for Phase 1: hardcoded user from seed) with a PDF file
- The PDF can be up to 100 MB

### Outputs
- PDF stored at `storage/plans/{plan_id}.pdf`
- `plans` row created with: `id`, `project_id`, `filename`, `storage_path`, `file_size_bytes`, `page_count`, `pdf_type` (populated in Task 4)
- API response: `{ plan_id, filename, page_count, uploaded_at }`

### Acceptance criteria
- [ ] Endpoint: `POST /api/v1/plans` with `multipart/form-data`
- [ ] Rejects files that aren't PDFs (check magic bytes, not just extension)
- [ ] Rejects files over 100 MB with 413 status
- [ ] Extracts and stores `page_count` using PyMuPDF
- [ ] Creates a placeholder project if `project_id` not provided
- [ ] Unit tests cover: valid PDF, non-PDF file, oversized file, corrupt PDF
- [ ] Integration test uploads a real sample PDF and verifies the database row

### Claude Code Prompt Template

```
Read PROJECT_FOUNDATION.md and docs/PHASE_1_SPEC.md Task 3.

Task: Implement the PDF upload endpoint at POST /api/v1/plans.

Specification:
- Accept multipart/form-data with a "file" field (the PDF) and optional "project_id"
- Validate: magic bytes match PDF (0x25 0x50 0x44 0x46), size <= 100 MB
- Store file at storage/plans/{uuid}.pdf (ensure directory exists)
- Use PyMuPDF to extract page_count
- Create plans row (and a placeholder project if no project_id provided)
- Return 201 with {plan_id, filename, page_count, uploaded_at}
- On any error, do not leave orphan files on disk

Tests required (pytest):
- test_upload_valid_pdf: uses a fixture PDF in tests/fixtures/
- test_reject_non_pdf: uploads a .txt file, expects 400
- test_reject_oversized: expects 413
- test_reject_corrupt_pdf: expects 400
- test_no_orphan_files_on_failure: verifies cleanup

Do not:
- Process the PDF content beyond extracting page count (classification is Task 4)
- Implement presigned URLs (local filesystem for Phase 1)
- Add authentication beyond a hardcoded user dependency

Use the pytest fixtures pattern; share fixtures in conftest.py.
```

---

## Task 4: PDF Classification (Vector vs Raster)

### Context
Determine whether a PDF is vector-based (CAD export with extractable text and geometry) or raster (scanned or image-flattened). This drives the processing pipeline.

### Inputs
- A `plan_id` of an already-uploaded plan
- The stored PDF file on disk

### Outputs
- Updated `plans.pdf_type` set to one of: `vector`, `raster`, `mixed`
- Per-page classification stored in `plan_pages`

### Classification logic
A page is classified as:
- **vector**: has extractable text AND has vector drawing objects (lines, curves) covering substantial area
- **raster**: consists primarily of one or more images with minimal or no extractable text
- **mixed**: has vector elements but also large raster images (e.g., scanned background with CAD overlay)

A plan is classified as:
- **vector**: all or nearly all pages are vector
- **raster**: all or nearly all pages are raster
- **mixed**: a meaningful mix

### Acceptance criteria
- [ ] Service function `classify_pdf(pdf_path: Path) -> PdfClassification`
- [ ] `PdfClassification` is a Pydantic model with `overall_type` and `per_page: list[PageClassification]`
- [ ] Runs in under 10 seconds for a 100-page PDF
- [ ] Tests using fixtures for each type: a known vector plan, a known raster plan, a mixed plan
- [ ] Tested accuracy: correct classification on at least 28 of 30 sample plans

### Claude Code Prompt Template

```
Read PROJECT_FOUNDATION.md and docs/PHASE_1_SPEC.md Task 4.

Task: Implement PDF classification service at app/services/pdf/classifier.py.

Signature:
def classify_pdf(pdf_path: Path) -> PdfClassification:
    ...

Classification rules:
- Per page:
  - Extract text with PyMuPDF; if > 20 characters of extracted text AND vector drawing
    objects cover > 5% of page area → VECTOR
  - If page consists of images covering > 80% of area AND text is minimal (< 20 chars) →
    RASTER
  - Otherwise → MIXED
- Overall:
  - If > 90% of pages are vector → VECTOR
  - If > 90% of pages are raster → RASTER
  - Otherwise → MIXED

Implementation notes:
- Use fitz.Page.get_text() for text
- Use fitz.Page.get_drawings() for vector objects; compute bounding box coverage
- Use fitz.Page.get_images() for rasters

Test fixtures to create:
- tests/fixtures/sample_vector.pdf (CAD-exported plan)
- tests/fixtures/sample_raster.pdf (scanned plan)
- tests/fixtures/sample_mixed.pdf

Tests:
- test_classify_vector_plan: expects VECTOR
- test_classify_raster_plan: expects RASTER
- test_classify_mixed_plan: expects MIXED
- test_classify_empty_pdf: expects appropriate handling (not crash)
- test_classify_performance: 100-page PDF classifies in < 10 seconds

Wire into the upload endpoint so pdf_type is populated on upload.

Do not:
- Attempt to extract schedules or do any content parsing in this task
- Use any OCR (that's for raster pages in later tasks)
```

---

## Task 5: Page Type Classification

### Context
A plan PDF contains different page types: floor plans, elevations, sections, schedules, site plans, details. For Phase 1, we only need to identify SCHEDULE pages (where door and window schedules typically live).

### Inputs
- A `plan_id`
- Its pages (text already extractable because we're in vector pipeline for Phase 1)

### Outputs
- `plan_pages.page_type` populated for each page; focus on correctly identifying `schedule` and `floor_plan` pages. Others can default to `unknown`.

### Classification approach
- Extract title block text from each page (typically lower-right corner)
- Match against patterns:
  - Schedule: text contains "SCHEDULE", "DOOR SCHEDULE", "WINDOW SCHEDULE", "JOINERY SCHEDULE"
  - Floor plan: text contains "FLOOR PLAN", "GROUND FLOOR", "FIRST FLOOR", "LEVEL 1", "LEVEL 2"
  - Elevation: text contains "ELEVATION", "NORTH", "SOUTH", "EAST", "WEST"
  - Section: text contains "SECTION"
  - Site: text contains "SITE PLAN", "SITE"

- Pages may have multiple tags (rare); pick the most prominent.

### Acceptance criteria
- [ ] Service function `classify_page_types(pdf_path: Path) -> list[PageType]`
- [ ] Handles title blocks in different positions (search full page text, but weight text near edges)
- [ ] Tests on 10 sample plans: correct classification of floor plan and schedule pages on at least 9 of 10
- [ ] Graceful handling of plans where classification is ambiguous (returns `unknown`)

### Claude Code Prompt Template

```
Read PROJECT_FOUNDATION.md and docs/PHASE_1_SPEC.md Task 5.

Task: Implement page type classification at app/services/pdf/page_classifier.py.

Goal: Correctly identify which pages of a plan PDF are SCHEDULE pages and which are
FLOOR_PLAN pages. Other types (elevation, section, site, detail, unknown) are best-effort.

Signature:
def classify_page_types(pdf_path: Path) -> list[PageClassification]:
    ...

PageClassification fields:
- page_number: int (1-indexed)
- page_type: Literal['floor_plan', 'schedule', 'elevation', 'section', 'site_plan',
  'detail', 'unknown']
- detected_title: str | None (the title block text if found)
- confidence: float (0.0-1.0)

Logic:
- Extract all text from the page with PyMuPDF
- Search for type-indicating keywords (see Task 5 spec for the list)
- Weight matches near page edges higher (title blocks are usually bottom-right)
- If multiple matches, pick highest-weighted
- If no match, return 'unknown' with low confidence

Do not:
- Use OCR (assume vector PDF)
- Attempt to parse the schedule content itself (Task 6)

Tests:
- Create 5 fixture PDFs with known page types
- test_identifies_schedule_pages
- test_identifies_floor_plan_pages
- test_handles_ambiguous_pages
- test_returns_unknown_for_unlabelled_pages

Wire into the upload flow so plan_pages rows have page_type populated.
```

---

## Task 6: Door and Window Schedule Extraction

### Context
This is the core value-delivery task of Phase 1. Parse the door and window schedules from pages classified as `schedule`.

### Inputs
- A plan with at least one page classified as `schedule`
- The PDF file

### Outputs
- A list of door entries: `[{schedule_id, type, width_mm, height_mm, material, location_note, raw_row}]`
- A list of window entries with the same structure
- Entries written to `takeoff_elements` with `source='schedule'` and `confidence=0.95`

### Australian schedule conventions to handle

Door schedules typically have columns like:
- **ID/Mark** (D01, D02, D-01)
- **Width x Height** (sometimes separate, sometimes combined: "820 x 2040")
- **Type** (Hinged, Sliding, Cavity Slider, Bifold)
- **Material/Finish** (Solid Core, Glazed, Timber)
- **Location** (Bedroom 1, Entry, Ensuite)
- **Fire rating** (sometimes)
- **Notes**

Window schedules typically have:
- **ID/Mark** (W01, W-01)
- **Width x Height**
- **Type** (Awning, Sliding, Casement, Fixed, Louvre)
- **Glazing** (Single, Double, Obscure)
- **Sill height** (sometimes)
- **Energy rating** (U-value, SHGC - often present post-NCC 2022)

Variations to handle:
- Tables may be in landscape or portrait orientation
- Tables may span multiple pages
- Rows may be missing data (normalise to null, don't error)
- Sizes may be in mm (standard) or occasionally meters
- Combined door + window schedule on one page

### Acceptance criteria
- [ ] Service function `extract_schedules(pdf_path: Path, schedule_pages: list[int]) -> ScheduleExtractionResult`
- [ ] Handles at least 3 common table layouts (test fixtures provided)
- [ ] Extracts all standard columns; unknown columns captured in `raw_row` JSONB
- [ ] Target: correct extraction on at least 25 of 30 sample plans (83%)
- [ ] When extraction fails or is low-confidence, returns `status='needs_review'` with the problem described

### Claude Code Prompt Template

```
Read PROJECT_FOUNDATION.md and docs/PHASE_1_SPEC.md Task 6 carefully. This is the core
feature of Phase 1.

Task: Extract door and window schedules from pages classified as 'schedule'.

Implementation at app/services/pdf/schedule_parser.py.

Approach:
1. Use pdfplumber to extract tables from the schedule page(s)
2. Identify header row by matching against known column patterns (see Task 6 spec)
3. For each data row:
   - Extract schedule_id (must match pattern like 'D01', 'W-01', 'WIN-001')
   - Parse dimensions (handle '820 x 2040', '820x2040', separate columns)
   - Normalise type (map free text to our enum: hinged, sliding, cavity_slider, bifold,
     awning, casement, fixed, louvre)
   - Preserve full raw row in a JSONB field for audit
4. Return ScheduleExtractionResult with separate doors and windows lists plus metadata

Key Australian handling:
- Dimensions are in mm by default; if a value < 20, assume meters and convert
- Sliding doors with panel counts (e.g., "2400 x 2100 - 3 panel") should record panel count
- Sizes like "820/2040" use / as separator sometimes
- Handle cells that have been merged in the source table

Pydantic models needed:
- DoorScheduleEntry, WindowScheduleEntry (with all fields from spec)
- ScheduleExtractionResult {doors, windows, warnings, extraction_confidence}

Tests:
- Use 5 fixture PDFs with known schedules of varying layouts
- For each, assert exact extraction of all entries
- test_handles_landscape_schedule
- test_handles_multi_page_schedule
- test_handles_missing_columns
- test_handles_unknown_door_type (falls back to 'unknown', doesn't crash)

Important: Write the detected entries to takeoff_elements with source='schedule' and
confidence=0.95. Each row is one element.

Do not:
- Try to reconcile against the floor plan (that's Phase 2)
- Apply any pricing (that's Phase 4)
- OCR-scan anything (Phase 1 is vector only)
```

---

## Task 7: Takeoff Orchestration and Async Processing

### Context
Wire tasks 4, 5, and 6 together into a single pipeline triggered by an API call. Because processing takes 30+ seconds, this must run as a background job.

### Inputs
- `POST /api/v1/plans/{plan_id}/takeoff` trigger

### Outputs
- A `takeoffs` row created immediately with `status='pending'`
- Background job runs: classify → identify pages → extract schedules → update takeoff status
- Final status: `completed`, `needs_review`, or `failed`

### Acceptance criteria
- [ ] Endpoint returns immediately (< 500ms) with takeoff_id
- [ ] Celery worker picks up the job and runs the full pipeline
- [ ] Status transitions are recorded in `processing_log` JSONB field
- [ ] Failures are caught and logged; status becomes `failed` with `error_message` set
- [ ] Frontend can poll `GET /api/v1/takeoffs/{id}` to check status

### Claude Code Prompt Template

```
Read PROJECT_FOUNDATION.md and docs/PHASE_1_SPEC.md Task 7.

Task: Wire the Phase 1 pipeline into an async job.

Components:
1. POST /api/v1/plans/{plan_id}/takeoff endpoint
   - Creates takeoffs row with status='pending'
   - Enqueues Celery task
   - Returns 202 Accepted with {takeoff_id, status, poll_url}

2. Celery task: process_takeoff(takeoff_id)
   Steps (each logged to processing_log JSONB):
   a. Update status = 'processing'
   b. Classify PDF (vector/raster/mixed) — populate plans.pdf_type
   c. Classify page types — populate plan_pages
   d. If plan is raster: set status='failed' with message
      "Raster PDFs not yet supported — Phase 1 requires vector plans"
   e. If no schedule pages found: status='failed' with clear message
   f. Extract schedules — insert takeoff_elements
   g. Compute total_confidence from element confidences
   h. Update status = 'completed' (or 'needs_review' if confidence < 0.8)

3. GET /api/v1/takeoffs/{id} endpoint returns current status, counts, and elements

Error handling:
- Any exception in a step captures traceback to error_message
- Never leave a takeoff in 'processing' indefinitely — use a 10-minute timeout
- Celery retries: max 2 retries, only on transient errors (e.g., temp file issues)

Tests:
- test_happy_path: upload sample plan, trigger takeoff, poll until complete, verify elements
- test_raster_plan_fails_gracefully
- test_no_schedule_fails_gracefully
- test_corrupt_pdf_marked_failed_not_stuck

Do not:
- Skip the async/worker setup and make it synchronous (this is essential infrastructure)
- Build retry logic beyond Celery's built-in retries
```

---

## Task 8: Frontend — Upload and View

### Context
Build the minimum UI: upload a PDF, see processing status, view extracted doors and windows, export as CSV.

### Pages required
1. `/` — Upload page with drag-and-drop
2. `/plans/{id}` — Plan detail page showing processing status and, when ready, the extracted elements grouped as Doors and Windows with counts

### Acceptance criteria
- [ ] Drag-and-drop PDF upload with progress indicator
- [ ] Client-side validation: only PDFs, max 100 MB
- [ ] After upload, automatically trigger takeoff and navigate to detail page
- [ ] Detail page polls every 2 seconds until status is terminal
- [ ] Clear status messages: "Uploading", "Classifying PDF", "Extracting schedule", "Done"
- [ ] Doors table and Windows table with all extracted fields
- [ ] "Export CSV" button that downloads a CSV of elements
- [ ] Error states clearly shown with actionable messages
- [ ] Playwright E2E test: upload fixture PDF, wait for completion, verify counts

### Claude Code Prompt Template

```
Read PROJECT_FOUNDATION.md and docs/PHASE_1_SPEC.md Task 8.

Task: Build the Phase 1 frontend — upload and view flow only.

Stack (from foundation doc):
- Next.js 14 App Router, TypeScript strict
- shadcn/ui components (Button, Table, Card, Progress, Alert)
- TanStack Query for server state
- Tailwind for layout

Pages:
1. app/page.tsx — Upload interface
   - Large drag-and-drop zone with file picker fallback
   - Validates file type and size client-side
   - Shows upload progress
   - On success, navigates to /plans/{id}

2. app/plans/[id]/page.tsx — Plan detail
   - Polls GET /api/v1/takeoffs/{latest_id_for_plan} every 2s while pending/processing
   - Shows stepper-style progress: Classifying → Identifying Pages → Extracting Schedule → Done
   - When complete, shows two tables: Doors and Windows
   - Export CSV button (generates client-side from the data)

Components to build in components/:
- PlanUploader (drag-and-drop with validation)
- ProcessingStatus (stepper with current step highlighted)
- ElementsTable (reusable for doors and windows)
- ExportButton (triggers CSV download)

Backend API client in lib/api.ts:
- Strongly typed with Zod schemas matching backend Pydantic models
- Handles errors consistently

Tests (Playwright):
- e2e/upload-and-view.spec.ts: upload fixture PDF, wait for "Done" status, assert table
  shows expected count
- e2e/invalid-file.spec.ts: try to upload a .txt, assert client-side rejection

Do not:
- Add editing capabilities (that's Phase 2)
- Add authentication UI
- Add a plans list page or dashboard (one plan at a time is fine for Phase 1)
- Try to preview the PDF itself (just show extracted data)
```

---

## Task 9: Testing Against Sample Plans

### Context
The acceptance target for Phase 1 is 95% accuracy on plans that have schedules. We need to verify this against a real sample set before declaring Phase 1 done.

### Inputs
- Sample plan set (30 Australian plans, mix of volume builder, architect, draftsperson)
- Truth files for each

### Outputs
- An automated evaluation script that runs the full pipeline against each sample plan and reports:
  - Count accuracy (detected vs truth count)
  - ID coverage (how many truth IDs were found)
  - Type accuracy (did we classify the door/window type correctly)
  - Overall pass/fail per plan

### Acceptance criteria
- [ ] `make evaluate` runs the evaluation end-to-end
- [ ] Produces a report at `eval_results/{timestamp}.json` and a human-readable summary
- [ ] At least 25 of 30 sample plans (83%) pass with > 95% element accuracy
- [ ] Failing plans have actionable notes explaining what broke

### Claude Code Prompt Template

```
Read PROJECT_FOUNDATION.md and docs/PHASE_1_SPEC.md Task 9.

Task: Build an evaluation harness for Phase 1 accuracy.

Create scripts/evaluate.py that:
1. Reads every PDF in data/sample_plans/*.pdf
2. For each, loads the paired data/sample_plans/*.truth.json
3. Runs the full takeoff pipeline (same code path as production)
4. Compares extracted vs truth:
   - Total door count match
   - Total window count match
   - Schedule IDs recovered (set intersection)
   - Type classification accuracy (per element)
5. Writes results to eval_results/{ISO_timestamp}.json
6. Prints a summary table to stdout

Output format (JSON):
{
  "run_at": "...",
  "total_plans": 30,
  "passed": 26,
  "failed": 4,
  "overall_element_accuracy": 0.94,
  "per_plan": [
    {
      "plan": "smith_residence.pdf",
      "doors": {"truth": 14, "detected": 14, "correct_ids": 14, "missing_ids": [],
                "extra_ids": []},
      "windows": {...},
      "passed": true,
      "notes": ""
    },
    ...
  ]
}

Add a "make evaluate" target to the Makefile.

Do not:
- Fix accuracy issues during this task — just measure. Fixing bugs surfaced by evaluation
  is a separate follow-up.
- Skip plans that error — record the error and count as failed.
```

---

## Phase 1 Completion Checklist

Phase 1 is DONE when all of the following are true:

- [ ] All 9 tasks above have passing tests
- [ ] `make evaluate` shows ≥ 83% of sample plans pass with ≥ 95% element accuracy
- [ ] Three real Australian builders have successfully uploaded one of their plans and gotten a usable door/window list
- [ ] Feedback from those builders is captured in `docs/PHASE_1_FEEDBACK.md`
- [ ] Known limitations documented in README
- [ ] A loom/screen recording of a full upload-to-CSV flow exists for demo purposes

Do NOT start Phase 2 until this checklist is green.

---

## Anti-Patterns to Refuse

When Claude Code suggests any of these, push back:

1. **"Let me add X library for Y"** — unless X is in the foundation doc, stop. Evaluate whether the problem is real or if existing libraries handle it.
2. **"Let me refactor this to be cleaner"** — reject unless there is a specific, named problem and scope is bounded.
3. **"I'll make this synchronous for simplicity"** — no. Takeoff processing must be async per Task 7.
4. **"Let's skip the tests for now"** — no. Phase 1 has no skipped tests.
5. **"I can build the whole Phase 1 in one session"** — no. Tasks are separate for a reason; each gets its own session.
6. **"This PDF format is weird, let me handle it specially"** — capture the case as a fixture, not a hardcoded special case.
7. **"Let me add OCR for safety"** — Phase 1 is vector only. Raster support is Phase 5.

---

*End of Phase 1 Specification. When Phase 1 is complete, draft the Phase 2 spec using this document as a template.*
