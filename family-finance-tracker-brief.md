# Family Finance Tracker — Build Brief (v2)

## Project Summary

A self-hosted, Docker-based personal finance web app for a family of 3 (husband, wife, kid).
It polls a shared IMAP inbox for forwarded bank statements, card statements, invoices, and vouchers,
uses AI to extract transactions and balances, and presents a polished, responsive dashboard
with charts, multi-currency support, and a smart entity/category learning system.

Runs entirely on a local LAN (no internet exposure). Docker Compose, single command to start.

---

## Non-Negotiables

- **No currency mixing, ever.** CRC and USD are always kept separate. When both appear in a
  report or table, use two columns or two chart series. Never convert, never blend. Currency
  is a first-class dimension.
- **Multi-person from day one.** Every account, transaction, and report is scoped to a Person.
  The system infers ownership from account/card details found in the documents themselves.
- **Pluggable AI providers.** The app must support Claude API, Gemini API, and LM Studio
  (local, OpenAI-compatible endpoint) with the ability to switch from the UI settings page
  at runtime, no restart required. **Default is Gemini.**
- **Entity aliasing is core infrastructure**, not a nice-to-have. All detected names (banks,
  merchants, accounts, issuers) go through a canonical entity resolution system.
- **Two-tier category rules.** Categorization keys on `(entity, memo_pattern)` — not just
  entity — so that transfers to the same person can resolve to different categories based on
  the memo text. See section below.
- **Reconciliation on every statement.** Use the bank's own opening/closing/totals to validate
  the AI's extraction before committing transactions. See section below.
- **Transaction-level deduplication.** Beyond message-id email dedup, every transaction has a
  content-derived natural key so re-uploads, overlapping statements, and re-forwards don't
  duplicate data.
- **Clean, polished, responsive UI.** Functional and beautiful. Mobile and desktop ready.
  Think Actual Budget / Copilot Money — not a corporate BI dashboard, not a bare CRUD app.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | Python, FastAPI |
| Background jobs | APScheduler (in-process, IMAP poll) + FastAPI `BackgroundTasks` for the parse pipeline |
| Database | PostgreSQL |
| Frontend | React + Tailwind CSS + **Tremor** (dashboard components, wraps Recharts internally) |
| PDF parsing | pdfplumber (text PDFs only — see note) |
| Email | imaplib / IMAPClient (Python) |
| Auth | JWT, bcrypt-hashed passwords stored in DB, admin bootstrapped from env |
| Containerization | Docker Compose |
| Reverse proxy | Nginx (serves frontend, proxies API) |

**On OCR:** Deferred. All target banks (starting with Banco Nacional CR) emit text PDFs.
We will add `pytesseract` only if/when a bank delivers scanned-image PDFs. Adding it later is
a localized change in `pdf_extractor.py`.

**On Celery/Redis:** Not used. APScheduler triggers the 5-minute IMAP poll inside the FastAPI
process; new emails enqueue parse work into an asyncio bounded queue (concurrency-limited).
This is the right size for ~hundreds of transactions per month and one to three accounts per
person. If we ever need to scale out (heavier local-model inference, multiple users beyond the
family), the parse pipeline is already structured as pure-ish functions taking IDs — swapping
the in-process executor for a Celery worker is mechanical.

---

## Docker Compose Services

```
services:
  db          → PostgreSQL
  backend     → FastAPI app (includes APScheduler for IMAP polling, in-process worker)
  frontend    → React app built and served via Nginx
```

Single `.env` file at project root for all configuration. No secrets in code.

---

## Environment Variables (`.env`)

```
# IMAP (Gmail or any IMAP-capable provider)
IMAP_HOST=imap.gmail.com
IMAP_PORT=993
IMAP_USER=
IMAP_PASSWORD=                      # Gmail app password recommended
IMAP_FOLDER=INBOX
IMAP_POLL_INTERVAL_MINUTES=5

# Database
POSTGRES_DB=financedb
POSTGRES_USER=finance
POSTGRES_PASSWORD=

# AI Provider (claude | gemini | lmstudio) — default gemini
AI_PROVIDER=gemini
GEMINI_API_KEY=
CLAUDE_API_KEY=
LMSTUDIO_BASE_URL=http://host.docker.internal:1234/v1
LMSTUDIO_MODEL=

# Auth
SECRET_KEY=                         # JWT signing
ADMIN_EMAIL=                        # Seeded on first run if no admin exists
ADMIN_PASSWORD=                     # Hashed and stored on first run; can then be removed from .env
JWT_ACCESS_TTL_MINUTES=60
JWT_REFRESH_TTL_DAYS=7
```

