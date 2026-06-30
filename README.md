# Tea or Coffee

Multi-office beverage ordering system with real-time updates, role-based access, and a distributor hierarchy.

---

## Architecture

| Layer | Tech |
|---|---|
| Backend API | FastAPI + Motor (async MongoDB) |
| Frontend | Streamlit (multi-page) |
| Database | MongoDB |
| Real-time | WebSocket (per-office broadcast) |
| Auth | bcrypt passwords + session tokens (7-day expiry) |

The backend runs as a FastAPI server (`uvicorn`). When deployed on a single machine, `app.py` auto-starts the backend on port 8000 if it isn't already running.

---

## Environment Variables

### Backend (FastAPI)

Set these in a `.env` file at the project root, or as real environment variables. All variables are prefixed with `TOC_`.

| Variable | Required | Default | Description |
|---|---|---|---|
| `TOC_MONGODB_URI` | **Yes** | — | Full MongoDB connection string, e.g. `mongodb+srv://user:pass@cluster.mongodb.net/teaorcoffee` |
| `TOC_ADMIN_PASS` | **Yes** | — | Master admin password used for all password-gated admin API calls |
| `TOC_MAIN_ADMIN_NAME` | No | `Vaibhav` | Name of the user who is automatically assigned the `main_admin` role on startup |

Example `.env`:
```env
TOC_MONGODB_URI=mongodb+srv://user:password@cluster.mongodb.net/teaorcoffee
TOC_ADMIN_PASS=your-secure-admin-password
TOC_MAIN_ADMIN_NAME=Vaibhav
```

### Frontend (Streamlit)

Set via environment variable or Streamlit secrets (`secrets.toml`).

| Variable | Required | Default | Description |
|---|---|---|---|
| `API_BASE_URL` | No | `http://localhost:8000` | Base URL of the FastAPI backend. Set this when the frontend and backend are on different hosts (e.g. cloud deployments). |

Via environment variable:
```env
API_BASE_URL=https://your-api-domain.com
```

Via Streamlit secrets (`.streamlit/secrets.toml`):
```toml
API_BASE_URL = "https://your-api-domain.com"
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

# Start backend
uvicorn src.teaorcoffee.main:app --host 0.0.0.0 --port 8000 --reload

# Start frontend (separate terminal)
streamlit run app.py
```

## Running with Docker (backend only)

```bash
docker build -t teaorcoffee .
docker run -p 8000:8000 \
  -e TOC_MONGODB_URI="mongodb+srv://..." \
  -e TOC_ADMIN_PASS="your-password" \
  teaorcoffee
```

---

## Database Seeding

On first startup, the backend automatically:
- Creates the **Implevision** office
- Seeds default products: Tea 🍵 (max 2) and Coffee ☕ (max 1)
- Seeds the allowed names list
- Assigns `main_admin` role to the user matching `TOC_MAIN_ADMIN_NAME`
- Assigns `office_hr` role to Ranjeet and Jimish
- Migrates any old `{tea, coffee}` vote documents to the new flat schema
