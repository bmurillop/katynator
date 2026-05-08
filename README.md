# MY Finanzas

A self-hosted, Docker-based personal finance tracker for a Costa Rican family. It polls a shared IMAP inbox for forwarded bank statements, uses AI to extract transactions, and presents a bilingual (Spanish) dashboard with multi-currency support, entity/category learning, and reconciliation against the bank's own totals.

Runs entirely on the local LAN — no internet exposure beyond the IMAP and AI API calls.

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/bmurillop/katynator.git
cd katynator

# 2. Configure
cp .env.example .env
# Edit .env — minimum required fields: see "Required env vars" below

# 3. Start
docker compose up -d

# 4. Open
# http://finanzas.internal  (if DNS is set up on the LAN)
# http://localhost          (from the host machine)
```

On first boot the backend:
1. Runs all Alembic migrations automatically
2. Creates an admin user from `ADMIN_EMAIL` / `ADMIN_PASSWORD` if no users exist
3. Seeds the 12 default system categories

Log in with the admin credentials you set in `.env`. You will be forced to change the password on first login.

---

## Environment Variables

Copy `.env.example` to `.env` and fill in the values. All services read from this single file.

### Required

| Variable | Description |
|---|---|
| `POSTGRES_DB` | Database name (e.g. `financedb`) |
| `POSTGRES_USER` | Database user |
| `POSTGRES_PASSWORD` | Database password — pick a strong one |
| `SECRET_KEY` | JWT signing key — generate with `python -c "import secrets; print(secrets.token_hex(32))"` |
| `ADMIN_EMAIL` | Bootstrap admin email (first-run only) |
| `ADMIN_PASSWORD` | Bootstrap admin password (first-run only, then you'll be forced to change it) |

### IMAP (email polling)

| Variable | Default | Description |
|---|---|---|
| `IMAP_HOST` | `imap.gmail.com` | IMAP server |
| `IMAP_PORT` | `993` | IMAP port (SSL) |
| `IMAP_USER` | — | Email address |
| `IMAP_PASSWORD` | — | Password or app password (Gmail requires an [App Password](https://myaccount.google.com/apppasswords)) |
| `IMAP_FOLDER` | `INBOX` | Folder to poll |
| `IMAP_POLL_INTERVAL_MINUTES` | `5` | How often to check for new emails |
| `RAW_EMAIL_DIR` | `/data/raw_emails` | Where to store raw `.eml` files (must match Docker volume mount) |

### AI Provider

The active provider can be changed at runtime from the Settings page without a restart.

| Variable | Default | Description |
|---|---|---|
| `AI_PROVIDER` | `gemini` | Active provider: `gemini`, `claude`, or `lmstudio` |
| `GEMINI_API_KEY` | — | Required if using Gemini |
| `CLAUDE_API_KEY` | — | Required if using Claude |
| `LMSTUDIO_BASE_URL` | `http://host.docker.internal:1234/v1` | LM Studio API base URL |
| `LMSTUDIO_MODEL` | — | Model name as returned by LM Studio |

### Auth / JWT

| Variable | Default | Description |
|---|---|---|
| `JWT_ACCESS_TTL_MINUTES` | `60` | Access token lifetime |
| `JWT_REFRESH_TTL_DAYS` | `7` | Refresh token lifetime |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Docker Compose                                         │
│                                                         │
│  ┌──────────┐   ┌───────────────────┐   ┌───────────┐  │
│  │ frontend │──▶│     backend       │──▶│    db     │  │
│  │  (nginx) │   │  (FastAPI + APSch)│   │ (Postgres)│  │
│  └──────────┘   └───────────────────┘   └───────────┘  │
│       :80             :8000 (internal)       :5432      │
└─────────────────────────────────────────────────────────┘
```

- **frontend** — React + Vite + Tailwind + Tremor, served by Nginx. Nginx also proxies all `/api/` requests to the backend.
- **backend** — FastAPI app. Runs Alembic migrations on startup, bootstraps the admin user, starts APScheduler for IMAP polling, and exposes all REST endpoints.
- **db** — PostgreSQL 16. Data persisted in the `pgdata` named volume.

### Email → Transaction Pipeline

Every `IMAP_POLL_INTERVAL_MINUTES`, the scheduler wakes up and processes new emails:

```
IMAP poll → store .eml → create Email record
  └─ for each attachment / body:
       ExtractText  (pdfplumber for PDF, BS4 for HTML)
       AIParseStep  (calls active AI provider)
       ReconcileStep (validates AI output against bank totals)
       ResolveEntities (fuzzy-match names → entity table)
       CreateTransactions (dedup_key, category rules, account linking)
