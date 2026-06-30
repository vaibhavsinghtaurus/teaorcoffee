# Tea or Coffee — Major Refactor Plan

> Reference this file any time. It is also saved in Claude's memory.

---

## What We're Building

| Feature | Status |
|---|---|
| Multiple offices (default: "Implevision") | ✅ Done |
| Per-office users, allowed names, products | ✅ Done |
| Dynamic products (Tea & Coffee as defaults) | ✅ Done |
| Roles in DB (not hardcoded) | ✅ Done |
| Sub-admins & HRs per office | ✅ Done |
| Distributor companies with hierarchical staff | ✅ Done |
| Distributor page (view orders + manage staff) | ✅ Done |
| Page-refresh session persistence fix | ✅ Done |
| Full UI redesign | ✅ Done |

---

## New Roles

| Role | Access |
|---|---|
| `main_admin` | Everything — global; defaults to "Vaibhav" (env: `TOC_MAIN_ADMIN_NAME`) |
| `office_admin` | Manage one office (users, products, orders, allowed names) |
| `office_hr` | View/manage orders + stats for their office |
| `user` | Order page only |
| `company_admin` | Manage their distributor company's staff + see orders |
| `distributor_staff` | See orders for served office only |

---

## New DB Collections

### `offices`
```
{ _id: ObjectId, name, slug, is_active, created_at }
```

### `products`
```
{ _id: ObjectId, office_id, name, emoji, max_qty, is_active, sort_order, created_at }
```

### `distributor_companies`
```
{ _id: ObjectId, name, office_id, is_active, created_at }
```

### `positions` (per company — configurable)
```
{ _id: ObjectId, company_id, name, level, is_active }
```

### `users` — NEW fields added
```
office_id: str | null        ← which office (for office users)
company_id: str | null       ← which company (for distributor users)
role: str                    ← main_admin / office_admin / office_hr / user / company_admin / distributor_staff
position: str | null         ← e.g. "Manager" (for distributor staff)
```

### `votes` — NEW schema (flat)
```
{ _id: ObjectId, user_id, office_id, date, product_id, product_name, product_emoji, qty }
```
Old `{tea, coffee}` records are migrated automatically on startup.

### `allowed_names` — NEW field added
```
office_id: str    ← which office this name belongs to
```

---

## File Change List

### Backend (src/teaorcoffee/)
```
core/config.py          MODIFY  — remove hardcoded names, add MAIN_ADMIN_NAME env var
core/database.py        REWRITE — offices, products, distributor, new vote schema
core/init_db.py         REWRITE — seed implevision + products + migrate old votes + set roles
core/auth.py            MODIFY  — AuthUser gets role, office_id, office_name, company_id, position
core/state.py           MODIFY  — store ws→office_id map for per-office broadcast
models/schema.py        REWRITE — all new models
routes/auth.py          MODIFY  — return role + office info on login
routes/votes.py         MODIFY  — dynamic single-product ordering
routes/admin.py         MODIFY  — multi-office, product mgmt
routes/hr.py            MODIFY  — office-scoped
routes/stats.py         MODIFY  — office-scoped, dynamic products
routes/office_admin.py  CREATE  — office-level admin endpoints
routes/distributor.py   CREATE  — distributor CRUD + order view
routes/products.py      CREATE  — product CRUD (admin/HR only)
routes/offices.py       CREATE  — office CRUD (main admin only)
utils/broadcast.py      MODIFY  — per-office broadcast
main.py                 MODIFY  — register new routers
```

### Frontend
```
streamlit_utils/session.py    CREATE  — require_auth() with localStorage bridge (session fix)
streamlit_utils/api.py        REWRITE — all new endpoints
streamlit_utils/styles.py     MODIFY  — role colors, better layout
app.py                        MODIFY  — store role/office in localStorage
pages/1_Order.py              MODIFY  — dynamic products + session fix
pages/2_Admin.py              MODIFY  — main admin: offices, global users, all products
pages/3_HR.py                 MODIFY  — office-scoped HR panel
pages/4_Stats.py              MODIFY  — dynamic product stats, office-scoped
pages/5_Office_Admin.py       CREATE  — office admin panel
pages/6_Distributor.py        CREATE  — distributor panel + staff/position mgmt
```

---

## Session Persistence Fix

**Problem:** `st.session_state` resets on browser refresh (F5). Current code only has the localStorage bridge on `app.py`, so refreshing any other page loses the session.

**Fix:** `streamlit_utils/session.py` — `require_auth(allowed_roles=None)` function:
1. If `st.session_state.token` exists → return session data, done
2. If `?ls_token` query param exists → restore session from it, `st.query_params.clear()`, return session data
3. Otherwise → inject JS that reads localStorage and redirects to **current page** with `?ls_token=...&ls_user=...&ls_role=...&ls_office_id=...&ls_office_name=...&ls_company_id=...` — then `st.stop()`

localStorage keys saved at login:
- `toc_token`, `toc_username`, `toc_role`, `toc_office_id`, `toc_office_name`, `toc_company_id`, `toc_position`

---

## Vote Migration (on startup in init_db.py)

For every old vote with `{tea, coffee}` fields and no `product_id`:
- tea > 0 → product = Tea product doc for implevision
- coffee > 0 → product = Coffee product doc for implevision
- Write `product_id`, `product_name`, `product_emoji`, `qty`, `office_id` to the document

---

## Broadcast Payload (new format)

```json
{
  "totals": {
    "Tea":    { "total": 5, "emoji": "🍵" },
    "Coffee": { "total": 3, "emoji": "☕" }
  },
  "orders": [
    { "name": "Vaibhav", "product_name": "Tea", "product_emoji": "🍵", "qty": 2 }
  ],
  "order_count": 8
}
```

---

## Page Routing by Role

| Role | Auto-redirect to |
|---|---|
| `main_admin` | `pages/2_Admin.py` |
| `office_admin` | `pages/5_Office_Admin.py` |
| `office_hr` | `pages/3_HR.py` |
| `user` | `pages/1_Order.py` |
| `company_admin` / `distributor_staff` | `pages/6_Distributor.py` |

---

## Default Seeding (Implevision office)

**Allowed names (existing):**
Vaibhav, Sourabh, Nitin, Hemang, Om, Bhavya Shah, Bhavya Prajapati, Meet, Gopal,
Sashikant, Ranjeet, Gaurav, Jimish, Devesh, Pratik, Abhi, Abhishek

**Auto-assigned roles on init:**
- Vaibhav → `main_admin`
- Ranjeet, Jimish → `office_hr`
- Everyone else → `user`

**Products seeded for Implevision:**
- Tea 🍵 (max 2, sort_order 0)
- Coffee ☕ (max 1, sort_order 1)

---

## Environment Variables

```env
TOC_MONGODB_URI=        # required
TOC_ADMIN_PASS=         # main admin password (still used for extra security)
TOC_HR_PASS=            # DEPRECATED — roles now from DB
TOC_MAIN_ADMIN_NAME=    # optional, defaults to "Vaibhav"
```
