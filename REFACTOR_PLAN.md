# Unified Companies + Distributor Marketplace Refactor

## Context

The current schema has two parallel, awkwardly-related concepts: `offices`
(e.g. Implevision) and `distributor_companies` (e.g. Zaff), where a
distributor "belongs to" and only serves one office. Roles (`main_admin`,
`office_admin`, `office_hr`, `user`, `company_admin`, `distributor_staff`),
products, and allowed-names are all hardcoded-ish per office. Admin approval
is required to add a new office (`office_requests`).

The user wants a single unified model: **companies**, each operating in
either `company` mode (Implevision — employees/managers/HRs) or
`distributor` mode (Zaff — manager/HR/distributor boys who supply products
with prices to buyer companies). Registration should be fully self-serve
(no approval step), roles should be DB-driven with no hardcoded names,
pricing must be versioned (never deleted, only superseded), orders must be
editable/schedulable, and only a super admin sees cross-company stats —
each company only sees its own.

Per user decision: **preserve existing data** via in-place migration (not a
clean reset), and **manager has the same permissions as company_admin**
except two super-admin-only actions (deactivating a company, changing its
mode).

---

## New Data Model

### `companies` (replaces `offices` + `distributor_companies`)
```
{ _id, name, slug, mode: "company" | "distributor",
  distributor_id: ObjectId|null,   # only for mode="company" — which distributor they buy from
  is_active: bool,                 # false = "inoperative" (soft delete, blocks login for all members)
  created_at }
```

### `users` (renamed field, renamed roles)
```
{ _id, name, nickname, company_id,     # was office_id — same value/meaning, just renamed
  role: "super_admin" | "company_admin" | "manager" | "hr" | "employee" | "distributor_boy",
  is_active, is_disabled, session_token, token_expires_at, password_hash, last_login_at }
```
`office_admin`→`company_admin`, `office_hr`→`hr`, `user`→`employee`,
`distributor_staff`→`distributor_boy`, `main_admin`→`super_admin`.
`company_admin` (old distributor-side role) stays `company_admin`.

### `distributor_products` (replaces per-office `products`; owned by a distributor company)
```
{ _id, company_id (must be mode=distributor), name, emoji,
  current_price: float, max_qty: int, is_active, sort_order, created_at }
```

### `product_price_history` (NEW — append-only, never deleted)
```
{ _id, distributor_product_id, price, changed_by_user_id, effective_at }
```

### `company_products` (NEW — buyer company's enabled subset of a distributor's catalog)
```
{ _id, company_id (mode=company buyer), distributor_product_id,
  is_enabled: bool, max_qty_override: int|null, added_at }
```
This is what answers "let each office choose what products their employees
can order." The order page only shows rows here with `is_enabled=true`.

### `votes` (orders — extended, same collection)
```
{ _id, user_id, company_id, date,              # date can be today OR future (scheduling)
  distributor_product_id, product_name, product_emoji, qty,
  price_at_order: float,
  status: "pending" | "delivered",              # NEW — distributor marks delivered
  delivered_at: ISO|null, delivered_by_user_id: int|null,
  created_at, updated_at }
```
**Ordering constraint changes**: it's no longer "one order per user per
day, full stop" — it's "one **pending** order per user per day." Once a
distributor marks an order delivered, that employee is free to place a new
order the same day (e.g. wants a second tea later). This replaces the old
full unique index `(user_id, date)` with a **partial unique index**:
`{user_id:1, date:1}` unique, `partialFilterExpression: {status: "pending"}`.
Scheduling a future order is still just inserting with a future `date` and
`status="pending"`.

### Retired
- `offices`, `distributor_companies`, `positions`, `allowed_names`,
  `office_requests` — no longer read/written by new code. Left in place,
  untouched, as historical residue (not dropped, per "preserve data").

---

## Role Matrix