---

## Auth & User Management

- On first startup, if no `users` row exists, the backend creates an admin from
  `ADMIN_EMAIL` / `ADMIN_PASSWORD`, bcrypt-hashes the password, stores it, and logs a notice.
  The env vars can be cleared after first boot.
- Two roles: `admin` and `member`. Admin can invite users, reset passwords, manage system
  settings. Members use the app.
- **Invite flow:** admin clicks "Add user", enters email and a temporary password. New user
  signs in and is forced to change password on first login.
- **Password reset:** admin-driven. Admin clicks "Reset" on a user, enters a new temp
  password, gives it to the user out of band. No email-based reset flow.
- JWT access + refresh tokens. Refresh extends sliding window on activity.
- Sessions revoke on password change.

### `users`
| Field | Type | Notes |
|---|---|---|
| id | UUID PK | |
| email | text UNIQUE | |
| password_hash | text | bcrypt |
| role | enum | `admin`, `member` |
| person_id | FK → persons (nullable) | Links the user to "their" person for default scoping |
| must_change_password | boolean | Forced on first login or after admin reset |
| created_at | timestamp | |
| last_login_at | timestamp | |

---

## Data Model

### `persons`
| Field | Type | Notes |
|---|---|---|
| id | UUID PK | |
| name | text | Display name |
| created_at | timestamp | |

### `entities`
Central table for all named things: banks, merchants, card issuers, etc.

| Field | Type | Notes |
|---|---|---|
| id | UUID PK | |
| canonical_name | text | The "real" name, user-confirmed |
| display_name | text | User's preferred label |
| type | enum | `bank`, `merchant`, `issuer`, `person`, `other` |
| confirmed | boolean | Has a human reviewed this entity? |
| created_at | timestamp | |

Note: `person` type is for human payees (e.g., transfers to a relative, a contractor). They
behave like merchants in the rule system but are visually distinguished in the UI.

### `entity_patterns`
Many-to-one. Raw strings that map to an Entity.

| Field | Type | Notes |
|---|---|---|
| id | UUID PK | |
| entity_id | FK → entities | |
| pattern | text | Raw string as seen in PDF/email |
| normalized | text | Lowercase, stripped, accent-stripped, for fuzzy matching |
| source | enum | `auto_detected`, `user_added`, `ai_suggested` |
| created_at | timestamp | |

### `accounts`
| Field | Type | Notes |
|---|---|---|
| id | UUID PK | |
| person_id | FK → persons | Owner |
| bank_entity_id | FK → entities | The bank |
| issuer_entity_id | FK → entities | Card issuer if applicable |
| account_type | enum | `checking`, `savings`, `credit_card`, `loan`, `other` |
| currency | enum | `CRC`, `USD` |
| nickname | text | User-defined label |
| account_number_hint | text | Last 4 digits or partial, for matching |
| last_known_balance | numeric | Updated on each statement |
| balance_as_of | date | Date of last balance update |
| confirmed | boolean | Has user reviewed/confirmed this account? |
| created_at | timestamp | |

### `categories`
| Field | Type | Notes |
|---|---|---|
| id | UUID PK | |
| name | text | "Groceries", "School", "Utilities", etc. |
| color | text | Hex color for UI |
| icon | text | Optional icon name |
| is_system | boolean | Built-in defaults vs user-created |

### `category_rules` (two-tier)

The big change. A rule can scope by entity, by memo pattern, or both. Priority breaks ties.

| Field | Type | Notes |
|---|---|---|
| id | UUID PK | |
| entity_id | FK → entities (nullable) | If NULL, rule is entity-agnostic (e.g. "anything containing AMAZON") |
| memo_pattern | text (nullable) | Pattern string, interpreted per `match_type` |
| match_type | enum | `any`, `contains`, `exact`, `regex` |
| category_id | FK → categories | |
| priority | integer | Higher wins. Default: entity+memo rule = 100, entity-only = 50, memo-only = 25 |
| source | enum | `user_confirmed`, `ai_suggested` |
| created_at | timestamp | |

