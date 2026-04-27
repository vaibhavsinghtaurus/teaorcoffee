import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
from streamlit_utils.api import (
    admin_add_name,
    admin_get_allowed_names,
    admin_pending_password,
    admin_place_order,
    admin_remove_all_logins,
    admin_remove_name,
    admin_remove_order,
    admin_rename_user,
    admin_reset,
    admin_set_disabled,
    admin_set_nickname,
    admin_unbind,
    get_orders_breakdown,
    get_votes,
)
from streamlit_utils.styles import get_css

st.set_page_config(
    page_title="Admin — Tea or Coffee",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="collapsed",
)

if "theme" not in st.session_state:
    st.session_state.theme = "dark"

st.markdown(get_css(st.session_state.theme), unsafe_allow_html=True)

# ── Top bar ───────────────────────────────────────────────────────────────────
bar_l, bar_mid, bar_r = st.columns([4, 1, 1])
with bar_l:
    st.markdown("<h2 style='margin:0'>🔐 Admin Panel</h2>", unsafe_allow_html=True)
with bar_mid:
    is_dark = st.toggle("🌙", value=st.session_state.theme == "dark", key="theme_toggle_admin")
    if (is_dark and st.session_state.theme != "dark") or (not is_dark and st.session_state.theme != "light"):
        st.session_state.theme = "dark" if is_dark else "light"
        st.rerun()
with bar_r:
    if st.button("← Back to Order", use_container_width=True):
        st.switch_page("pages/1_Order.py")

st.markdown("<div style='margin:8px 0'></div>", unsafe_allow_html=True)

# ── Admin password gate ───────────────────────────────────────────────────────
with st.container(border=True):
    st.markdown(
        "<h3 style='color:white;margin:0 0 8px'>Admin Password</h3>",
        unsafe_allow_html=True,
    )
    admin_pw = st.text_input(
        "Password",
        type="password",
        placeholder="Enter admin password…",
        label_visibility="collapsed",
        key="admin_pw",
    )

if not admin_pw:
    st.info("Enter the admin password above to unlock the panel.")
    st.stop()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_orders, tab_users, tab_names = st.tabs(["📋 Orders", "👥 Users", "📝 Allowed Names"])


# ═══════════════════════ ORDERS TAB ══════════════════════════════════════════
with tab_orders:
    st.markdown("#### Today's Orders")

    col_refresh, col_reset = st.columns([3, 1])
    with col_refresh:
        if st.button("🔄 Refresh", key="refresh_orders"):
            st.rerun()
    with col_reset:
        if st.button("🗑️ Reset ALL Orders", type="primary", key="reset_all"):
            status, resp = admin_reset(admin_pw)
            if status == 200:
                st.success("All orders reset.")
                st.rerun()
            else:
                st.error(resp.get("detail", "Wrong password or error."))

    try:
        votes = get_votes(st.session_state.get("token", ""))
        breakdown = get_orders_breakdown(st.session_state.get("token", ""))

        m1, m2 = st.columns(2)
        m1.metric("🍵 Total Tea", votes.get("tea", 0))
        m2.metric("☕ Total Coffee", votes.get("coffee", 0))

        if breakdown["orders"]:
            st.markdown("---")
            for order in breakdown["orders"]:
                bev = f"🍵 Tea ×{order['tea']}" if order["tea"] > 0 else f"☕ Coffee ×{order['coffee']}"
                c1, c2, c3 = st.columns([3, 3, 2])
                c1.write(f"**{order['name']}**")
                c2.write(bev)
                with c3:
                    if st.button("Remove", key=f"rm_{order['name']}"):
                        s, r = admin_remove_order(order["name"], admin_pw)
                        if s == 200:
                            st.success(f"Removed {order['name']}'s order.")
                            st.rerun()
                        else:
                            st.error(r.get("message", "Error"))
        else:
            st.info("No orders today.")
    except Exception as exc:
        st.warning(f"Could not load orders (need a valid user token): {exc}")
        st.caption("Tip: sign in as a user first so a token is in session state.")

    st.markdown("---")

    # ── Place order on behalf of a user ───────────────────────────────────
    with st.container(border=True):
        st.markdown(
            "<h4 style='color:white;margin:0 0 10px'>Place Order for User</h4>",
            unsafe_allow_html=True,
        )
        po_col1, po_col2 = st.columns(2)
        with po_col1:
            po_name = st.text_input(
                "User name", key="po_name",
                placeholder="User name…", label_visibility="collapsed",
            )
        with po_col2:
            po_bev = st.selectbox(
                "Beverage", ["🍵 Tea (max 2)", "☕ Coffee (max 1)"],
                key="po_bev", label_visibility="collapsed",
            )

        po_qty = st.number_input(
            "Quantity", min_value=1,
            max_value=2 if "Tea" in po_bev else 1,
            value=1, step=1, key="po_qty",
        )

        if st.button("PLACE ORDER", key="po_btn", use_container_width=True, type="primary"):
            if not po_name.strip():
                st.error("Enter a user name.")
            else:
                tea = po_qty if "Tea" in po_bev else 0
                coffee = po_qty if "Coffee" in po_bev else 0
                s, r = admin_place_order(po_name.strip(), admin_pw, tea, coffee)
                if s == 200 and r.get("success"):
                    st.success(r["message"])
                    st.rerun()
                elif s == 409:
                    st.warning(r.get("detail", "User already ordered today."))
                else:
                    st.error(r.get("detail", r.get("message", "Error.")))


