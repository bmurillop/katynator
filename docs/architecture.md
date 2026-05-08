# Architecture

> **Audience:** developers and AI agents continuing this project. For end-user setup, see [deployment.md](deployment.md).

## Repository Layout

```
katynator/
├── docker-compose.yml
├── .env.example
├── docs/                        ← you are here
├── backend/
│   ├── Dockerfile               # python:3.12-slim; runs alembic upgrade head then uvicorn
│   ├── requirements.txt
│   ├── pyproject.toml
│   ├── alembic/
│   │   └── versions/
│   │       ├── 0001_initial_schema.py
│   │       ├── 0002_unresolved_entity_names.py
│   │       └── 0003_seed_categories.py
│   ├── tests/
│   │   ├── pipeline/            # unit tests for critical business logic
│   │   └── api/                 # route-level tests
│   └── app/
│       ├── main.py              # FastAPI app, lifespan, CORS, router registration
│       ├── config.py            # pydantic-settings; reads .env
│       ├── db.py                # async SQLAlchemy engine + session factory
│       ├── scheduler.py         # APScheduler setup (IMAP poll job)
│       ├── worker.py            # in-process asyncio queue + concurrency cap
│       ├── auth/
│       │   ├── bootstrap.py     # first-run admin creation + category seeding
│       │   ├── deps.py          # FastAPI Depends helpers: current_user, require_admin, require_member
│       │   └── jwt.py           # token creation/verification
│       ├── models/              # SQLAlchemy ORM models
│       ├── schemas/             # Pydantic request/response schemas
│       ├── api/                 # FastAPI routers (one file per resource)
│       ├── ai/
│       │   ├── base.py          # AIProvider abstract class + FinancialParseResult
│       │   ├── factory.py       # get_provider() / get_provider_by_name()
│       │   ├── gemini_provider.py
│       │   ├── claude_provider.py
│       │   ├── lmstudio_provider.py
│       │   └── prompts/
│       │       └── parse_statement.jinja2   # THE prompt — edit this to tune extraction
│       ├── pipeline/
│       │   ├── coordinator.py        # orchestrates all steps for one document
│       │   ├── imap_poller.py        # connects to IMAP, fetches new messages
│       │   ├── email_parser.py       # extracts attachments and body text
│       │   ├── pdf_extractor.py      # pdfplumber text extraction
│       │   ├── reconciler.py         # validates AI output vs bank totals
│       │   ├── quality_score.py      # 0–1 structural quality check
│       │   ├── entity_resolver.py    # fuzzy name → entity matching
│       │   ├── dedup.py              # sha256 dedup_key computation
│       │   ├── rule_engine.py        # two-tier category rule resolution
│       │   └── transaction_builder.py # account linking, INSERT with dedup
│       └── tools/
│           └── parse_pdf.py     # standalone CLI for prompt iteration
└── frontend/
    ├── Dockerfile               # node:20 build → nginx:1.27 serve
    ├── nginx.conf               # serves SPA; proxies /api/ to backend:8000
    ├── vite.config.js
    ├── tailwind.config.js       # amber/brown/cream/green palette
    ├── package.json
    └── src/
        ├── main.jsx
        ├── App.jsx              # routes + ProtectedRoute wrapper
        ├── index.css            # global styles (.card, .btn-ghost, .input, etc.)
        ├── context/
        │   └── AuthContext.jsx  # JWT storage, user state, signIn/signOut
        ├── api/                 # thin axios wrappers (one file per resource)
        ├── components/
        │   ├── Layout.jsx       # sidebar + main content shell
        │   ├── Sidebar.jsx      # dark sidebar with nav links
        │   ├── CurrencyAmount.jsx
        │   └── Pagination.jsx
        └── pages/               # one component per route
```

---

## Database Schema

### `persons`

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| name | text | Display name |
| created_at | timestamp | |

Every account and transaction belongs to a person. This is the primary scoping dimension for all reports.

### `entities`

Central registry for all named things: banks, merchants, card issuers, family members.

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| canonical_name | text | The "real" name, user-confirmed |
| display_name | text | User's preferred label |
| type | enum | `bank`, `merchant`, `issuer`, `person`, `other` |
| confirmed | boolean | Has a human reviewed this? |
| created_at | timestamp | |