**Constraints:**
- At least one of `entity_id` or `memo_pattern` must be non-null
- `(entity_id, memo_pattern, match_type)` is unique to prevent duplicate rules

**Resolution algorithm** for a transaction with `entity = E`, `description = D`:

1. Fetch all rules where `entity_id = E` OR `entity_id IS NULL`
2. Order by `priority DESC, created_at DESC`
3. For each rule, evaluate the memo predicate against `D`:
   - `match_type=any` → matches always (entity-only fallback)
   - `match_type=contains` → case-insensitive substring on normalized description
   - `match_type=exact` → case-insensitive equality on normalized description
   - `match_type=regex` → Python `re.search` on normalized description
4. First match wins → set `category_id`, `category_source=rule`
5. No match → leave `category_id` NULL, set `needs_review=true`

### `transactions`
| Field | Type | Notes |
|---|---|---|
| id | UUID PK | |
| account_id | FK → accounts | |
| date | date | Transaction date |
| posted_date | date | Posting date if different |
| description_raw | text | Exactly as seen in statement |
| description_normalized | text | For fuzzy matching and dedup |
| merchant_entity_id | FK → entities | Resolved merchant/payee (nullable) |
| amount | numeric(18,2) | Always positive |
| direction | enum | `debit`, `credit` |
| currency | enum | `CRC`, `USD` |
| category_id | FK → categories | Nullable until categorized |
| category_source | enum | `rule`, `ai_suggested`, `user_set` |
| dedup_key | text | sha256 hex digest, see Dedup section |
| needs_review | boolean | Flagged for user attention |
| created_at | timestamp | |

**Indexes:**
- `UNIQUE (account_id, dedup_key)` — enforces dedup at the DB level
- `(account_id, date DESC)` — primary query pattern
- `(category_id, date DESC)` — category reports
- `(merchant_entity_id)` — entity drill-down

### `transaction_documents`
Many-to-many: a transaction can be confirmed by multiple source documents (audit trail when
the same transaction shows up in two statements or a re-uploaded document).

| Field | Type | Notes |
|---|---|---|
| transaction_id | FK → transactions | |
| document_id | FK → documents | |
| PRIMARY KEY (transaction_id, document_id) | | |

### `emails`
| Field | Type | Notes |
|---|---|---|
| id | UUID PK | |
| message_id | text UNIQUE | IMAP message-id header |
| received_at | timestamp | |
| sender | text | |
| subject | text | |
| status | enum | `pending`, `processing`, `processed`, `failed`, `skipped` |
| error_message | text | If failed |
| raw_stored_path | text | Path to stored raw email file (Docker volume) |

### `documents`
| Field | Type | Notes |
|---|---|---|
| id | UUID PK | |
| email_id | FK → emails | |
| doc_type | enum | `pdf`, `html_body`, `plain_text` |
| filename | text | Original filename if attachment |
| extracted_text | text | Full text after parsing |
| ai_raw_response | jsonb | Raw JSON from AI parse |
| reconciliation_status | enum | `passed`, `failed`, `not_applicable` |
| reconciliation_details | jsonb | Computed totals vs claimed totals |
| derived_quality_score | float | 0–1, computed from structural checks (see AI section) |
| processed_at | timestamp | |

---

## AI Provider Abstraction

`AIProvider` abstract base class in `backend/app/ai/base.py`:

```python
class AIProvider(ABC):
    @abstractmethod
    async def parse_financial_document(self, text: str) -> FinancialParseResult:
        pass

    @abstractmethod
    async def suggest_entity_match(self, raw_name: str, candidates: list[str]) -> str | None:
        pass

    @abstractmethod
    async def suggest_category(self, description: str, available_categories: list[str]) -> str | None:
        pass
```

Implementations:
- `backend/app/ai/gemini_provider.py` → Google AI SDK (**default**)
- `backend/app/ai/claude_provider.py` → Anthropic SDK
- `backend/app/ai/lmstudio_provider.py` → OpenAI-compatible HTTP

Active provider is loaded at runtime from the `AI_PROVIDER` env var or from the DB setting if
the user changed it in the UI. A `ProviderFactory` resolves it per request.

