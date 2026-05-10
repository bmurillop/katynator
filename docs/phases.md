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

- `AIProvider` abstract base class with `parse_financial_document`, `suggest_entity_match`, `suggest_category`
- Gemini provider (default)
- Claude (Anthropic SDK) provider
- LM Studio (OpenAI-compatible) provider
- Provider factory with runtime switching from DB setting
- Jinja2 prompt template (`parse_statement.jinja2`)
- `parse_pdf` CLI tool for prompt iteration without the full pipeline
- `GET/PATCH /api/settings` with AI provider field

## The WHO / WHAT distinction

Every transaction classification answers two questions:

- **WHO** → *Entity*: the stable real-world identity behind the noisy raw bank text (a merchant, bank, person, or income source). Identified by entity rules (pattern matching) and AI fallback. Stored in `merchant_entity_id`.
- **WHAT** → *Category*: what the money was for (Groceries, Education, Transport…). Assigned by two-tier category rules keyed on `(entity + memo_pattern)`, so the same payee can map to different categories depending on the memo. Stored in `category_id`.

The pipeline resolves WHO first, then uses that result to drive the WHAT classification. Reports can filter and group by either dimension independently.

---

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
- Two-tier category rule engine (entity + memo pattern, priority-ordered)
- Account auto-linking via `account_number_hint` + `bank_entity_id`
- **Entity rules** (step 3b in resolver): pattern-based rules (contains/starts_with/exact/regex) fire after fuzzy matching and before AI, resolving WHO deterministically
- **AI category suggestions**: when no rule matches, `suggest_category` is called and result stored as `category_source=ai_suggested`
- Migration 0002: `unresolved_entity_names` table
- Migration 0003: 12 seeded system categories
- Migration 0004: `income_source` entity type
- Migration 0005: `starts_with` match type
- Migration 0006: `is_transfer` on transactions, `sets_transfer` on category_rules, nullable `category_id` on rules
- Unit tests for all critical pipeline modules

## Phase 4 — Core API ✅

- `/api/persons` CRUD
- `/api/accounts` CRUD
- `/api/transactions` list + filters + PATCH
- `/api/transactions/summary` — debit/credit totals per currency (excludes transfers)
- `/api/transactions/summary/monthly` — month-bucketed totals for charts (excludes transfers)
- `/api/transactions/summary/by-category` — debit totals grouped by category + currency (used for donut chart)
- `/api/transactions/suggest-categories` — bulk AI suggestion for all uncategorized transactions
- `/api/transactions/suggest-entities` — bulk AI suggestion for all transactions with no entity
- `/api/entity-rules` CRUD + preview + apply single + reapply all
- `/api/entities` list + PATCH + pattern management
- `/api/unresolved-entities` list + resolve + ignore
- `/api/categories` CRUD
- `/api/category-rules` CRUD + preview + apply single + reapply all
- `/api/emails` list + retry + manual poll trigger
- `/api/users` CRUD (admin only)
- Pagination on all list endpoints

## Phase 5 — Frontend ✅

- Vite + React + Tailwind + Tremor scaffold
- JWT auth flow with forced password change
- **Dashboard**: stat cards (income/expense per currency), monthly bar charts, top-categories donut chart (current month, per currency), inbox attention cards
- **Transactions**: full list with filters (person, account, currency, direction, category, date range, needs_review), inline category + transfer modal with rule creation, re-apply all rules button
- **Accounts**: list with balance, currency, confirmation status
- **Inbox** (3 tabs):
  - *Entidades sin resolver*: resolution cards with link-to-existing or create-new flow
  - *Transacciones por revisar*: expandable rows with inline category + entity editing; AI suggestion chip (violet IA badge) with one-click confirm; bulk "✦ Sugerir con IA" button
  - *Correos fallidos*: error log with retry and manual poll trigger
- **Entities**: list + detail modal with inline edit (name, display name, type)
- **Entities** (2 tabs):
  - *Entidades*: list + detail modal (edit name, type; manage exact patterns)
  - *Reglas*: entity rules — create/edit (pattern + match type → entity); re-apply all; "◈ Sugerir entidades" AI bulk button
- **Categories** (2 tabs):
  - *Categorías*: create + edit
  - *Reglas*: create + **edit** (click row or ✎ button); transfer rules (sets_transfer); live match-count preview; apply single rule; reapply all
- **Settings**: AI provider selector, IMAP config display
- Sidebar inbox badge: live count of needs_review transactions + pending unresolved entities, refreshes every 60 s
- `CurrencyAmount` component — every amount shows its currency symbol
- `CurrencyBadge`, `Pagination` components

---

## Phase 6 — Dashboard & Reports 🔲

- ✅ Top spending categories donut chart on Dashboard (done)
- 🔲 Reports page (`/informes`)
  - Monthly bar chart — income vs expenses, per currency
  - Category breakdown — donut or bar, filterable by person, date range, currency
  - Account balance history — line chart over time
  - Spending trend by category over time

## Phase 7 — Polish 🔲

- 🔲 Inbox: failed document cards with specific reconciliation diff shown
- 🔲 Settings: live IMAP test button (`POST /api/settings/test-imap`)
- 🔲 Settings: live AI test button (`POST /api/settings/test-ai`)
- 🔲 Email/document processing log page (`/emails`)
- 🔲 User management page (`/usuarios`, admin only) — invite flow, password reset
- 🔲 Persons page (`/personas`) — family member management
- 🔲 Account balance updates after reconciliation passes (`last_known_balance`, `balance_as_of`)
- 🔲 Mobile responsiveness polish
- 🔲 Loading, empty, and error states for all pages

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