```

Failed emails land in the Inbox with the specific error and a "Reprocess" button.

### AI Providers

Three interchangeable implementations all satisfy the same `AIProvider` interface:

| Provider | When to use |
|---|---|
| **Gemini** (default) | Best balance of accuracy and cost for this workload |
| **Claude** | Higher accuracy ceiling; slightly higher cost |
| **LM Studio** | Fully offline — requires a running LM Studio instance on the same LAN |

The active provider is stored in the DB settings and can be swapped from the UI at runtime.

### Data Model (summary)

| Table | Purpose |
|---|---|
| `persons` | Family members — every account and transaction is scoped to one |
| `entities` | Canonical names for banks, merchants, card issuers, people |
| `entity_patterns` | Raw strings that map to an entity (many-to-one) |
| `accounts` | Bank accounts and cards, each owned by a person with a fixed currency |
| `categories` | Expense/income categories (12 system defaults + user-created) |
| `category_rules` | Two-tier rules: `(entity, memo_pattern)` → category |
| `transactions` | Individual line items; currency is always explicit |
| `transaction_documents` | Many-to-many audit trail between transactions and source docs |
| `emails` | Processing log for every received email |
| `documents` | Extracted text + AI output + reconciliation result per attachment |
| `unresolved_entity_names` | Queue of raw names that need user resolution |
| `users` | Login accounts with `admin` / `member` roles |

Full schema → [`docs/architecture.md`](docs/architecture.md)

---

## UI Pages

| Route | Page |
|---|---|
| `/` | Dashboard — account balances, monthly charts (CRC and USD separate) |
| `/transacciones` | Transaction list with filters |
| `/cuentas` | Account management |
| `/bandeja` | Inbox — unresolved entities, uncategorized transactions, failed docs |
| `/entidades` | Entity management (banks, merchants, aliases) |
| `/categorias` | Category and rule management |
| `/configuracion` | Settings — IMAP config, AI provider selector, user management |

---

## LAN DNS Setup (optional but recommended)

Add to your router/DNS server so any device on the LAN reaches the app at `http://finanzas.internal`:

```
finanzas.internal  →  <IP of the host running Docker Compose>
```

If you skip this, the app is still reachable at `http://<host-ip>` on port 80.

---

## What's Implemented (Phases 1–5)

- [x] Docker Compose stack (db, backend, frontend)
- [x] Full PostgreSQL schema with Alembic migrations (0001–0003)
- [x] Admin bootstrap + 12 seeded system categories
- [x] JWT auth with forced password change on first login
- [x] All 3 AI providers (Gemini, Claude, LM Studio)
- [x] Full email pipeline (IMAP → PDF extraction → AI parse → reconcile → entity resolve → transaction create)
- [x] Two-tier category rule engine
- [x] Transaction deduplication via content-derived `dedup_key`
- [x] Reconciliation against bank totals with quality scoring
- [x] All REST API endpoints (accounts, transactions, entities, categories, rules, emails, users, settings)
- [x] Monthly summary endpoint (`GET /api/transactions/summary/monthly`)
- [x] React frontend — all pages listed above fully functional
- [x] Light-background UI with amber/brown/cream palette; sidebar stays dark

## What's Next (Phases 6–7)

- [ ] Reports page (category breakdowns, account balance history, spending trends)
- [ ] Inbox: inline scope-picker for categorizing transactions and resolving entities
- [ ] Settings page: live IMAP/AI provider test buttons, polling interval control
- [ ] Email/document processing log with reconciliation status badges
- [ ] Mobile responsiveness polish

See [`docs/phases.md`](docs/phases.md) for the full build order and status.

---

## Development

See [`docs/development.md`](docs/development.md) for:
- Running backend and frontend locally (outside Docker)
- Running tests
- Using the `parse_pdf` CLI to iterate the AI prompt
- Adding a new bank / AI provider
- Alembic migration workflow