# ═══════════════════════ USERS TAB ═══════════════════════════════════════════
with tab_users:
    col_u1, col_u2 = st.columns(2, gap="large")

    # ── Disable / Enable user ──────────────────────────────────────────────
    with col_u1:
        with st.container(border=True):
            st.markdown("<h4 style='color:white;margin:0 0 8px'>Disable / Enable User</h4>", unsafe_allow_html=True)
            dis_name = st.text_input("User name", key="dis_name", label_visibility="collapsed",
                                     placeholder="User name…")
            dis_action = st.selectbox("Action", ["Disable", "Enable"], key="dis_action",
                                      label_visibility="collapsed")
            if st.button("Apply", key="dis_btn", use_container_width=True):
                if dis_name.strip():
                    s, r = admin_set_disabled(dis_name.strip(), admin_pw, dis_action == "Disable")
                    if s == 200 and r.get("success"):
                        st.success(r["message"])
                    else:
                        st.error(r.get("message", "Error"))

    # ── Unbind session ─────────────────────────────────────────────────────
    with col_u2:
        with st.container(border=True):
            st.markdown("<h4 style='color:white;margin:0 0 8px'>Unbind Session (Force Re-login)</h4>",
                        unsafe_allow_html=True)
            ub_name = st.text_input("User name", key="ub_name", label_visibility="collapsed",
                                    placeholder="User name…")
            if st.button("Unbind", key="ub_btn", use_container_width=True):
                if ub_name.strip():
                    s, r = admin_unbind(ub_name.strip(), admin_pw)
                    if s == 200 and r.get("success"):
                        st.success(r["message"])
                    else:
                        st.error(r.get("message", "Error"))

    st.markdown("---")
    col_u3, col_u4 = st.columns(2, gap="large")

    # ── Rename user ────────────────────────────────────────────────────────
    with col_u3:
        with st.container(border=True):
            st.markdown("<h4 style='color:white;margin:0 0 8px'>Rename User</h4>", unsafe_allow_html=True)
            old_name = st.text_input("Current name", key="old_name", label_visibility="collapsed",
                                     placeholder="Current name…")
            new_name = st.text_input("New name", key="new_name", label_visibility="collapsed",
                                     placeholder="New name…")
            if st.button("Rename", key="rename_btn", use_container_width=True):
                if old_name.strip() and new_name.strip():
                    s, r = admin_rename_user(old_name.strip(), new_name.strip(), admin_pw)
                    if s == 200 and r.get("success"):
                        st.success(f"Renamed {r['old_name']} → {r['new_name']}")
                    else:
                        st.error(r.get("message", "Error"))

    # ── Remove all logins ──────────────────────────────────────────────────
    with col_u4:
        with st.container(border=True):
            st.markdown("<h4 style='color:white;margin:0 0 8px'>Remove All Sessions</h4>",
                        unsafe_allow_html=True)
            st.caption("Forces everyone to log in again.")
            if st.button("⚠️ Remove All Logins", key="rm_all_logins", use_container_width=True, type="primary"):
                s, r = admin_remove_all_logins(admin_pw)
                if s == 200:
                    st.success(r.get("message", "Done."))
                    st.session_state.clear()
                else:
                    st.error(r.get("detail", "Error"))

    st.markdown("---")
    col_u5, _ = st.columns(2, gap="large")

    # ── Set / clear nickname ───────────────────────────────────────────────
    with col_u5:
        with st.container(border=True):
            st.markdown("<h4 style='color:white;margin:0 0 8px'>Set Nickname</h4>", unsafe_allow_html=True)
            st.caption("Leave nickname blank to clear it.")
            nick_name = st.text_input("User name", key="nick_username", label_visibility="collapsed",
                                      placeholder="User name…")
            nick_value = st.text_input("Nickname (optional)", key="nick_value", label_visibility="collapsed",
                                       placeholder="Nickname… (blank to clear)")
            if st.button("Save Nickname", key="nick_btn", use_container_width=True):
                if nick_name.strip():
                    nickname_to_set = nick_value.strip() if nick_value.strip() else None
                    s, r = admin_set_nickname(nick_name.strip(), nickname_to_set, admin_pw)
                    if s == 200 and r.get("success"):
                        st.success(r["message"])
                    elif s == 409:
                        st.warning(r.get("detail", "Nickname already taken."))
                    else:
                        st.error(r.get("detail", r.get("message", "Error")))
                else:
                    st.error("Enter a user name.")

    st.markdown("---")

    # ── Pending password users ─────────────────────────────────────────────
    st.markdown("#### Users Without Password Set")
    if st.button("🔍 Fetch", key="fetch_pending"):
        s, r = admin_pending_password(admin_pw)
        if s == 200:
            users = r.get("users", [])
            if users:
                for u in users:
                    st.write(f"• {u}")
            else:
                st.success("All users have passwords set.")
        else:
            st.error(r.get("detail", "Error"))


