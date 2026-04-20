# Project Foundation Document
## Australian Building Takeoff Automation System

**Version:** 1.0
**Last Updated:** 20 April 2026
**Purpose:** Master reference document for all Claude Code development sessions. This document defines the project architecture, tech stack, conventions, and standards. It should be referenced or attached at the start of every coding session so the AI has consistent context.

---

## How to Use This Document

1. Keep this file at the root of your project as `PROJECT_FOUNDATION.md`
2. At the start of every Claude Code session, run: `claude --add-file PROJECT_FOUNDATION.md` or reference it in your first prompt with "Read PROJECT_FOUNDATION.md before proceeding"
3. When any decision changes (tech stack, schema, architecture), update this document FIRST, then implement
4. Never let Claude Code make architectural decisions without updating this document

---

## 1. Project Vision

### What We Are Building
An automated building takeoff system for Australian residential and light commercial construction. Users upload architectural PDF plans; the system identifies, counts, measures, and prices every relevant building element (doors, windows, walls, floors, fittings, etc.) and produces a priced bill of materials.

### Target User
Australian builders and estimators performing construction takeoffs. They currently do this manually with a ruler, highlighter, and spreadsheet — a process that takes 4-40 hours per plan depending on complexity.

### Non-Goals (Explicitly Out of Scope for v1)
- Commercial high-rise plans (structural complexity beyond v1 scope)
- 3D BIM model processing (we work with 2D PDFs only)
- Plans from regions other than Australia/NZ
- Real-time collaborative editing
- Mobile-first UI (desktop-first; mobile is future)

### Success Metrics
- **Accuracy:** 95%+ on vector PDFs with schedules; 85%+ on raster PDFs
- **Speed:** Full takeoff in under 5 minutes per plan
- **Verification overhead:** User can verify and correct results in under 10 minutes per plan
- **Coverage:** Handles 80%+ of Australian residential plans (volume builder + standard architect plans)

---

## 2. Core Philosophy and Guardrails

### Honesty Principle
The system NEVER produces confident-looking outputs it cannot back up. Every detected element has a confidence score. Low-confidence detections are flagged for human review, not silently accepted.

### Verification-First Design
The product is not "AI that does takeoffs perfectly." It is "AI that does 95% of the takeoff automatically and makes the remaining 5% take seconds to verify." The verification UI is a first-class feature, not an afterthought.

### Schedule-as-Ground-Truth
Australian permitted plans almost always contain door and window schedules. These are authoritative. The system prioritises schedule extraction and uses visual detection as a cross-check, not the primary source.

### Progressive Enhancement
The system works on any PDF, but works BETTER on vector PDFs with schedules. It never refuses to process a plan; it adjusts confidence scores based on what it can extract.

---

## 3. Technology Stack

All technology choices below are FINAL unless updated in this document. Do not deviate in code without updating this document first.

### Backend
- **Language:** Python 3.11+
- **Framework:** FastAPI (async support, OpenAPI docs built-in, type-safe)
- **Task Queue:** Celery with Redis broker (PDF processing is too slow for synchronous requests)
- **Database:** PostgreSQL 15+ (relational data, strong typing, JSONB for flexible fields)
- **File Storage:** Local filesystem for v1; S3-compatible (Cloudflare R2 or AWS S3) for production

### PDF and Image Processing
- **PDF Parsing:** PyMuPDF (fitz) — most capable library for mixed vector/raster content
- **Table Extraction:** pdfplumber as primary; camelot as fallback for complex tables
- **OCR:** PaddleOCR (significantly better than Tesseract for table text and architectural drawings)
- **Image Processing:** OpenCV (cv2) and Pillow
- **Computer Vision (Phase 2+):** Ultralytics YOLO v8 for symbol detection

### Frontend
- **Framework:** Next.js 14+ with App Router (React with server components, excellent DX, easy deployment)
- **Language:** TypeScript (strict mode; no `any` types without justification in a comment)
- **Styling:** Tailwind CSS + shadcn/ui components (fast to build, professional default look)
- **PDF Rendering:** PDF.js via react-pdf-viewer
- **State Management:** Zustand for client state; TanStack Query for server state
- **Forms:** React Hook Form + Zod validation

### Infrastructure (v1)
- **Hosting:** Railway or Render for backend; Vercel for frontend (easy deploy from git)
- **Database hosting:** Railway-managed Postgres or Supabase
- **Auth:** Supabase Auth or Clerk (do not build custom auth)
- **File uploads:** Direct-to-storage presigned URLs (large PDFs should never touch the API server)