### `entity_patterns`

Many raw strings → one entity.

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| entity_id | FK → entities | |
| pattern | text | Raw string as seen in PDF/email |
| normalized | text | Lowercased, accent-stripped, for fuzzy matching |
| source | enum | `auto_detected`, `user_added`, `ai_suggested` |

### `accounts`

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| person_id | FK → persons | Owner |
| bank_entity_id | FK → entities | The bank |
| issuer_entity_id | FK → entities | Card issuer (nullable) |
| account_type | enum | `checking`, `savings`, `credit_card`, `loan`, `other` |
| currency | enum | `CRC`, `USD` — **fixed at creation, never changed** |
| nickname | text | User-defined label |
| account_number_hint | text | Last 4 digits or partial, for matching |
| last_known_balance | numeric | Updated on each passing reconciliation |
| balance_as_of | date | |
| confirmed | boolean | |

### `categories`

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| name | text | |
| color | text | Hex color |
| icon | text | Emoji or icon name |
| is_system | boolean | System defaults cannot be deleted |

**Default categories** (seeded by migration 0003): Alimentación, Transporte, Vivienda, Salud, Entretenimiento, Servicios, Educación, Ropa y Calzado, Viajes, Transferencias, Ingresos, Otros.

### `category_rules`

The two-tier rule system. A rule can match on entity, memo pattern, or both.

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| entity_id | FK → entities, nullable | If NULL, matches any entity |
| memo_pattern | text, nullable | Pattern string |
| match_type | enum | `any`, `contains`, `exact`, `regex` |
| category_id | FK → categories | |
| priority | integer | Higher wins. entity+memo=100, entity-only=50, memo-only=25 |
| source | enum | `user_confirmed`, `ai_suggested` |

**Constraint:** at least one of `entity_id` or `memo_pattern` must be non-null.
**Unique constraint:** `(entity_id, memo_pattern, match_type)` — no duplicate rules.

**Resolution algorithm** for a transaction with entity E and description D:
1. Load all rules where `entity_id = E` OR `entity_id IS NULL`
2. Sort by `priority DESC, created_at DESC`
3. For each rule: evaluate memo predicate against D
   - `any` → always matches (entity-only fallback)
   - `contains` → case-insensitive substring
   - `exact` → case-insensitive equality
   - `regex` → Python `re.search`
4. First match → set `category_id`, `category_source = rule`
5. No match → leave `category_id` NULL, set `needs_review = true`

### `transactions`

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| account_id | FK → accounts | |
| date | date | Transaction date |
| posted_date | date | Posting date if different (nullable) |
| description_raw | text | Exactly as extracted |
| description_normalized | text | For matching and dedup |
| merchant_entity_id | FK → entities, nullable | Resolved payee |
| amount | numeric(18,2) | Always positive |
| direction | enum | `debit`, `credit` |
| currency | enum | `CRC`, `USD` — **always present in API responses** |
| category_id | FK → categories, nullable | |
| category_source | enum | `rule`, `ai_suggested`, `user_set` |
| dedup_key | text | SHA-256 hex digest |
| needs_review | boolean | |

**Key index:** `UNIQUE (account_id, dedup_key)` — enforced at DB level.

### `emails`

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| message_id | text UNIQUE | IMAP Message-ID header — the email-level dedup key |
| received_at | timestamp | |
| sender | text | |
| subject | text | |
| status | enum | `pending`, `processing`, `processed`, `failed`, `skipped` |
| error_message | text | Populated on failure |
| raw_stored_path | text | Path on the Docker volume |

### `documents`

One per attachment or body part extracted from an email.

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| email_id | FK → emails | |
| doc_type | enum | `pdf`, `html_body`, `plain_text` |
| filename | text | Original filename |
| extracted_text | text | Full extracted text |
| ai_raw_response | jsonb | Raw JSON from AI provider |
| reconciliation_status | enum | `passed`, `failed`, `not_applicable` |
| reconciliation_details | jsonb | Computed vs claimed totals |
| derived_quality_score | float | 0–1; documents below 0.85 flag all their transactions `needs_review` |
| processed_at | timestamp | |