# ═══════════════════════ NAMES TAB ═══════════════════════════════════════════
with tab_names:
    st.markdown("#### Allowed Names")

    if st.button("🔄 Load Names", key="load_names"):
        s, r = admin_get_allowed_names(admin_pw)
        if s == 200:
            st.session_state["_names_list"] = r.get("names", [])
        else:
            st.error(r.get("detail", "Wrong password."))

    names_list: list = st.session_state.get("_names_list", [])
    if names_list:
        for n in names_list:
            nc1, nc2 = st.columns([5, 1])
            nc1.write(f"• {n}")
            with nc2:
                if st.button("Remove", key=f"rn_{n}"):
                    s, r = admin_remove_name(n, admin_pw)
                    if s == 200:
                        st.success(r.get("message", "Removed."))
                        st.session_state.pop("_names_list", None)
                        st.rerun()
                    else:
                        st.error(r.get("message", "Error"))

    st.markdown("---")
    st.markdown("#### Add New Name")
    with st.container(border=True):
        st.markdown("<h4 style='color:white;margin:0 0 8px'>Add Allowed Name</h4>", unsafe_allow_html=True)
        new_allowed = st.text_input("Name", key="new_allowed", label_visibility="collapsed",
                                    placeholder="Full name…")
        if st.button("Add Name", key="add_name_btn", use_container_width=True):
            if new_allowed.strip():
                s, r = admin_add_name(new_allowed.strip(), admin_pw)
                if s == 200 and r.get("success"):
                    st.success(r["message"])
                    st.session_state.pop("_names_list", None)
                    st.rerun()
                elif s == 409:
                    st.warning(r.get("message", "Already exists."))
                else:
                    st.error(r.get("message", "Error"))