### Development Tools
- **Package management:** `uv` for Python, `pnpm` for Node
- **Linting:** `ruff` for Python, `eslint` + `prettier` for TypeScript
- **Formatting:** `ruff format` for Python, `prettier` for TS
- **Testing:** `pytest` for Python, `vitest` + `playwright` for TS
- **Type checking:** `mypy --strict` for Python, `tsc --noEmit` for TS

### Justification for Key Choices

**Why Python backend + Next.js frontend instead of full Next.js?**
The PDF and ML ecosystem lives in Python. PyMuPDF, PaddleOCR, and YOLO are Python-first. Trying to do this in Node would mean worse libraries or shelling out to Python anyway.

**Why Celery instead of simpler job queue?**
PDF processing can take 30s-5min. The API must return immediately and the frontend must poll for results. Celery handles retries, failures, and scaling properly.

**Why PostgreSQL instead of MongoDB?**
Takeoff data is relational (plans have pages, pages have elements, elements link to pricing). JSONB columns handle flexible per-element properties without losing relational integrity.

**Why shadcn/ui?**
Copy-paste components owned by us, not an external dependency. Professional look out of the box. Heavy customisation without fighting the library.

---

## 4. Project Structure

```
takeoff-system/
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI routes
│   │   │   ├── v1/
│   │   │   │   ├── plans.py
│   │   │   │   ├── takeoffs.py
│   │   │   │   ├── pricing.py
│   │   │   │   └── auth.py
│   │   ├── core/             # Config, security, base classes
│   │   │   ├── config.py
│   │   │   └── security.py
│   │   ├── db/               # Database models and sessions
│   │   │   ├── models.py
│   │   │   └── session.py
│   │   ├── services/         # Business logic
│   │   │   ├── pdf/
│   │   │   │   ├── classifier.py      # Vector vs raster detection
│   │   │   │   ├── extractor.py       # Text and element extraction
│   │   │   │   ├── schedule_parser.py # Door/window schedule parsing
│   │   │   │   └── page_classifier.py # Floor plan vs elevation etc
│   │   │   ├── detection/
│   │   │   │   ├── symbols.py         # CV-based detection (Phase 2)
│   │   │   │   └── reconciliation.py  # Cross-check schedule vs visual
│   │   │   └── takeoff/
│   │   │       ├── orchestrator.py    # Main pipeline
│   │   │       └── confidence.py      # Confidence scoring
│   │   ├── workers/          # Celery tasks
│   │   │   └── tasks.py
│   │   └── schemas/          # Pydantic models for API I/O
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── fixtures/         # Sample PDFs for testing
│   ├── alembic/              # Database migrations
│   └── pyproject.toml
├── frontend/
│   ├── app/                  # Next.js App Router
│   │   ├── (auth)/
│   │   ├── (dashboard)/
│   │   │   ├── plans/
│   │   │   └── takeoffs/
│   │   └── api/              # Next.js API routes (thin proxy only)
│   ├── components/
│   │   ├── ui/               # shadcn/ui components
│   │   ├── plan-viewer/      # PDF viewer with overlays
│   │   └── takeoff-editor/   # Verification UI
│   ├── lib/
│   │   ├── api.ts            # Backend API client
│   │   └── utils.ts
│   └── package.json
├── data/                     # Training data, sample plans (git-ignored)
├── docs/
│   ├── PROJECT_FOUNDATION.md # This file
│   ├── API.md                # API contract documentation
│   ├── PHASE_1_SPEC.md       # Per-phase build specs
│   └── DECISIONS.md          # Architectural decision log
└── docker-compose.yml        # Local dev environment
```

---

## 5. Database Schema (Core Tables)

This is the v1 schema. Any changes require updating this document first.