### Standard AI Parse Output

All providers return this JSON. **No `confidence` field** — see Quality Score below.

```json
{
  "account_hint": "Visa ****4521",
  "bank_hint": "Banco Nacional",
  "person_hint": "Juan Pérez",
  "currency": "CRC",
  "statement_date": "2025-04-30",
  "period_start": "2025-04-01",
  "period_end": "2025-04-30",
  "opening_balance": 110000.00,
  "closing_balance": 125000.00,
  "claimed_debit_count": 12,
  "claimed_debit_total": 45000.00,
  "claimed_credit_count": 2,
  "claimed_credit_total": 60000.00,
  "transactions": [
    {
      "date": "2025-04-12",
      "posted_date": "2025-04-13",
      "description": "SUPERMERCADO PERIMERCADO",
      "amount": 34500.00,
      "direction": "debit"
    }
  ]
}
```

The prompt template lives in `backend/app/ai/prompts/parse_statement.jinja2` so iteration is
schema-free.

### Derived Quality Score (replaces self-reported confidence)

Compute after parse, store in `documents.derived_quality_score`. Each check contributes equally;
final score is the proportion of checks that passed:

1. Output is valid JSON matching the schema
2. All required fields present and well-typed
3. All transaction dates fall within `[period_start, period_end]`
4. `len(transactions) == claimed_debit_count + claimed_credit_count`
5. Reconciliation passes (see below)
6. No transaction has zero or negative amount
7. Currency is one of the supported set

Documents with score < 0.85 are auto-flagged `needs_review` on every transaction they produced.

---

## Reconciliation

Run after AI parse, before transaction insert. The Banco Nacional statement format (and most
others) gives us:

- `opening_balance`, `closing_balance`
- `claimed_debit_count`, `claimed_debit_total`
- `claimed_credit_count`, `claimed_credit_total`

**Checks:**

1. `sum(t.amount for t in extracted if t.direction == 'debit') == claimed_debit_total` (within $0.01)
2. `sum(t.amount for t in extracted if t.direction == 'credit') == claimed_credit_total` (within $0.01)
3. `count(debits) == claimed_debit_count` and same for credits
4. `opening_balance + claimed_credit_total - claimed_debit_total == closing_balance` (within $0.01)

**Outcomes:**

- All pass → `reconciliation_status = passed`, transactions inserted normally
- Any fail → `reconciliation_status = failed`, store the diff in `reconciliation_details`,
  proceed with insert but mark every produced transaction `needs_review = true`, surface the
  document in the inbox with the specific failure ("debit total off by $4.00 — likely missed one")
- Statement format doesn't expose totals → `not_applicable`, skip checks

---

## Transaction Deduplication

Every transaction gets a content-derived `dedup_key`:

```python
dedup_key = sha256(
    f"{account_id}|{date.isoformat()}|{amount:.2f}|{direction}|{normalized_description}"
).hexdigest()
```

**Description normalization:**

- Lowercase
- Accent-strip (`unicodedata.normalize('NFKD', ...)`)
- Strip punctuation
- Collapse whitespace
- **Drop bank-internal numeric reference IDs** — long digit runs (≥6 digits) at the start of
  descriptions are reference numbers that vary across statement re-issues. Replace with `[REF]`
  before hashing.

**Insert behavior:**

- DB has `UNIQUE (account_id, dedup_key)`
- `INSERT ... ON CONFLICT DO NOTHING RETURNING id` — if conflict, fetch the existing
  transaction and append the new `document_id` to `transaction_documents`
- Log the dedup hit so we can see how often it triggers

**Edge case:** two genuinely identical transactions on the same day. Banks almost always
disambiguate with a sequence number or merchant ref in the description; if not, we miss one.
Acceptable tradeoff. Surfaced in the email log so the user can manually add it if needed.

---

## Email → Transaction Pipeline

Triggered every `IMAP_POLL_INTERVAL_MINUTES` by APScheduler running in-process in the backend
container. New emails enqueue work into an asyncio bounded queue; an in-process worker
processes them with a small concurrency cap (default 2).

