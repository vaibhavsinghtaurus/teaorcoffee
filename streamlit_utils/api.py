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


def place_vote(token: str, tea: int, coffee: int) -> tuple[int, dict]:
    r = httpx.post(
        f"{_base()}/vote",
        json={"tea": tea, "coffee": coffee},
        headers=_auth(token),
        timeout=10,
    )
    return r.status_code, r.json()


def get_orders_breakdown(token: str) -> dict:
    r = httpx.get(f"{_base()}/orders/breakdown", headers=_auth(token), timeout=10)
    r.raise_for_status()
    return r.json()


# ── Admin ─────────────────────────────────────────────────────────────────────

def admin_reset(password: str) -> tuple[int, dict]:
    r = httpx.post(f"{_base()}/reset", json={"password": password}, timeout=10)
    return r.status_code, r.json()


def admin_get_allowed_names(password: str) -> tuple[int, dict]:
    r = httpx.get(f"{_base()}/allowed-names", params={"password": password}, timeout=10)
    return r.status_code, r.json()


def admin_add_name(name: str, password: str) -> tuple[int, dict]:
    r = httpx.post(f"{_base()}/allowed-names", json={"name": name, "password": password}, timeout=10)
    return r.status_code, r.json()


def admin_remove_name(name: str, password: str) -> tuple[int, dict]:
    r = httpx.request(
        "DELETE", f"{_base()}/allowed-names",
        json={"name": name, "password": password}, timeout=10,
    )
    return r.status_code, r.json()


def admin_remove_order(name: str, password: str) -> tuple[int, dict]:
    r = httpx.post(f"{_base()}/remove-order", json={"name": name, "password": password}, timeout=10)
    return r.status_code, r.json()


def admin_set_disabled(name: str, password: str, disabled: bool) -> tuple[int, dict]:
    r = httpx.post(
        f"{_base()}/set-user-disabled",
        json={"name": name, "password": password, "disabled": disabled},
        timeout=10,
    )
    return r.status_code, r.json()


def admin_unbind(name: str, password: str) -> tuple[int, dict]:
    r = httpx.post(f"{_base()}/unbind", json={"name": name, "password": password}, timeout=10)
    return r.status_code, r.json()


def admin_remove_all_logins(password: str) -> tuple[int, dict]:
    r = httpx.post(f"{_base()}/remove-all-logins", json={"password": password}, timeout=10)
    return r.status_code, r.json()


def admin_pending_password(password: str) -> tuple[int, dict]:
    r = httpx.get(f"{_base()}/users/pending-password", params={"password": password}, timeout=10)
    return r.status_code, r.json()


def admin_rename_user(old_name: str, new_name: str, password: str) -> tuple[int, dict]:
    r = httpx.put(
        f"{_base()}/users/rename",
        json={"old_name": old_name, "new_name": new_name, "password": password},
        timeout=10,
    )
    return r.status_code, r.json()


def admin_place_order(name: str, password: str, tea: int, coffee: int) -> tuple[int, dict]:
    r = httpx.post(
        f"{_base()}/place-order",
        json={"name": name, "password": password, "tea": tea, "coffee": coffee},
        timeout=10,
    )
    return r.status_code, r.json()