```sql
-- Users and organisations
CREATE TABLE organisations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id UUID REFERENCES organisations(id),
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    role TEXT NOT NULL DEFAULT 'member',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Plans and projects
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id UUID NOT NULL REFERENCES organisations(id),
    name TEXT NOT NULL,
    address TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id),
    filename TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    page_count INTEGER,
    pdf_type TEXT, -- 'vector', 'raster', 'mixed'
    uploaded_by UUID REFERENCES users(id),
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE plan_pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    page_type TEXT, -- 'floor_plan', 'elevation', 'section', 'schedule', 'site_plan', 'detail', 'unknown'
    page_title TEXT,
    scale TEXT, -- e.g. '1:100'
    width_mm NUMERIC,
    height_mm NUMERIC,
    UNIQUE (plan_id, page_number)
);

-- Takeoff runs (one plan can have multiple takeoff runs as we re-process)
CREATE TABLE takeoffs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID NOT NULL REFERENCES plans(id),
    status TEXT NOT NULL DEFAULT 'pending', -- pending, processing, completed, failed, needs_review
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    processing_log JSONB, -- Detailed log of what happened
    total_confidence NUMERIC -- Overall confidence score 0.0-1.0
);

-- Individual detected elements
CREATE TABLE takeoff_elements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    takeoff_id UUID NOT NULL REFERENCES takeoffs(id) ON DELETE CASCADE,
    element_type TEXT NOT NULL, -- 'door', 'window', 'wall', 'room' etc.
    element_subtype TEXT, -- 'single_door', 'sliding_window' etc.
    schedule_id TEXT, -- e.g. 'D01', 'W05' from the drawing schedule
    page_id UUID REFERENCES plan_pages(id),
    bounding_box JSONB, -- {x, y, width, height} in page coordinates
    properties JSONB, -- type-specific: size, material, etc.
    source TEXT NOT NULL, -- 'schedule', 'visual_detection', 'vision_model', 'manual'
    confidence NUMERIC NOT NULL, -- 0.0-1.0
    status TEXT NOT NULL DEFAULT 'detected', -- 'detected', 'verified', 'corrected', 'rejected'
    verified_by UUID REFERENCES users(id),
    verified_at TIMESTAMPTZ,
    original_properties JSONB -- For audit: what we originally detected before correction
);

-- Pricing (to be expanded in Phase 4)
CREATE TABLE price_lists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id UUID REFERENCES organisations(id), -- NULL = global/default
    name TEXT NOT NULL,
    region TEXT, -- 'NSW', 'VIC', 'QLD' etc
    valid_from DATE,
    valid_to DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE price_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    price_list_id UUID NOT NULL REFERENCES price_lists(id) ON DELETE CASCADE,
    item_code TEXT,
    description TEXT NOT NULL,
    unit TEXT NOT NULL, -- 'each', 'm', 'm2', 'm3', 'lm' etc.
    unit_price_ex_gst NUMERIC NOT NULL,
    supplier TEXT,
    match_rules JSONB -- How to match this price to an element (type, size range, material)
);
```

---

## 6. API Contract Principles

All API endpoints follow these conventions. Do not deviate.

- **Base path:** `/api/v1/`
- **Authentication:** Bearer token in `Authorization` header
- **Content-Type:** `application/json` except for file upload endpoints
- **Errors:** Standard problem+json format: `{ type, title, status, detail, instance }`
- **Pagination:** Cursor-based, not offset: `?cursor=xxx&limit=50`
- **Timestamps:** ISO 8601 UTC, e.g. `2026-04-20T14:30:00Z`
- **IDs:** UUIDs as strings, never integers
- **Nullability:** Explicit in response schemas; never omit keys that are null

### Core Endpoints (v1)

```
POST   /api/v1/plans                      Upload plan (returns presigned URL)
GET    /api/v1/plans/{plan_id}            Get plan details
GET    /api/v1/plans/{plan_id}/pages      List pages with classification
POST   /api/v1/plans/{plan_id}/takeoff    Trigger takeoff processing
GET    /api/v1/takeoffs/{takeoff_id}      Get takeoff status and results
PATCH  /api/v1/takeoff-elements/{id}      Update a detected element (user correction)
POST   /api/v1/takeoffs/{id}/export       Export takeoff (CSV, XLSX, PDF)
```

---

## 7. Coding Standards

### Python
- **Type hints everywhere.** `mypy --strict` must pass with zero errors.
- **No unused variables, imports, or parameters.** `ruff check` must pass clean.
- **Docstrings on all public functions** (Google style):
```python
def extract_schedule(pdf_path: Path, page_number: int) -> list[ScheduleEntry]:
    """Extract door or window schedule from a plan page.

    Args:
        pdf_path: Path to the PDF file.
        page_number: 1-indexed page number containing the schedule.

    Returns:
        List of schedule entries with IDs, types, and dimensions.

    Raises:
        ScheduleNotFoundError: If no schedule table is detected on the page.
    """
```
- **No print statements in production code.** Use `structlog` for logging.
- **Dependency injection over globals.** Pass services into functions; don't import and instantiate inside.
- **Pure functions where possible.** Especially in the `services/` layer.
- **Pydantic v2 for all data models at API and service boundaries.**

### TypeScript
- **`strict: true` in tsconfig.** No `any` without a `// eslint-disable-next-line` comment explaining why.
- **Components are functions, not classes.**
- **Props interfaces exported** for reuse.
- **Server components by default;** client components opt-in with `"use client"`.
- **Data fetching in server components** or via TanStack Query hooks; never in `useEffect`.