### `unresolved_entity_names`

Queue of raw names that the pipeline could not resolve to a known entity.

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| raw_name | text | Exactly as seen |
| email_id | FK → emails | Source email |
| resolved | boolean | Cleared once user acts |

---

## Pipeline Detail

### Transaction Deduplication

```python
dedup_key = sha256(
    f"{account_id}|{date}|{amount:.2f}|{direction}|{normalized_description}"
).hexdigest()
```

**Normalization steps** (applied before hashing):
1. Lowercase
2. Accent-strip (`unicodedata.normalize('NFKD', ...)`)
3. Strip punctuation
4. Collapse whitespace
5. **Drop leading numeric reference IDs** — a run of ≥6 digits at the start of the description is replaced with `[REF]`. This is a bank-agnostic normalization that handles the Banco Nacional pattern where every statement re-issue has a different internal reference number.

**On conflict:** `INSERT ... ON CONFLICT DO NOTHING RETURNING id`. If the row already exists, the new document is appended to `transaction_documents` as an audit link.

### Reconciliation Checks

Run after AI parse, before inserting transactions. All four must pass for `reconciliation_status = passed`:

1. `sum(debit amounts) ≈ claimed_debit_total` (within ±0.01)
2. `sum(credit amounts) ≈ claimed_credit_total` (within ±0.01)
3. `count(debits) == claimed_debit_count`
4. `opening_balance + claimed_credit_total − claimed_debit_total ≈ closing_balance`

If the statement does not expose these fields, `reconciliation_status = not_applicable` (a first-class outcome, not an error).

### Quality Score

Computed after reconciliation. Each check contributes 1/7 to the score:

1. Output is valid JSON matching the schema
2. All required fields present and typed correctly
3. All transaction dates within `[period_start, period_end]`
4. `count(transactions) == claimed_debit_count + claimed_credit_count`
5. Reconciliation passed
6. No transaction has zero or negative amount
7. Currency is in the supported set

Score < 0.85 → every transaction from that document gets `needs_review = true`.

### Entity Resolution Algorithm

For each raw name extracted from a document:

1. **Exact match** on `entity_patterns.pattern` (case-insensitive)
2. **Normalized match** on `entity_patterns.normalized`
3. **Token overlap** — Jaccard similarity on word tokens
   - ≥ 0.6 → auto-link
   - 0.4–0.6 → suggest with confidence displayed
4. **AI suggestion** — send raw name + top 5 candidates; AI returns best match or "new entity"
5. **No match** → create `unresolved_entity_names` row for user inbox

---

## AI Provider Interface

All three providers implement the same abstract base in `backend/app/ai/base.py`:

```python
class AIProvider(ABC):
    async def parse_financial_document(self, text: str) -> FinancialParseResult: ...
    async def suggest_entity_match(self, raw_name: str, candidates: list[str]) -> str | None: ...
    async def suggest_category(self, description: str, available_categories: list[str]) -> str | None: ...
```

`FinancialParseResult` is the Pydantic model for the standardized AI output — see `backend/app/ai/base.py` for the full field list.

The extraction prompt lives in `backend/app/ai/prompts/parse_statement.jinja2`. **Edit the Jinja2 template to tune extraction behavior** — no Python changes required for prompt iteration.

---

## CORS

Allowed origins (configured in `backend/app/main.py`):

- `http://finanzas.internal` / `https://finanzas.internal`
- `http://localhost` / `http://localhost:5173` (Vite dev) / `http://localhost:3000`

If deploying to a different hostname, add it to `_CORS_ORIGINS` in `main.py`.

---

## Named Docker Volumes

| Volume | Mounted at | Content |
|---|---|---|
| `pgdata` | `/var/lib/postgresql/data` | PostgreSQL data files |
| `raw_emails` | `/data/raw_emails` | Raw `.eml` files from IMAP |

The `RAW_EMAIL_DIR` env var must match the container mount path (`/data/raw_emails`). Changing the Docker volume mount requires updating both `docker-compose.yml` and `RAW_EMAIL_DIR`.