```
1. ImapPoller (APScheduler, every N minutes)
   └─ Connects to IMAP, fetches new unseen emails (UID-based)
   └─ Stores raw email to volume, creates Email record (status=pending)
   └─ Enqueues ParseEmailJob

2. ParseEmailJob
   └─ Extracts body (HTML → plain text) and attachments (PDF)
   └─ Creates Document records
   └─ For each: ExtractTextStep → AIParseStep → ReconcileStep → ResolveEntitiesStep → CreateTransactionsStep

3. ExtractTextStep
   └─ PDF: pdfplumber
   └─ HTML: strip tags, normalize whitespace
   └─ Plain text: clean and store
   (OCR fallback intentionally not implemented yet — add when a non-text-PDF source appears)

4. AIParseStep
   └─ Active AIProvider.parse_financial_document(text)
   └─ Stores raw JSON in documents.ai_raw_response

5. ReconcileStep
   └─ Runs the four reconciliation checks
   └─ Computes derived_quality_score
   └─ Sets documents.reconciliation_status

6. ResolveEntitiesStep
   └─ For each detected name (bank, merchant, account hint, person):
       a. Normalize
       b. Exact match against entity_patterns → link
       c. Fuzzy match (Jaccard, Levenshtein) → auto-link if score > threshold
       d. AI suggestion against top candidates
       e. No match → create UnresolvedEntity for inbox

7. CreateTransactionsStep
   └─ Match/create Account record
   └─ Compute dedup_key for each transaction
   └─ INSERT ... ON CONFLICT DO NOTHING → on conflict, link document via transaction_documents
   └─ Apply category_rules with two-tier resolution
   └─ Flag uncategorized or low-quality-score transactions as needs_review
   └─ Update account.last_known_balance and balance_as_of (only if reconciliation passed)
   └─ Mark Email as processed
```

On any step failure: mark Email status=failed, store error, do not retry automatically. User
can trigger reprocess from UI.

**Idempotency:** every step is safe to re-run. Email-level: message_id dedup. Transaction
level: dedup_key. Entity-level: pattern uniqueness.

---

## Entity Resolution System

### Matching Algorithm (in order)

1. **Exact match** on `entity_patterns.pattern` (case-insensitive)
2. **Normalized match** on `entity_patterns.normalized`
   (lowercase, accent-strip, punctuation-strip, collapse spaces)
3. **Token overlap score** — Jaccard similarity on tokens.
   ≥ 0.6 → auto-link. 0.4–0.6 → suggest with confidence shown.
4. **AI suggestion** — send raw name + top 5 candidate entity names. Returns best match or "new entity".
5. **No match** → create unresolved entry for user inbox.

### Unresolved Entity UI Flow

When a new raw string arrives with no match:

```
New name detected: "BNServicios"
Suggested match:   Banco Nacional de Costa Rica  [85% overlap]

  [✓ Yes, same entity]   [✗ It's different]   [+ Create new entity]
```

- **Yes** → adds the raw string as a new pattern under that entity
- **It's different** → user names the new entity
- **Create new** → explicit new entity, user names and types it

### Editing Entities

On any transaction, account, or entity detail view:
- Rename (updates `display_name`, preserves `canonical_name`)
- Add a pattern manually ("Also known as...")
- Detach a pattern and reassign to another entity

---

## Category System

### Default Categories (seeded on first run)

Food & Dining, Groceries, Transport, Fuel, Utilities, Entertainment, Health, Education,
Shopping, Travel, Income, Transfers, Fees & Charges, Other.

### Categorization UX (the rule-creation moment)

When a user categorizes a flagged transaction in the inbox, the modal asks **scope**:

```
Categorize "YOCK ZUNIGA PAOLA/ANGIE 202616 BECA 36" as Education?

  Apply this category to:
  ( ) Just this transaction
  ( ) All transactions to YOCK ZUNIGA PAOLA          (entity rule)
  (●) All to YOCK ZUNIGA PAOLA where memo contains "BECA"   (entity + memo rule, recommended)
  ( ) All transactions where memo contains "BECA"           (memo-only rule)
  ( ) Custom pattern...                                      (regex)
```

The "memo contains X" suggestion picks the most distinctive non-stopword token from the memo
(short language-aware stopword list for ES/EN). User can override.

Confirming the rule:
1. Sets `category_id` on this transaction with `category_source=user_set`
2. Creates a `category_rules` row with the chosen scope and `priority` defaulted by scope type
3. Re-applies rules retroactively to all currently uncategorized transactions

