# Family Finance Tracker

A self-hosted, Docker-based personal finance app for a family of 3. It polls a shared
IMAP inbox for forwarded bank statements, uses AI to extract transactions, and presents
a polished dashboard with multi-currency support and an entity/category learning system.

Runs on the local LAN only — no internet exposure.

## Branding & UI rules

- **Brand name: MY Finanzas** — use this in all user-facing text, titles, and labels.
  The repo/internal name stays "family-finance-tracker" but nothing shown to the user
  should say that.
- **Internal LAN hostname: `finanzas.internal`** — used in CORS allowed origins and
  nginx `server_name`. Update any config that still references `finance.internal`.
- **Language: Spanish (Costa Rica)**
  - Default locale: `es-CR`
  - Dates: `dd/MM/yyyy`; numbers: period as decimal separator, comma as thousands (₡1,234.56 / $1,234.56)
  - All UI labels, nav items, placeholders, error messages, and empty states in Spanish
  - If implementing i18n (stretch goal), use `react-i18next` with `es-CR` as the
    default locale and `en` as fallback. If not, hard-code Spanish everywhere.
- **Color palette — amber + earth brown + forest green:**

  | Token name | Hex | Use |
  |---|---|---|
  | `brown-900` | `#5C3318` | Dark earth brown — page backgrounds, sidebars |
  | `brown-600` | `#8C5E38` | Warm brown — cards, borders |
  | `amber-500` | `#C99828` | Amber — primary CTA, highlights, links |
  | `cream` | `#F0EDD5` | Cream / ivory — light text, icon fills |
  | `green-800` | `#3D5C1A` | Dark forest green — income, positive deltas |
  | `green-600` | `#6B8840` | Forest green — secondary accents, tags |

  Wire these into `tailwind.config.js` `theme.extend.colors` in Phase 5.
  Tremor's component palette should be overridden to use amber as the primary color.

## Source of truth

**Read `family-finance-tracker-brief.md` before starting any phase.** It's the canonical
spec. If anything in this file conflicts with the brief, the brief wins — update this file
to match.

## Sample documents

`samples/` contains real bank statements used as test fixtures. The Banco Nacional CR
statement in particular is the reference format the system must handle correctly.

Use these for unit tests and for iterating the AI prompt with the standalone CLI
(`backend/app/tools/parse_pdf.py`). Never commit real account numbers — the samples
are for the maintainer only and should be in `.gitignore` if the repo ever leaves
this machine.

## Tech stack (short version)

- Backend: Python + FastAPI, async SQLAlchemy, APScheduler in-process for IMAP polling
- DB: PostgreSQL, Alembic migrations
- Frontend: React + Vite + Tailwind + Tremor
- AI: pluggable provider (Gemini default, Claude, LM Studio), prompt in Jinja2 template
- Auth: JWT, bcrypt, admin bootstrapped from env on first run
- Containerization: Docker Compose, three services (db, backend, frontend)

No Celery, no Redis, no OCR — these are explicitly deferred. See brief Phase 8.

## Non-negotiables

These are absolute. Don't relax them without updating the brief first.

- **Currency is never blended.** CRC and USD are always separate columns, separate
  series, separate totals. No conversions.
- **Multi-person from day one.** Every account, transaction, and report is scoped to a Person.
- **Two-tier category rules.** A rule scopes by entity, by memo pattern, or both. Same
  payee can resolve to different categories based on memo. See brief Category section.
- **Reconciliation on every statement.** Validate AI extraction against the bank's own
  opening/closing/totals before committing transactions.
- **Transaction-level dedup.** Every transaction has a content-derived `dedup_key` with
  a unique DB constraint. On conflict, link via `transaction_documents` instead of erroring.
- **All pipeline steps are idempotent.** Safe to retry. `message_id` for email-level
  dedup, `dedup_key` for transaction-level, pattern uniqueness for entities.
- **All DB changes go through Alembic.** Never edit schema by hand.
- **All transaction API responses include the `currency` field.** Never omit it.

## Workflow

- **Use plan mode before writing code in a new area.** Propose first, then execute.
- **Phase by phase.** Don't skip ahead; each phase is independently testable. The brief
  lays out the order — follow it.
- **Commit after each green phase or logical unit.** Small commits, clear messages.
- **Run tests after any change to:** `entity_resolver`, `reconciler`, `dedup`, or
  `rule_engine`. These are the critical business logic.
- **Use the standalone `parse_pdf` CLI to iterate the AI prompt** against `samples/`
  without running the full pipeline. Build it early in Phase 2.
- **For verification, spawn a fresh code-reviewer subagent** after a phase lands. The
  agent that wrote the code is a poor reviewer of its own work.

## Project-specific gotchas

(Append to this list as we discover them.)

- Banco Nacional CR descriptions begin with a long numeric reference ID (e.g.
  `99837153 ...`). These vary across re-issues of the same statement, so they must be
  stripped before computing `dedup_key`. See the dedup section in the brief for the rule
  (≥6-digit run at start → replace with `[REF]`).
- Banco Nacional sometimes shows the same transaction date twice with the posted_date
  in the description (e.g. `28-03-26 BN-PAR/...`). Don't double-count.
- Personal-payee transfers (Paola, Olga in samples) carry the actual category in the
  free-text memo, not the payee. The two-tier rule engine exists specifically for this.
- The brief's Build Order is the recommended order. Don't try to ship Phase 3 in one
  session — split it into IMAP poller → PDF extraction → AI parse + reconciliation →
  entity resolution + dedup → transaction creation with rules.

## Models

- `sonnet` for day-to-day coding work — right balance of speed and quality.
- `opus` for hard design moments (schema decisions, the rule engine, debugging that's
  stuck for more than ~15 minutes).
- `haiku` for trivial edits or scripted tasks where speed matters more than depth.

## What good output looks like for this project

- Migrations are reversible and have clear `up`/`down`.
- Every new pipeline step has a unit test using a real sample as fixture.
- Currency type is plumbed end-to-end — DB column, Pydantic schema, API response, UI.
- Errors don't crash the worker — they update `Email.status='failed'` with a useful
  `error_message` and surface in the UI.
- The frontend never displays a number without a currency symbol.
