import os
import httpx
import streamlit as st


def _base() -> str:
    try:
        return st.secrets.get("API_BASE_URL", os.getenv("API_BASE_URL", "http://localhost:8000"))
    except Exception:
        return os.getenv("API_BASE_URL", "http://localhost:8000")


def ws_base() -> str:
    return _base().replace("https://", "wss://").replace("http://", "ws://")


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Auth ──────────────────────────────────────────────────────────────────────

def login(name: str, password: str | None = None) -> dict:
    payload: dict = {"name": name}
    if password:
        payload["password"] = password
    r = httpx.post(f"{_base()}/login", json=payload, timeout=10)
    return r.json()


# ── Votes / Orders ────────────────────────────────────────────────────────────

def get_votes(token: str) -> dict:
    r = httpx.get(f"{_base()}/votes", headers=_auth(token), timeout=10)
    r.raise_for_status()
    return r.json()


def get_my_vote(token: str) -> dict | None:
    r = httpx.get(f"{_base()}/vote/me", headers=_auth(token), timeout=10)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


def place_vote(token: str, product_id: str, qty: int) -> tuple[int, dict]:
    r = httpx.post(f"{_base()}/vote", json={"product_id": product_id, "qty": qty},
                   headers=_auth(token), timeout=10)
    return r.status_code, r.json()


def get_orders_breakdown(token: str) -> dict:
    r = httpx.get(f"{_base()}/orders/breakdown", headers=_auth(token), timeout=10)
    r.raise_for_status()
    return r.json()


def get_office_products(token: str) -> list[dict]:
    r = httpx.get(f"{_base()}/products", headers=_auth(token), timeout=10)
    if r.status_code != 200:
        return []
    return r.json().get("products", [])


# ── Stats ─────────────────────────────────────────────────────────────────────

def get_stats_daily(token: str, start: str, end: str) -> tuple[int, dict]:
    r = httpx.get(f"{_base()}/stats/daily", params={"start": start, "end": end},
                  headers=_auth(token), timeout=10)
    return r.status_code, r.json()


def get_stats_users_day(token: str, day: str) -> tuple[int, dict]:
    r = httpx.get(f"{_base()}/stats/users/day", params={"date": day},
                  headers=_auth(token), timeout=10)
    return r.status_code, r.json()


def get_stat_user_names(token: str) -> tuple[int, dict]:
    r = httpx.get(f"{_base()}/stats/user-names", headers=_auth(token), timeout=10)
    return r.status_code, r.json()


def get_stats_user_range(token: str, name: str, start: str, end: str) -> tuple[int, dict]:
    r = httpx.get(f"{_base()}/stats/user", params={"name": name, "start": start, "end": end},
                  headers=_auth(token), timeout=10)
    return r.status_code, r.json()


# ── Admin ─────────────────────────────────────────────────────────────────────

def admin_reset(password: str, office_id: str | None = None) -> tuple[int, dict]:
    payload: dict = {"password": password}
    if office_id:
        payload["office_id"] = office_id
    r = httpx.post(f"{_base()}/reset", json=payload, timeout=10)
    return r.status_code, r.json()


def admin_get_allowed_names(password: str, office_id: str | None = None) -> tuple[int, dict]:
    params: dict = {"password": password}
    if office_id:
        params["office_id"] = office_id
    r = httpx.get(f"{_base()}/allowed-names", params=params, timeout=10)
    return r.status_code, r.json()


def admin_add_name(name: str, password: str, office_id: str | None = None) -> tuple[int, dict]:
    payload: dict = {"name": name, "password": password}
    if office_id:
        payload["office_id"] = office_id
    r = httpx.post(f"{_base()}/allowed-names", json=payload, timeout=10)
    return r.status_code, r.json()


def admin_remove_name(name: str, password: str) -> tuple[int, dict]:
    r = httpx.request("DELETE", f"{_base()}/allowed-names",
                      json={"name": name, "password": password}, timeout=10)
    return r.status_code, r.json()


def admin_remove_order(name: str, password: str) -> tuple[int, dict]:
    r = httpx.post(f"{_base()}/remove-order", json={"name": name, "password": password}, timeout=10)
    return r.status_code, r.json()


def admin_set_disabled(name: str, password: str, disabled: bool) -> tuple[int, dict]:
    r = httpx.post(f"{_base()}/set-user-disabled",
                   json={"name": name, "password": password, "disabled": disabled}, timeout=10)
    return r.status_code, r.json()


def admin_unbind(name: str, password: str) -> tuple[int, dict]:
    r = httpx.post(f"{_base()}/unbind", json={"name": name, "password": password}, timeout=10)
    return r.status_code, r.json()


