# Tea or Coffee

Multi-office beverage ordering system with real-time updates, role-based access, and a distributor hierarchy.

---

## Architecture

| Layer | Tech |
|---|---|
| Backend API | FastAPI + Motor (async MongoDB) |
| Frontend | Plain HTML / CSS / JS (served by FastAPI) |
| Database | MongoDB |
| Real-time | WebSocket (per-office broadcast) |
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

## Roles

| Role | Who | Access |
|---|---|---|
| `main_admin` | Global superuser (default: "Vaibhav") | Everything — all offices, all users, all products |
| `office_admin` | Per-office admin | Manage one office: orders, users, names, products, stats |
| `office_hr` | Per-office HR | View/manage orders and stats for their office |
| `user` | Regular staff | Place one order per day |
| `company_admin` | Distributor company admin | Manage their company's staff and positions; view orders |
| `distributor_staff` | Delivery staff | View today's orders for the office they serve |

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

On first startup, the backend seeds the database:
- Creates the **Implevision** office
- Seeds default products: Tea 🍵 (max 2) and Coffee ☕ (max 1)
- Seeds the allowed names list
- Migrates any old `{tea, coffee}` vote documents to the new flat schema

On first visit to the app, a **setup screen** appears. Enter the name of a user already in the allowed list and choose a password — this creates the `main_admin` account. After setup, the normal login page is shown. Roles for all other users (office_admin, office_hr, etc.) are assigned via the Admin panel.
