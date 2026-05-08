# Build Phases

The canonical spec is `family-finance-tracker-brief.md` at the repo root. This file tracks what has been completed and what remains.

---

## Phase 1 — Foundation ✅

- Docker Compose with db, backend, frontend services
- Full PostgreSQL schema via Alembic (migration 0001)
- Admin bootstrap from env on first run
- JWT auth: login, refresh, logout, change-password
- Forced password change on first login
- Two roles: `admin` and `member`
- `GET /api/health`

## Phase 2 — AI Providers ✅

- `AIProvider` abstract base class
- Gemini provider (default)
- Claude (Anthropic SDK) provider
- LM Studio (OpenAI-compatible) provider
- Provider factory with runtime switching
- Jinja2 prompt template (`parse_statement.jinja2`)
- `parse_pdf` CLI tool for prompt iteration without the full pipeline
- `GET/PATCH /api/settings` with AI provider field

## Phase 3 — Email Pipeline ✅

- IMAP poller via APScheduler (runs in-process)
- Raw email storage to Docker volume
- Email and Document DB records
- PDF text extraction (pdfplumber)
- HTML body stripping (BeautifulSoup)
- AI parse step
- Reconciliation step (4 checks against bank totals)
- Derived quality score (0–1, 7 structural checks)
- Entity resolution (exact → normalized → fuzzy → AI → unresolved)
- Transaction creation with `dedup_key` and `ON CONFLICT DO NOTHING`
- Two-tier category rule engine
- Account auto-linking via `account_number_hint` + `bank_entity_id`
- Migration 0002: `unresolved_entity_names` table
- Migration 0003: 12 seeded system categories
- Unit tests for all critical pipeline modules

## Phase 4 — Core API ✅

- `/api/persons` CRUD
- `/api/accounts` CRUD
- `/api/transactions` list + filters + PATCH + monthly summary
- `/api/entities` list + PATCH + pattern management
- `/api/unresolved-entities` list + resolve
- `/api/categories` CRUD
- `/api/category-rules` CRUD
- `/api/emails` list + reprocess
- `/api/users` CRUD (admin only)
- Pagination on list endpoints

## Phase 5 — Frontend ✅

- Vite + React + Tailwind + Tremor scaffold
- JWT auth flow with forced password change
- All 7 pages: Dashboard, Transactions, Accounts, Inbox, Entities, Categories, Settings
- Light-background palette (cream/amber/brown), dark sidebar
- Monthly bar charts on Dashboard (CRC and USD separate series)
- Full CRUD modals for accounts, entities, categories, rules, users
- `CurrencyAmount` component — every amount shows its currency symbol
- Pagination component

---

## Phase 6 — Dashboard & Reports 🔲

- Reports page (`/informes`)
  - Monthly bar chart — income vs expenses, per currency
  - Category breakdown — donut or bar, filterable by person, date range, currency
  - Account balance history — line chart
  - Spending trend by category over time
- Dashboard: top spending categories donut chart
- Dashboard: account balance cards grouped by person

## Phase 7 — Polish 🔲

- Inbox: inline scope-picker modal for categorizing transactions
  - "Just this one" / "All to entity" / "All where memo contains X" / "Custom regex"
  - Re-applies rules retroactively on confirm
- Inbox: unresolved entity resolution cards with suggested matches
- Inbox: failed document cards with specific reconciliation diff shown
- Settings page: live IMAP test button, live AI test button
- Settings page: polling interval control
- Email/document processing log (`/bandeja/emails`)
- Mobile responsiveness polish
- Loading, empty, and error states for all pages

## Phase 8 — Later 🔲

- OCR fallback with pytesseract (only when a non-text-PDF bank appears)
- Automated pg_dump backups + encrypted offsite copy
- Celery + Redis migration (only if polling volume outgrows in-process queue)

---

## Non-Negotiables (never relax without updating the brief)

- No currency mixing — CRC and USD always separate
- Multi-person scoping on every account, transaction, and report
- Two-tier category rules keyed on `(entity, memo_pattern)`
- Reconciliation on every statement
- Transaction-level dedup via content-derived `dedup_key`
- All pipeline steps idempotent
- All DB changes through Alembic
- All transaction API responses include the `currency` field