def admin_remove_all_logins(password: str, office_id: str | None = None) -> tuple[int, dict]:
    payload: dict = {"password": password}
    if office_id:
        payload["office_id"] = office_id
    r = httpx.post(f"{_base()}/remove-all-logins", json=payload, timeout=10)
    return r.status_code, r.json()


def admin_pending_password(password: str, office_id: str | None = None) -> tuple[int, dict]:
    params: dict = {"password": password}
    if office_id:
        params["office_id"] = office_id
    r = httpx.get(f"{_base()}/users/pending-password", params=params, timeout=10)
    return r.status_code, r.json()


def admin_rename_user(old_name: str, new_name: str, password: str) -> tuple[int, dict]:
    r = httpx.put(f"{_base()}/users/rename",
                  json={"old_name": old_name, "new_name": new_name, "password": password}, timeout=10)
    return r.status_code, r.json()


def admin_place_order(name: str, password: str, product_id: str, qty: int) -> tuple[int, dict]:
    r = httpx.post(f"{_base()}/place-order",
                   json={"name": name, "password": password, "product_id": product_id, "qty": qty}, timeout=10)
    return r.status_code, r.json()


def admin_set_nickname(name: str, nickname: str | None, password: str) -> tuple[int, dict]:
    r = httpx.put(f"{_base()}/users/nickname",
                  json={"name": name, "nickname": nickname, "password": password}, timeout=10)
    return r.status_code, r.json()


def admin_set_role(name: str, role: str, password: str) -> tuple[int, dict]:
    r = httpx.post(f"{_base()}/users/role",
                   json={"name": name, "role": role, "password": password}, timeout=10)
    return r.status_code, r.json()


def admin_list_users(password: str, office_id: str | None = None) -> tuple[int, dict]:
    params: dict = {"password": password}
    if office_id:
        params["office_id"] = office_id
    r = httpx.get(f"{_base()}/users", params=params, timeout=10)
    return r.status_code, r.json()


def admin_list_offices(password: str) -> tuple[int, dict]:
    r = httpx.get(f"{_base()}/offices", params={"password": password}, timeout=10)
    return r.status_code, r.json()


def admin_create_office(name: str, slug: str, password: str) -> tuple[int, dict]:
    r = httpx.post(f"{_base()}/offices", json={"name": name, "slug": slug, "password": password}, timeout=10)
    return r.status_code, r.json()


def admin_update_office(office_id: str, name: str, password: str) -> tuple[int, dict]:
    r = httpx.put(f"{_base()}/offices", json={"office_id": office_id, "name": name, "password": password}, timeout=10)
    return r.status_code, r.json()


def admin_set_office_active(office_id: str, is_active: bool, password: str) -> tuple[int, dict]:
    r = httpx.post(f"{_base()}/offices/active",
                   json={"office_id": office_id, "is_active": is_active, "password": password}, timeout=10)
    return r.status_code, r.json()


def admin_get_stats_daily(password: str, start: str, end: str, office_id: str | None = None) -> tuple[int, dict]:
    params: dict = {"password": password, "start": start, "end": end}
    if office_id:
        params["office_id"] = office_id
    r = httpx.get(f"{_base()}/admin/stats/daily", params=params, timeout=10)
    return r.status_code, r.json()


def admin_get_stats_users_day(password: str, date: str, office_id: str | None = None) -> tuple[int, dict]:
    params: dict = {"password": password, "date": date}
    if office_id:
        params["office_id"] = office_id
    r = httpx.get(f"{_base()}/admin/stats/users/day", params=params, timeout=10)
    return r.status_code, r.json()


def admin_get_user_names(password: str, office_id: str | None = None) -> tuple[int, dict]:
    params: dict = {"password": password}
    if office_id:
        params["office_id"] = office_id
    r = httpx.get(f"{_base()}/admin/stats/user-names", params=params, timeout=10)
    return r.status_code, r.json()


def admin_get_user_stats(password: str, name: str, start: str, end: str, office_id: str | None = None) -> tuple[int, dict]:
    params: dict = {"password": password, "name": name, "start": start, "end": end}
    if office_id:
        params["office_id"] = office_id
    r = httpx.get(f"{_base()}/admin/stats/user", params=params, timeout=10)
    return r.status_code, r.json()


# ── Products ──────────────────────────────────────────────────────────────────

def products_list(token: str) -> tuple[int, dict]:
    r = httpx.get(f"{_base()}/products", headers=_auth(token), timeout=10)
    return r.status_code, r.json()


def products_add(token: str, office_id: str, name: str, emoji: str, max_qty: int, password: str) -> tuple[int, dict]:
    r = httpx.post(f"{_base()}/products",
                   json={"office_id": office_id, "name": name, "emoji": emoji, "max_qty": max_qty, "password": password},
                   headers=_auth(token), timeout=10)
    return r.status_code, r.json()