### Both
- **Small files.** 300 lines max; split when approaching.
- **Small functions.** If a function exceeds 50 lines or has 3+ levels of nesting, split it.
- **Meaningful names.** `extract_door_schedule` not `parse_table` or `do_thing`.
- **Tests for every service function.** Unit tests should not require a database; use fakes.
- **No magic numbers.** Named constants with explanation: `DEFAULT_PDF_RENDER_DPI = 300  # Balances detail vs processing time`.

---

## 8. Phase Plan

Each phase ships independently. Do not start Phase N+1 until Phase N is tested against the sample plan set.

### Phase 1: Schedule Reader (Weeks 1-2)
**Goal:** Upload a vector PDF, extract door and window schedules, return structured data.

**Includes:**
- PDF upload endpoint + file storage
- PDF classification (vector vs raster)
- Page classification by title block
- Door/window schedule detection and parsing
- Basic frontend: upload → view extracted schedule
- Test suite against 30 sample plans

**Explicitly excludes:** CV, visual detection, pricing, user accounts (hardcoded single-user for v1).

### Phase 2: Floor Plan Reconciliation (Weeks 3-4)
**Goal:** Cross-check schedule entries against the floor plan using text labels.

**Includes:**
- Floor plan page identification
- Text extraction with positions from floor plan pages
- Matching schedule IDs (D01, W05) to positions on the plan
- Mismatch detection and flagging
- Verification UI: show overlays, let user confirm/correct

### Phase 3: Linear and Area Measurements (Weeks 5-8)
**Goal:** Calculate walls, floor areas, skirting, plaster.

**Includes:**
- Scale bar detection
- Wall detection (vector and raster paths)
- Room segmentation
- Area calculations with opening subtraction
- Waste factor configuration

### Phase 4: Pricing Integration (Weeks 9-10)
**Goal:** Connect takeoff quantities to a pricing database and produce a costed bill of materials.

### Phase 5: CV Symbol Detection (Weeks 11-16)
**Goal:** Handle raster plans and plans without schedules using a trained YOLO model.

### Phase 6+: Counts (power points, fittings), services (electrical, plumbing), site works.

---

## 9. Test Data Strategy

- Sample plans live in `data/sample_plans/` (git-ignored; stored separately)
- Each plan is accompanied by a `plan_name.truth.json` file with ground-truth counts and IDs
- The test suite runs the pipeline against all sample plans and computes accuracy metrics
- Minimum sample set for v1: 30 plans across: volume builder (10), architect custom (10), draftsperson (10)
- Expand to 100+ as plans become available

Truth file format:
```json
{
  "plan_name": "smith_residence.pdf",
  "doors": {
    "total": 14,
    "entries": [
      { "id": "D01", "type": "entry_door", "width_mm": 920 },
      { "id": "D02", "type": "internal_hinged", "width_mm": 820 }
    ]
  },
  "windows": { "total": 12, "entries": [...] },
  "notes": "Schedule on page 3; one window missing ID on floor plan."
}
```

---

## 10. Session Hygiene for Claude Code

When working with Claude Code on this project, follow these practices:

### Starting a session
1. `cd` into the project root
2. Reference this document: "Read PROJECT_FOUNDATION.md and the current phase spec before proceeding."
3. State the specific task in one sentence.
4. Link to relevant existing code if building on it.

### During a session
- If Claude suggests a stack change, library change, or schema change: stop. Update the foundation document first. Then resume.
- If Claude writes code that violates coding standards: point to the specific section of this document.
- Keep sessions focused on one feature. Start a new session for a new concern.

### Ending a session
- Ensure tests pass.
- Update `docs/DECISIONS.md` with any non-trivial decisions made.
- Commit with a descriptive message referencing the phase and task.

### Red flags to watch for
- "Let me just install a new library" without discussion — stop and evaluate
- Claude losing track of the schema or stack — re-attach the foundation document
- Sprawling functions or files — refuse to merge; ask for a split
- "Let me rewrite this to be cleaner" — reject unless scope is defined

---

## 11. Decisions Log Pointer

All non-trivial architectural decisions are logged in `docs/DECISIONS.md` in ADR (Architecture Decision Record) format. Each entry includes: context, decision, consequences. Do not make architectural decisions that aren't captured there.

---

## 12. Open Questions (to resolve before Phase 1 kickoff)

- [ ] Commercial model (SaaS vs desktop vs internal) — affects auth, multi-tenancy, billing
- [ ] Hosting decision (Railway vs Render vs self-hosted)
- [ ] Whether to use Supabase (auth + db + storage) vs separate services
- [ ] Sample plan set sourcing (need 30+ real Australian plans)
- [ ] Legal: are there copyright concerns with processing plans uploaded by users? (Likely need terms of service allowing processing)

---

*End of Foundation Document. This file is the single source of truth for project-wide decisions. Update it before making architectural changes in code.*