| Role | Scope | Permissions |
|---|---|---|
| `super_admin` | global | everything; only role that can deactivate a company or change its mode; only role that sees cross-company/global stats |
| `company_admin` | own company | manage manager/hr/employee (or distributor_boy) accounts, pick distributor (mode=company only), enable/disable products, edit local max_qty, view company stats/orders |
| `manager` | own company | identical to `company_admin` except cannot deactivate own company or change its mode |
| `hr` | own company | place/edit/remove today's (and scheduled) orders for employees, view company stats — same as today's office_hr |
| `employee` | own company | place/edit/cancel own orders only, from the company's enabled product list |
| `distributor_boy` | own (distributor) company | read-only: view the distributor's aggregated order dashboard |

---

## Migration Strategy (in `core/init_db.py`)

Key trick: **reuse existing ObjectIds** so all foreign keys keep working
without a remapping table.

1. For each doc in `offices`: insert into `companies` with the **same `_id`**, `mode="company"`, `is_active` preserved.
2. For each doc in `distributor_companies`: insert into `companies` with the **same `_id`**, `mode="distributor"`. If none exist, create a fresh "Zaff" company (mode=distributor).
3. Link buyer→distributor: for each migrated office/company, if an old `distributor_companies` doc had `office_id == that company`, set `distributor_id` to that distributor's (same, preserved) id. If a company has no distributor yet, default it to Zaff.
4. For each doc in old `products` (per-office): insert into `distributor_products` with the **same `_id`**, `company_id = <that office's distributor id>`, `current_price = 10` (no price existed before → default ₹10), copy `max_qty`/`emoji`/`name`. Insert one `product_price_history` row (price=10, effective_at=now) since product IDs are preserved, existing `votes.product_id` (now `distributor_product_id`) keeps resolving correctly with zero rewrite.
5. Create a `company_products` row per migrated product, `company_id=<original office>`, `is_enabled=true` (everything that was available stays available).
6. `users`: rename `office_id`→`company_id` (copy, then this becomes the field going forward), rename role strings per the mapping above.
7. `votes`: rename `office_id`→`company_id`, rename `product_id`→`distributor_product_id` (field rename only, value unchanged since IDs were preserved), backfill `price_at_order=10` for legacy rows missing it.
8. Ensure Implevision seed identities: `Vaibhav`→`super_admin`, `Jimish`→`manager`, `Ranjeet`→`hr`, remaining default names → `employee` (only applied if those users exist and don't already have a more specific role set — idempotent, DB-driven, no env vars).
9. Ensure Zaff has Tea 🍵 / Coffee ☕ at ₹10 each (`distributor_products` + one `product_price_history` row each) if they don't already exist for it.
10. New indexes: `companies.slug` unique, `distributor_products (company_id, name)` unique, `company_products (company_id, distributor_product_id)` unique, `product_price_history.distributor_product_id`, `users.name` unique, and replace `votes (user_id, date)` unique with the **partial** unique index described above (`status="pending"` only). Backfill `status="delivered"` on all pre-existing vote rows (they predate the delivery workflow, treat as already fulfilled) so the new partial index doesn't collide with old data.

This runs idempotently on every startup (matches the existing pattern in
`init_db.py` — checks `$exists`/absence before writing).

---

## Backend Changes

### `core/database.py` — rewrite
- Replace `offices`/`products`/`distributor_companies`/`positions` property accessors with `companies`, `distributor_products`, `product_price_history`, `company_products`.
- New methods: `create_company(name, slug, mode, distributor_id=None)`, `get_companies(mode=None, active_only=False)`, `set_company_active`, `set_company_distributor`, `set_company_mode` (super_admin only, guarded in route not DB layer).
- Product/pricing: `add_distributor_product`, `update_distributor_product_price` (inserts history row + updates `current_price`, never deletes), `get_price_history(product_id)`, `get_distributor_products(company_id)`.
- Company-product enablement: `enable_company_product`, `disable_company_product`, `set_company_product_max_qty`, `get_company_products(company_id)` (joined view with distributor product info).
- Votes: generalize `insert_vote`/`get_user_today_vote`/`has_user_voted_today`/`delete_user_today_vote` to take an explicit `date` param (default today) **and to only consider `status="pending"`** so scheduling and re-ordering-after-delivery reuse the same paths; add `update_vote(user_id, date, distributor_product_id, qty)` for edits (pending-only); add `get_user_orders(user_id, from_date)` for "my upcoming/today orders" list.
- Delivery workflow: `mark_order_delivered(vote_id, delivered_by_user_id)` (sets `status="delivered"`, `delivered_at`, `delivered_by_user_id`); `get_pending_orders_for_distributor(distributor_company_id, company_id=None)` — pending orders across (or filtered to one of) the distributor's buyer companies, grouped by company, each row showing employee name/product/qty for the "go into each office and mark delivered" workflow.
- **Stats vs fulfillment — status matters everywhere now**: all "consumption" stats (`get_today_totals`, `get_daily_totals_range`, `get_today_breakdown`, `get_user_orders_for_date`, `get_user_stats_range` — used by every company's own stats page and the super-admin global stats) now filter to **`status="delivered"` only**. A pending (not-yet-delivered) order isn't "consumption" yet, so it shouldn't count in a company's or the global stats totals.
- Distributor dashboard aggregation: `get_distributor_order_summary(distributor_company_id, date)` — per product, returns **both** `delivered_total` and `pending_total` (qty and order-count), plus the same delivered/pending split per buyer company and per user — this is the "tell them how many delivered vs not-delivered but ordered" view, distinct from the plain consumption stats above.
- Users: `add_company_member(name, company_id, role)` (single method replacing `seed_users`/`add_distributor_staff` duplication — used both by self-serve registration and by company_admin/manager one-click add).

### `core/auth.py`
- `AuthUser`/`_resolve_token` field rename `office_id`→`company_id`; `require_role` unchanged. Add a small helper `require_company_admin_or_manager(user)` used across company-scoped routes.
- Login-time check: block login if the user's company `is_active == False` ("Your company has been deactivated").

### `models/schema.py` — rewrite
- Rename models: `OfficeOut`→`CompanyOut` (adds `mode`, `distributor_id`), drop `PositionOut`/`AddPositionRequest`/position models, drop office-request models.
- New: `RegisterCompanyRequest` (name, slug, mode, distributor_id [required if mode=company], admin_name, admin_password, manager_names[], hr_names[], employee_or_staff_names[], enabled_product_ids[] [if mode=company]) / `RegisterCompanyResponse`.
- New: `DistributorProductOut` (id, name, emoji, current_price, max_qty, is_active), `AddDistributorProductRequest`, `UpdateProductPriceRequest` (product_id, new_price), `PriceHistoryEntry`.
- New: `CompanyProductOut` (distributor_product_id, name, emoji, price, max_qty, is_enabled), `EnableCompanyProductRequest`, `DisableCompanyProductRequest`.
- `VoteRequest` gains optional `date: str|None`. New `EditVoteRequest` (date, product_id, qty). New `MyOrdersResponse` (list of upcoming/today orders, each with an edit/cancel affordance).
- `UserOut`/`AuthUser`/`LoginResponse` field rename `office_id`→`company_id`, role literal updated.

### `routes/auth.py`
- `/setup` stays as a safety net (creates a `super_admin` if none exists — no longer requires the name to pre-exist in an "allowed list", since that concept is retired: it directly creates the user).
- Replace `/request-office` + admin-approval flow with **`POST /register-company`** (public, no auth): validates mode, creates the company row, creates the `company_admin` user (name+password supplied inline, no separate login step), creates manager/hr/employee (or distributor_boy) users via `add_company_member`, and — if mode=company — enables the chosen distributor products via `company_products`. Fully self-serve, no approval, effective immediately.
- `GET /companies/active` (rename of `/offices/active`) — for the login dropdown; only `mode=company` + `is_active=true` shown (distributor staff still log in via existing name/password, no dropdown entry needed, same as today's "Distributor Access" bypass).
- `GET /distributors/active` (NEW, public) — list active `mode=distributor` companies, used by the registration page's "pick your distributor" dropdown.
- Login: company_id checks generalized from office_id; add the inactive-company block described above.

### `routes/company_admin.py` (renamed from `office_admin.py`, prefix `/company-admin`)
- Same shape as today's `office_admin.py` but scoped by `company_id` instead of `office_id`, roles allowed = `company_admin`, `manager`, `super_admin`.
- Add distributor/product-catalog endpoints here (or a new `routes/company_products.py`): `GET /company-admin/catalog` (distributor's full catalog + enabled flag), `POST /company-admin/catalog/enable`, `POST /company-admin/catalog/disable`, `POST /company-admin/catalog/max-qty`.
- Add `POST /company-admin/staff` (replaces one-off allowed-name add) — add a manager/hr/employee directly with a role, one click, mirrors `add_company_member`.

### `routes/hr.py`
- Rename role checks `office_hr`→`hr` etc.; add edit-order endpoint (`PUT /hr/orders/edit`) mirroring the new self-service edit, since HR/manager also correct mistaken orders.

### `routes/distributor.py` — rewrite
- Drop `positions` endpoints entirely (positions collection retired).
- `GET /distributor/products` (own catalog with current price), `POST /distributor/products` (add new — becomes visible to every buyer company via `company_products` opt-in), `PUT /distributor/products/{id}/price` (append history + bump current price), `GET /distributor/products/{id}/price-history`, **`POST /distributor/products/{id}/active`** (deactivate/reactivate — the "remove a product" action; soft-delete only, price history and any past orders referencing it are untouched, and it drops off buyer companies' enable lists).
- `GET /distributor/orders/summary?date=` → per product **and** per buyer company **and** per user, each showing **delivered vs pending** counts/qty — built on `db.get_distributor_order_summary`.
- **`GET /distributor/orders/pending?company_id=`** → the fulfillment queue: pending orders grouped by buyer company (or filtered to one company/office when `company_id` is passed) — this is the "go into each office" view.
- **`POST /distributor/orders/{vote_id}/deliver`** → marks that order delivered (`db.mark_order_delivered`); once delivered, the employee's `has_user_voted_today` check for that date no longer blocks them, so they can place a new order the same day.
- `POST /distributor/staff` (manager/hr/distributor_boy — no more free-text "position", just role).

### `routes/votes.py`
- `POST /vote` gains optional `date` (defaults today; must be >= today) — this is "schedule an order." Product must be in `company_products` (enabled) for the user's company, not a raw per-office product lookup. Blocked only by an existing **pending** order for that date (delivered orders don't block a new one).
- New `PUT /vote` — edit an existing **pending** order (today's or a future scheduled one) owned by the caller: change product/qty. Disallow editing past dates or already-delivered orders.
- New `DELETE /vote?date=` — self-service cancel of a pending order (today's or scheduled).
- New `GET /orders/mine` — list caller's own orders with `date >= today` **and their status**, for an "upcoming orders" panel with edit/cancel buttons (delivered ones shown read-only).
- `GET /vote/me` now means "my current pending order for today" (if any) — the basis for whether the order form or the "already ordered, awaiting delivery" state is shown.

### `routes/products.py`
- Repurposed as the read-only "what can I order" endpoint for employees: `GET /products` now returns the calling user's company's **enabled** `company_products` (joined with distributor product info: name/emoji/current price/effective max_qty). Distributor-catalog CRUD moves to `routes/distributor.py` as above.

### `routes/admin.py` (super_admin only)
- Rename `/offices*` → `/companies*`: list all, create (manual override still useful even though self-serve exists), update, `set_company_active` (the "delete but don't delete" soft-delete — mark inoperative), and a new `set_company_mode`/`set_company_distributor` for edge-case fixups.
- Drop the office-requests tab/endpoints entirely (no approval flow anymore).
- Global stats endpoints unchanged in shape, just renamed fields (and now delivered-only, per the DB-layer change above); these remain the **only** place cross-company (`company_id=None`) stats are allowed — every other router requires a `company_id` scope tied to the caller.

### `main.py`
- Router registration list updates only (renamed modules); no structural change.

---

## Frontend Changes

- `templates/index.html`: rename office dropdown → company dropdown (`/companies/active`); replace the "Request addition of a new office" collapsible with a link to a new **`/register`** page.
- `templates/register.html` (NEW) + `routes/pages.py` `/register` route: mode toggle (Company vs Distributor), if Company mode show a distributor `<select>` (from `/distributors/active`) plus a checklist of that distributor's products to enable, name/role rows for manager(s)/hr(s)/employees (or distributor boys if distributor mode), admin name+password. Submits to `POST /register-company`, immediate success (no "pending approval" messaging).
- `templates/order.html`: replace the locked "ordered today" card with an editable one — show current **pending** order with **Edit**/**Cancel** buttons that re-open the form pre-filled (calls `PUT`/`DELETE /vote`); once a distributor marks it delivered, the order form reopens automatically (poll/refresh `GET /vote/me`, or push it over the existing `/ws/votes` broadcast) so the employee can place another order same day; add a date picker defaulting to today (schedule up to N days ahead) and an "Upcoming Orders" list below fed by `GET /orders/mine` (delivered entries shown read-only with a "✅ Delivered" tag); show price per product fetched from the (now richer) `/products` response.
- `templates/office_admin.html` → rename to `templates/company_admin.html`, served at `/company-admin`: relabel Office→Company throughout, add a "Product Catalog" tab (enable/disable distributor products, set local max-qty override), add "Add Staff" with a role dropdown (manager/hr/employee) replacing the old allowed-names flow.
- `templates/distributor.html`: replace the positions/staff-hierarchy UI with role-based staff add (manager/hr/distributor_boy); add a "Products & Pricing" tab (add product, edit price — shows current price + a price-history table, editing never deletes rows — plus a deactivate/remove toggle per product); rework the orders tab into the three summary views requested (total-by-product, by-company, by-user), **each split into delivered vs pending/not-yet-delivered counts** so the distributor can see at a glance how much has gone out vs is still owed, **plus a separate "Deliveries" tab**: pick a buyer company/office (or "all"), see its pending orders, click "✅ Mark Delivered" per order — this is the "go into each office" fulfillment workflow that frees the employee to reorder.
- `templates/admin.html`: rename Offices tab → Companies tab (mode column, distributor column, activate/deactivate = "mark inoperative"); remove the Office Requests tab; global stats tab explicitly labeled as super-admin-only (already gated server-side).
- `static/app.js`: `Auth.setSession`/`getUser` field rename `office_id`/`office_name`→`company_id`/`company_name`; no structural change otherwise (helpers like `initTabs`, `statsDateRange`, `buildChart` are reused as-is for all new tabs/pages).

---

## Verification

1. `poetry run pytest` (or existing test runner) — check `tests/` for anything touching offices/products/votes and update alongside.
2. Start the app locally (`uvicorn` per `main.py`) against a copy of the real Mongo URI (or a local Mongo) and confirm on startup logs that migration ran without exceptions and counts look sane (log counts of migrated offices/distributors/products).
3. Manual walkthrough in browser:
   - Login as `Vaibhav` → lands on super_admin admin panel; confirm Companies tab shows Implevision (mode=company, distributor=Zaff) and Zaff (mode=distributor); confirm global stats tab works.
   - Login as `Jimish` (manager) and `Ranjeet` (hr) → confirm both reach the company admin panel with equal capability (per the manager=company_admin decision) except no deactivate-company control.
   - Register a brand-new company end-to-end via `/register` (both modes) with no approval step, then log in as its admin immediately.
   - As an employee: place today's order, edit it, schedule one for tomorrow, edit/cancel the scheduled one.
   - As Zaff's manager: add a new product with a price, change an existing price, confirm price history retains the old row; confirm Implevision's company_admin sees the new product in their enable/disable catalog; deactivate/remove a product and confirm it disappears from buyer catalogs but past orders referencing it are untouched.
   - Enable/disable a product for Implevision and confirm it appears/disappears from the employee order page.
   - As super_admin, mark a company inoperative and confirm its members can no longer log in, while its historical order data is untouched.
   - Confirm distributor dashboard shows totals-by-product, by-company, and by-user correctly for a day with orders from Implevision.
   - Delivery flow: as an employee, place an order; confirm a second order is blocked while it's pending, and that it does **not** show up yet in Implevision's own stats page (delivered-only). As Zaff's manager/distributor_boy, open the Deliveries tab, find Implevision's pending order, mark it delivered — confirm it now appears in Implevision's stats, and that Zaff's order-summary tabs correctly show it moving from the pending bucket to the delivered bucket (by product, by company, by user). Confirm the employee's order page now shows the completed order (read-only) and lets them place a brand-new order the same day.