def products_update(token: str, product_id: str, name: str, emoji: str, max_qty: int, password: str) -> tuple[int, dict]:
    r = httpx.put(f"{_base()}/products",
                  json={"product_id": product_id, "name": name, "emoji": emoji, "max_qty": max_qty, "password": password},
                  headers=_auth(token), timeout=10)
    return r.status_code, r.json()


def products_set_active(token: str, product_id: str, is_active: bool, password: str) -> tuple[int, dict]:
    r = httpx.post(f"{_base()}/products/active",
                   json={"product_id": product_id, "is_active": is_active, "password": password},
                   headers=_auth(token), timeout=10)
    return r.status_code, r.json()


# ── Office Admin ──────────────────────────────────────────────────────────────

def oa_get_orders(token: str) -> tuple[int, dict]:
    r = httpx.get(f"{_base()}/office-admin/orders", headers=_auth(token), timeout=10)
    return r.status_code, r.json()


def oa_reset_orders(token: str) -> tuple[int, dict]:
    r = httpx.post(f"{_base()}/office-admin/orders/reset", headers=_auth(token), timeout=10)
    return r.status_code, r.json()


def oa_remove_order(token: str, name: str) -> tuple[int, dict]:
    r = httpx.post(f"{_base()}/office-admin/orders/remove",
                   json={"name": name, "password": ""}, headers=_auth(token), timeout=10)
    return r.status_code, r.json()


def oa_place_order(token: str, name: str, product_id: str, qty: int) -> tuple[int, dict]:
    r = httpx.post(f"{_base()}/office-admin/orders/place",
                   json={"name": name, "password": "", "product_id": product_id, "qty": qty},
                   headers=_auth(token), timeout=10)
    return r.status_code, r.json()


def oa_list_users(token: str) -> tuple[int, dict]:
    r = httpx.get(f"{_base()}/office-admin/users", headers=_auth(token), timeout=10)
    return r.status_code, r.json()


def oa_set_role(token: str, name: str, role: str) -> tuple[int, dict]:
    r = httpx.post(f"{_base()}/office-admin/users/role",
                   json={"name": name, "role": role, "password": ""}, headers=_auth(token), timeout=10)
    return r.status_code, r.json()


def oa_set_disabled(token: str, name: str, disabled: bool) -> tuple[int, dict]:
    r = httpx.post(f"{_base()}/office-admin/users/disable",
                   json={"name": name, "password": "", "disabled": disabled}, headers=_auth(token), timeout=10)
    return r.status_code, r.json()


def oa_logout_all(token: str) -> tuple[int, dict]:
    r = httpx.post(f"{_base()}/office-admin/users/logout-all", headers=_auth(token), timeout=10)
    return r.status_code, r.json()


def oa_pending_password(token: str) -> tuple[int, dict]:
    r = httpx.get(f"{_base()}/office-admin/users/pending-password", headers=_auth(token), timeout=10)
    return r.status_code, r.json()


def oa_get_allowed_names(token: str) -> tuple[int, dict]:
    r = httpx.get(f"{_base()}/office-admin/allowed-names", headers=_auth(token), timeout=10)
    return r.status_code, r.json()


def oa_add_name(token: str, name: str) -> tuple[int, dict]:
    r = httpx.post(f"{_base()}/office-admin/allowed-names",
                   json={"name": name, "password": ""}, headers=_auth(token), timeout=10)
    return r.status_code, r.json()


def oa_remove_name(token: str, name: str) -> tuple[int, dict]:
    r = httpx.request("DELETE", f"{_base()}/office-admin/allowed-names",
                      json={"name": name, "password": ""}, headers=_auth(token), timeout=10)
    return r.status_code, r.json()


def oa_stats_daily(token: str, start: str, end: str) -> tuple[int, dict]:
    r = httpx.get(f"{_base()}/office-admin/stats/daily", params={"start": start, "end": end},
                  headers=_auth(token), timeout=10)
    return r.status_code, r.json()


def oa_stats_users_day(token: str, date: str) -> tuple[int, dict]:
    r = httpx.get(f"{_base()}/office-admin/stats/users/day", params={"date": date},
                  headers=_auth(token), timeout=10)
    return r.status_code, r.json()


def oa_user_names(token: str) -> tuple[int, dict]:
    r = httpx.get(f"{_base()}/office-admin/stats/user-names", headers=_auth(token), timeout=10)
    return r.status_code, r.json()


def oa_user_stats(token: str, name: str, start: str, end: str) -> tuple[int, dict]:
    r = httpx.get(f"{_base()}/office-admin/stats/user",
                  params={"name": name, "start": start, "end": end},
                  headers=_auth(token), timeout=10)
    return r.status_code, r.json()


