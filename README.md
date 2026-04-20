# Casa Estimation

Australian Building Takeoff Automation System. Upload an architectural PDF; get a
structured list of doors, windows, and (in later phases) walls, areas, fittings, and
prices.

This repo hosts the Phase 1 implementation: a vector-PDF schedule reader.

> Authoritative project context lives in [`PROJECT_FOUNDATION.md`](./PROJECT_FOUNDATION.md).
> Read it before making architectural decisions.

## Repository layout

```
backend/        FastAPI service, Celery workers, Alembic migrations
frontend/       Next.js 14 App Router UI
docs/           Phase specs and addenda
data/           Sample plans + truth files (git-ignored)
docker-compose.yml  Local Postgres + Redis
Makefile        Top-level dev/test/migrate/etc. targets
```

## Prerequisites

- Python 3.11+ with [`uv`](https://github.com/astral-sh/uv)
- Node 20+ with [`pnpm`](https://pnpm.io/)
- Docker (for local Postgres + Redis)

## Quick start

```bash
# 1. Bring up infra (Postgres + Redis)
make infra

# 2. Install dependencies
make install

# 3. Apply migrations and seed dev data
cp .env.example .env
make migrate
make seed
make seed-catalogue

# 4. Start backend (:8000) and frontend (:3000)
make dev

# In another shell, start the Celery worker for async takeoff processing
make dev-worker
```

Sanity check the backend:

```bash
curl http://localhost:8000/api/v1/health
# {"status": "ok"}
```

The frontend is served at <http://localhost:3000>.

## Common commands

| Command | Description |
| --- | --- |
| `make dev` | Run backend and frontend together |
| `make migrate` | Apply Alembic migrations |
| `make seed` | Seed development organisation + user |
| `make seed-catalogue` | Seed the Phase 1 element catalogue (doors/windows) |
| `make test` | Run backend (pytest) and frontend (vitest) tests |
| `make typecheck` | `mypy --strict` + `tsc --noEmit` |
| `make lint` | Ruff + ESLint |
| `make format` | Ruff format + Prettier |
| `make evaluate` | Run accuracy evaluation against sample plans |

## Phase 1 scope

Vector PDFs only. Door and window schedules. CSV export. No floor-plan reconciliation,
no pricing, no CV — see [`docs/PHASE_1_SPEC.md`](./docs/PHASE_1_SPEC.md) and
[`docs/PHASE_1_ADDENDUM.md`](./docs/PHASE_1_ADDENDUM.md) for the full spec.

## Known limitations

- Raster PDFs are rejected (Phase 5 will add OCR + CV).
- No authentication; a single hardcoded dev user is created by `make seed`.
- Sample plan corpus and accuracy evaluation harness are present but require real
  Australian plans + truth files in `data/sample_plans/` to be meaningful.
