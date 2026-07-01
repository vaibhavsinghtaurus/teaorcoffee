# Tea or Coffee

A multi-tenant beverage ordering system: **companies** order tea/coffee/etc.
from a **distributor**, with real-time updates, DB-driven roles, and no
hardcoded admin/HR names.

---

## Architecture

| Layer | Tech |
|---|---|
| Backend API | FastAPI + Motor (async MongoDB) |
| Frontend | Plain HTML / CSS / JS (served by FastAPI) |
| Database | MongoDB |
| Real-time | WebSocket (per-company broadcast) |
| Auth | bcrypt passwords + session tokens, stored in `localStorage` |

FastAPI serves both the API and the static frontend from the same process. No separate frontend server is needed.

---

## Environment Variables

Set these in a `.env` file at the project root, or as real environment variables.

| Variable | Required | Default | Description |
|---|---|---|---|
| `TOC_MONGODB_URI` | **Yes** | — | Full MongoDB connection string |

Example `.env`:
```env
TOC_MONGODB_URI=mongodb+srv://user:password@cluster.mongodb.net/teaorcoffee
```

---

## Companies & Modes

Every tenant is a **company**, operating in one of two modes:

- **`company` mode** — orders products (e.g. Implevision). Has `employee`,
  `hr`, `manager`, and `company_admin` members (multiple of each allowed),
  and buys from exactly one `distributor`.
- **`distributor` mode** — supplies products with prices to buyer companies
  (e.g. Zaff). Has `manager`, `hr`, `distributor_boy`, and `company_admin`
  members. Adds/prices its own product catalog; buyer companies choose which
  of those products to enable for their own employees.

Anyone can self-register a new company (either mode) from the login page —
**no approval step**. A super admin can mark any company inoperative
(soft delete — blocks login for its members, keeps all historical data).

## Roles

| Role | Scope | Access |
|---|---|---|
| `super_admin` | global | everything; only role that can deactivate a company or see cross-company stats |
| `company_admin` | own company | full control of their company (staff, distributor selection, product catalog, orders, stats) |
| `manager` | own company | same as `company_admin`, minus deactivating/reconfiguring the company itself |
| `hr` | own company | place/edit/remove today's (and scheduled) orders for employees, view stats |
| `employee` | own company | place, edit, schedule, and cancel their own orders |
| `distributor_boy` | own distributor | view the distributor's order dashboard and mark deliveries |

## Ordering

- Employees pick from their company's **enabled** products (chosen by their
  `company_admin`/`manager` from the distributor's catalog).
- Orders can be scheduled for a future date, and edited/cancelled any time
  before they're delivered.
- Only one **pending** order per person per day — once the distributor marks
  it delivered, that person is free to place a new one the same day.
- Stats pages only count **delivered** orders (pending ones aren't
  "consumption" yet). The distributor's own dashboard shows delivered vs.
  pending separately.
- Product prices are versioned — a distributor can update a price at any
  time, but past prices are kept in history and never deleted.

---

## Running Locally

```bash
# Install dependencies
poetry install

# Start the server (serves API + frontend on port 8000)
uvicorn src.teaorcoffee.main:app --host 0.0.0.0 --port 8000 --reload
```

Open `http://localhost:8000` in your browser.

## Deploying to FastAPI Cloud

```bash
# Install the FastAPI CLI (if not already installed)
pip install "fastapi[standard]"

# Deploy from the project root
fastapi deploy
```

Set `TOC_MONGODB_URI` as an environment variable in the FastAPI Cloud dashboard before deploying.

---

## Running with Docker

```bash
docker build -t teaorcoffee .
docker run -p 8000:8000 \
  -e TOC_MONGODB_URI="mongodb+srv://..." \
  teaorcoffee
```

---

## First-Time Setup

On startup, the backend seeds/migrates the database automatically and
idempotently:
- Creates **Zaff** (distributor) with Tea 🍵 and Coffee ☕ at ₹10 each
- Creates **Implevision** (company), buying from Zaff, with Tea/Coffee enabled
- Seeds identities: Vaibhav → `super_admin`, Jimish → `manager`,
  Ranjeet → `hr`, everyone else → `employee`
- Migrates any pre-existing `offices`/`distributor_companies`/`products`
  documents into the unified `companies`/`distributor_products` schema,
  preserving IDs and historical order data

A **setup screen** appears on first visit only if no super admin exists yet
(e.g. a completely empty database) — it lets you create one directly by
name and password. Otherwise, just sign in, or register a new company from
the login page.