# ── HR ────────────────────────────────────────────────────────────────────────

def hr_get_orders(token: str) -> tuple[int, dict]:
    r = httpx.get(f"{_base()}/hr/orders", headers=_auth(token), timeout=10)
    return r.status_code, r.json()


def hr_remove_order(token: str, name: str) -> tuple[int, dict]:
    r = httpx.post(f"{_base()}/hr/remove-order",
                   json={"name": name, "password": ""}, headers=_auth(token), timeout=10)
    return r.status_code, r.json()


def hr_place_order(token: str, name: str, product_id: str, qty: int) -> tuple[int, dict]:
    r = httpx.post(f"{_base()}/hr/place-order",
                   json={"name": name, "password": "", "product_id": product_id, "qty": qty},
                   headers=_auth(token), timeout=10)
    return r.status_code, r.json()


def hr_stats_daily(token: str, start: str, end: str) -> tuple[int, dict]:
    r = httpx.get(f"{_base()}/hr/stats/daily", params={"start": start, "end": end},
                  headers=_auth(token), timeout=10)
    return r.status_code, r.json()


def hr_stats_users_day(token: str, date: str) -> tuple[int, dict]:
    r = httpx.get(f"{_base()}/hr/stats/users/day", params={"date": date},
                  headers=_auth(token), timeout=10)
    return r.status_code, r.json()


def hr_user_names(token: str) -> tuple[int, dict]:
    r = httpx.get(f"{_base()}/hr/stats/user-names", headers=_auth(token), timeout=10)
    return r.status_code, r.json()


def hr_user_stats(token: str, name: str, start: str, end: str) -> tuple[int, dict]:
    r = httpx.get(f"{_base()}/hr/stats/user",
                  params={"name": name, "start": start, "end": end},
                  headers=_auth(token), timeout=10)
    return r.status_code, r.json()


# ── Distributor ───────────────────────────────────────────────────────────────

def dist_get_orders(token: str) -> tuple[int, dict]:
    r = httpx.get(f"{_base()}/distributor/orders", headers=_auth(token), timeout=10)
    return r.status_code, r.json()


def dist_list_companies(token: str) -> tuple[int, dict]:
    r = httpx.get(f"{_base()}/distributor/companies", headers=_auth(token), timeout=10)
    return r.status_code, r.json()


def dist_create_company(token: str, name: str, office_id: str, password: str) -> tuple[int, dict]:
    r = httpx.post(f"{_base()}/distributor/companies",
                   json={"name": name, "office_id": office_id, "password": password},
                   headers=_auth(token), timeout=10)
    return r.status_code, r.json()


def dist_set_company_active(token: str, company_id: str, is_active: bool) -> tuple[int, dict]:
    r = httpx.post(f"{_base()}/distributor/companies/active",
                   params={"company_id": company_id, "is_active": str(is_active).lower()},
                   headers=_auth(token), timeout=10)
    return r.status_code, r.json()


def dist_list_staff(token: str, company_id: str) -> tuple[int, dict]:
    r = httpx.get(f"{_base()}/distributor/companies/{company_id}/staff",
                  headers=_auth(token), timeout=10)
    return r.status_code, r.json()


def dist_add_staff(token: str, company_id: str, name: str, role: str, position: str, password: str) -> tuple[int, dict]:
    r = httpx.post(f"{_base()}/distributor/staff",
                   json={"company_id": company_id, "name": name, "role": role,
                         "position": position, "password": password},
                   headers=_auth(token), timeout=10)
    return r.status_code, r.json()


def dist_remove_staff(token: str, user_id: int, password: str) -> tuple[int, dict]:
    r = httpx.request("DELETE", f"{_base()}/distributor/staff",
                      json={"user_id": user_id, "password": password},
                      headers=_auth(token), timeout=10)
    return r.status_code, r.json()


def dist_list_positions(token: str, company_id: str) -> tuple[int, dict]:
    r = httpx.get(f"{_base()}/distributor/companies/{company_id}/positions",
                  headers=_auth(token), timeout=10)
    return r.status_code, r.json()


def dist_add_position(token: str, company_id: str, name: str, level: int, password: str) -> tuple[int, dict]:
    r = httpx.post(f"{_base()}/distributor/positions",
                   json={"company_id": company_id, "name": name, "level": level, "password": password},
                   headers=_auth(token), timeout=10)
    return r.status_code, r.json()


def dist_remove_position(token: str, position_id: str, password: str) -> tuple[int, dict]:
    r = httpx.request("DELETE", f"{_base()}/distributor/positions",
                      json={"position_id": position_id, "password": password},
                      headers=_auth(token), timeout=10)
    return r.status_code, r.json()