### AI Category Suggestion

On first parse, the AI also suggests a category per transaction. Shown as a chip on the inbox
row. Clicking the chip = same scope picker pre-filled with the suggested category. Confirming
creates the rule with `source=ai_suggested` (still a real rule, just labeled).

---

## API Endpoints (FastAPI)

### Auth
```
POST   /api/auth/login
POST   /api/auth/refresh
POST   /api/auth/logout
POST   /api/auth/change-password
```

### Users (admin only)
```
GET    /api/users
POST   /api/users                 (invite with temp password)
PATCH  /api/users/{id}
POST   /api/users/{id}/reset-password
DELETE /api/users/{id}
```

### Core Resources
```
GET    /api/persons
POST   /api/persons
PATCH  /api/persons/{id}

GET    /api/accounts
POST   /api/accounts
PATCH  /api/accounts/{id}

GET    /api/transactions          ?person_id= &account_id= &category_id= &currency= &from= &to= &needs_review=
PATCH  /api/transactions/{id}     (set category, mark reviewed)
POST   /api/transactions/recategorize-all   (admin: re-apply all rules)

GET    /api/entities              ?type= &confirmed=
PATCH  /api/entities/{id}
POST   /api/entities/{id}/patterns
DELETE /api/entity-patterns/{id}

GET    /api/unresolved-entities
POST   /api/unresolved-entities/{id}/resolve

GET    /api/categories
POST   /api/categories
PATCH  /api/categories/{id}

GET    /api/category-rules
POST   /api/category-rules        (with scope: entity_id, memo_pattern, match_type)
DELETE /api/category-rules/{id}

GET    /api/emails                ?status=
POST   /api/emails/{id}/reprocess

GET    /api/documents/{id}        (includes reconciliation_status, derived_quality_score)

GET    /api/reports/summary       ?from= &to= &person_id= &currency=
GET    /api/reports/by-category   ?from= &to= &person_id= &currency=
GET    /api/reports/monthly       ?year= &person_id= &currency=
GET    /api/reports/income-vs-expense ?from= &to= &person_id=

GET    /api/settings
PATCH  /api/settings              (AI provider, polling interval, etc.)
POST   /api/settings/test-ai
POST   /api/settings/test-imap
```

---

## Frontend Pages & Components

### Pages

| Route | Description |
|---|---|
| `/` | Dashboard overview |
| `/transactions` | Full transaction list with filters |
| `/accounts` | Account list and detail |
| `/persons` | Family members |
| `/entities` | Banks, merchants, issuers, persons |
| `/categories` | Category management |
| `/rules` | Category rules — view, edit, delete, see priority |
| `/inbox` | Unresolved entities + uncategorized transactions + low-quality documents |
| `/reports` | Charts and graphs |
| `/emails` | Email + document processing log (with reconciliation status badges) |
| `/users` | User management (admin only) |
| `/settings` | IMAP, AI provider, polling config |

### Dashboard Overview

- Account balance cards — one per account, grouped by person, currency clearly shown
- Monthly spending summary (this month vs last month) — separate CRC and USD
- Recent transactions (last 10)
- Inbox badge — total items needing attention
- Top spending categories this month (donut chart per currency)

### Reports Page

- Monthly bar chart — income vs expenses per month, per currency
- Category breakdown — donut or bar, filterable by person, date range, currency
- Account balance history — line chart over time
- Spending trend by category over time

All charts respect the never-mix-currencies rule.

### Inbox Page

Three sections (each with its own badge count in the nav):

1. **Unresolved Entity Names** — suggestion cards
2. **Uncategorized Transactions** — inline scope picker per item
3. **Documents Needing Review** — failed reconciliation or quality_score < 0.85, with the
   specific reason shown

---

## Multi-Currency Display Rules

These rules are absolute throughout the entire application:

- Every numeric amount is displayed with its currency symbol (₡ for CRC, $ for USD)
- Tables that could contain both currencies get two columns: `Amount (CRC)` and `Amount (USD)` — each row fills only one
- Charts with both currencies use two separate series, or a currency toggle
- Totals, summaries, balances are always per-currency — no blended totals ever
- An account's currency is fixed at creation

---

## Build Order

