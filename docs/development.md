# Development Guide

## Prerequisites

- Docker + Docker Compose (for the full stack)
- Python 3.12+ (for running the backend locally)
- Node.js 20+ (for running the frontend locally)

---

## Running the Full Stack

```bash
cp .env.example .env
# fill in .env

docker compose up --build
```

The backend automatically runs `alembic upgrade head` on startup. On first boot it also creates the admin user and seeds categories.

Check logs:

```bash
docker compose logs -f backend
docker compose logs -f frontend
```

---

## Running Backend Locally (outside Docker)

Useful for faster iteration and breakpoint debugging.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Point at a running Postgres instance
export DATABASE_URL="postgresql+asyncpg://finance:changeme@localhost:5432/financedb"
export SECRET_KEY="dev-secret"
export ADMIN_EMAIL="admin@finance.internal"
export ADMIN_PASSWORD="dev-password"
export AI_PROVIDER="gemini"
export GEMINI_API_KEY="your-key"

# Apply migrations
alembic upgrade head

# Start the dev server
uvicorn app.main:app --reload --port 8000
```

The backend will be available at `http://localhost:8000`. Interactive API docs at `http://localhost:8000/docs`.

---

## Running the Frontend Locally

```bash
cd frontend
npm install
npm run dev
```

Vite dev server starts at `http://localhost:5173`. It proxies `/api/` requests to `http://localhost:8000` — make sure the backend is also running.

---

## Running Tests

```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt

pytest
```

Tests use an in-memory SQLite database via `aiosqlite` — no running Postgres required.

### What the tests cover

```
tests/pipeline/
  test_dedup.py          — dedup_key computation, normalization, leading-digit stripping
  test_reconciler.py     — all four reconciliation checks + not_applicable path
  test_entity_resolver.py — exact, normalized, and fuzzy matching
  test_rule_engine.py    — two-tier category rule resolution, priority ordering
  test_email_parser.py   — attachment extraction, HTML stripping
  test_quality_score.py  — quality score computation

tests/api/
  test_routes.py         — happy-path for each router
  test_users.py          — admin-only enforcement
  test_schemas.py        — Pydantic schema validation
```

**Always run tests after changing:** `entity_resolver`, `reconciler`, `dedup`, or `rule_engine`.

---

## The `parse_pdf` CLI

The fastest way to iterate on the AI extraction prompt without running the full pipeline.

```bash
cd backend
source .venv/bin/activate

# Basic usage — uses AI_PROVIDER env var (default: gemini)
GEMINI_API_KEY=your-key python -m app.tools.parse_pdf path/to/statement.pdf

# Choose a provider explicitly
python -m app.tools.parse_pdf path/to/statement.pdf --provider claude

# Print the raw LLM response before the parsed JSON
python -m app.tools.parse_pdf path/to/statement.pdf --raw

# Only extract PDF text (no AI call — useful for debugging extraction)
python -m app.tools.parse_pdf path/to/statement.pdf --text-only
```

Output is JSON to stdout; progress and summaries go to stderr so you can pipe the JSON directly:

```bash
python -m app.tools.parse_pdf statement.pdf | jq '.transactions | length'
```

The prompt template is at `backend/app/ai/prompts/parse_statement.jinja2`. Edit it freely — no Python changes needed.

---

## Alembic Migrations

All schema changes go through Alembic. Never modify the database by hand.

```bash
cd backend
source .venv/bin/activate

# Create a new migration (after editing models/)
alembic revision --autogenerate -m "describe what changed"

# Review the generated file in alembic/versions/ before applying
# Apply to the database
alembic upgrade head

# Roll back one step
alembic downgrade -1
```

Migration naming convention: `NNNN_short_description.py` where NNNN is a zero-padded sequence number (0001, 0002, …).

---

## Adding a New Bank

The pipeline is bank-agnostic by design. When a new bank's statements arrive:

1. Add a sample PDF to `samples/` (gitignored — real account numbers must never be committed).
2. Run the CLI to validate extraction: `python -m app.tools.parse_pdf samples/newbank.pdf --raw`
3. If extraction is wrong, edit `parse_statement.jinja2`. The prompt should describe *what to extract*, not *how this specific bank formats it*.
4. If a bank-specific quirk can't be handled generically, add a **conditional block** in the Jinja2 template keyed on `bank_hint` — never in Python code.
5. Add the bank's entity to the `entities` table via the UI (type: `bank`).

---

## Adding a New AI Provider

1. Create `backend/app/ai/yourprovider_provider.py` implementing `AIProvider` from `base.py`.
2. Register it in `backend/app/ai/factory.py` in the `get_provider_by_name` switch.
3. Add the env var(s) to `.env.example` and document them in `README.md`.
4. Add `yourprovider` as a valid choice in the settings API schema.

---

## Frontend Color Palette

Defined in `frontend/tailwind.config.js`:

| Token | Hex | Usage |
|---|---|---|
| `brown-900` | `#5C3318` | Page sidebar background |
| `brown-600` | `#8C5E38` | Card borders, dividers |
| `amber-500` | `#C99828` | Primary CTA, highlights, active nav |
| `cream` | `#F0EDD5` | Text on dark backgrounds (sidebar) |
| `green-800` | `#3D5C1A` | Income, positive amounts |
| `green-600` | `#6B8840` | Secondary accents |
| `ink` | `#2C1A0A` | Text on light backgrounds (main content area) |

**Important:** `@apply` in `index.css` cannot use `text-ink` or similar Tailwind utility classes because CSS is processed by PostCSS before Tailwind JIT scans the template files. Use plain CSS `color:` properties in `index.css`. Class strings in `.jsx` files work normally.

---

## Key Design Constraints (do not relax)

- **Currency is never blended.** CRC and USD stay in separate columns, series, and totals everywhere. No conversions, ever.
- **All DB changes go through Alembic.** Never `ALTER TABLE` by hand.
- **All API transaction responses include `currency`.** It's a required field in the response schema.
- **Pipeline steps are idempotent.** Safe to re-run. Email-level dedup on `message_id`, transaction-level on `dedup_key`.
- **Account currency is fixed at creation.** There is no migration path to change it.

---

## CLAUDE.md

`CLAUDE.md` at the repo root contains additional guidance specifically for Claude agents working on this codebase, including model recommendations, the canonical spec reference, and known gotchas with Banco Nacional statement formats.