**Phase 1 — Foundation**
- Docker Compose (db, backend, frontend)
- PostgreSQL schema + Alembic migrations
- Settings model + `.env` loading
- Basic FastAPI app structure
- Auth: bootstrap admin from env, login/refresh/change-password
- Seed default categories

**Phase 2 — AI Providers**
- `AIProvider` abstract base
- Gemini implementation (default)
- Claude and LM Studio implementations
- Provider factory + runtime switching
- Prompt template in `parse_statement.jinja2`
- CLI tool: `python -m app.tools.parse_pdf path/to.pdf` — runs AI parse in isolation,
  prints JSON. Use this to iterate the prompt against the Banco Nacional sample without
  the full pipeline.
- `/api/settings/test-ai` endpoint

**Phase 3 — Email Pipeline**
- IMAP poller (APScheduler)
- Email storage and Document extraction
- PDF text extraction (pdfplumber)
- HTML/plain text handling
- AI parse step
- Reconciliation step
- Derived quality score
- Entity resolution
- Transaction creation with dedup_key
- Two-tier rule resolution

**Phase 4 — Core API**
- All REST endpoints
- Filtering, pagination
- Report aggregations
- User management endpoints

**Phase 5 — Frontend**
- Vite + React + Tailwind + Tremor scaffold
- Auth flow
- Account and transaction views
- Inbox (three-section)
- Entity management UI
- Rule scope picker (the categorization modal)

**Phase 6 — Dashboard & Reports**
- Tremor charts
- Monthly summaries
- Category breakdowns

**Phase 7 — Polish**
- Mobile responsiveness
- Loading/empty/error states
- Email/document processing log UI
- Settings page with live provider testing
- User management UI

**Phase 8 (later, when needed)**
- OCR fallback (pytesseract) when first non-text-PDF source appears
- Backups (pg_dump cron + offsite encrypted copy)
- If polling falls behind: Celery + Redis migration

---

## File Structure

```
/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── auth/
│   │   │   ├── jwt.py
│   │   │   ├── deps.py            # FastAPI dependencies (current_user, require_admin)
│   │   │   └── bootstrap.py       # First-run admin creation
│   │   ├── models/                # SQLAlchemy models
│   │   ├── schemas/               # Pydantic schemas
│   │   ├── api/                   # FastAPI routers
│   │   ├── ai/
│   │   │   ├── base.py
│   │   │   ├── factory.py
│   │   │   ├── gemini_provider.py
│   │   │   ├── claude_provider.py
│   │   │   ├── lmstudio_provider.py
│   │   │   └── prompts/
│   │   │       └── parse_statement.jinja2
│   │   ├── pipeline/
│   │   │   ├── imap_poller.py
│   │   │   ├── email_parser.py
│   │   │   ├── pdf_extractor.py
│   │   │   ├── reconciler.py
│   │   │   ├── quality_score.py
│   │   │   ├── entity_resolver.py
│   │   │   ├── dedup.py
│   │   │   ├── rule_engine.py     # two-tier category rule resolution
│   │   │   └── transaction_builder.py
│   │   ├── scheduler.py           # APScheduler setup
│   │   ├── worker.py              # In-process asyncio queue + worker
│   │   └── tools/
│   │       └── parse_pdf.py       # CLI for prompt iteration
└── frontend/
    ├── Dockerfile
    ├── nginx.conf
    ├── package.json
    └── src/
        ├── main.jsx
        ├── App.jsx
        ├── api/
        ├── components/
        ├── pages/
        └── hooks/
```

---

## Notes for Implementation

- Use Alembic for all DB migrations — never modify the schema directly
- All pipeline steps must be idempotent (safe to retry)
- `message_id` is the email-level dedup key; `dedup_key` is the transaction-level dedup key
- Store raw emails and PDFs on disk (Docker volume), not in the DB
- Use async SQLAlchemy throughout the backend
- The entity resolver, reconciler, dedup function, and two-tier rule engine are critical
  business logic — write unit tests for each, with the Banco Nacional sample as a fixture
- The AI prompt lives in `parse_statement.jinja2` so it can be edited without code changes
- Seed default categories on first run (check if table is empty)
- All API responses for transactions must include the currency field — never omit it
- Admin password env vars are bootstrap-only; once an admin exists in the DB, they're ignored
  (don't accidentally re-seed on restart)
