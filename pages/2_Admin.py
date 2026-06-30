import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date as _date, timedelta
import pandas as pd
import streamlit as st
from streamlit_utils.api import (
    admin_list_offices, admin_create_office, admin_update_office, admin_set_office_active,
    admin_list_users, admin_set_role,
    admin_add_name, admin_get_allowed_names, admin_remove_name,
    admin_remove_order, admin_reset, admin_set_disabled, admin_unbind,
    admin_pending_password, admin_rename_user, admin_set_nickname,
    admin_remove_all_logins, admin_place_order, admin_get_stats_daily,
    products_list, products_add, products_update, products_set_active,
    dist_list_companies, dist_create_company,
    get_orders_breakdown, get_office_products,
)
from streamlit_utils.styles import get_css
from streamlit_utils.session import require_auth, do_logout

st.set_page_config(page_title="Admin — Tea or Coffee", page_icon="⚙️",
                   layout="wide", initial_sidebar_state="collapsed")

if "theme" not in st.session_state:
    st.session_state.theme = "dark"
st.markdown(get_css(st.session_state.theme), unsafe_allow_html=True)

sess = require_auth(allowed_roles=["main_admin"])
token = sess["token"]
admin_pw = st.session_state.get("_admin_pw_cache", "")

# ── Top bar ───────────────────────────────────────────────────────────────────
bar_l, bar_m, bar_r = st.columns([5, 1, 2])
with bar_l:
    st.markdown("<div class='topbar-title'>⚙️ Main Admin Panel</div>", unsafe_allow_html=True)
with bar_m:
    is_dark = st.toggle("🌙", value=st.session_state.theme == "dark", key="theme_t")
    if (is_dark and st.session_state.theme != "dark") or (not is_dark and st.session_state.theme != "light"):
        st.session_state.theme = "dark" if is_dark else "light"
        st.rerun()
with bar_r:
    c1, c2 = st.columns(2)
    with c1:
        if st.button("← Orders", use_container_width=True):
            st.switch_page("pages/1_Order.py")
    with c2:
        if st.button("Logout", use_container_width=True):
            do_logout()

st.markdown("<div style='margin:8px 0'></div>", unsafe_allow_html=True)

# ── Admin password gate ───────────────────────────────────────────────────────
with st.container(border=True):
    st.markdown("<h4 style='margin:0 0 8px'>Admin Password</h4>", unsafe_allow_html=True)
    pw_input = st.text_input("pw", type="password", placeholder="Enter admin password…",
                              label_visibility="collapsed", key="admin_pw_input")
    if pw_input:
        st.session_state["_admin_pw_cache"] = pw_input
        admin_pw = pw_input

if not admin_pw:
    st.info("Enter the admin password above to unlock the panel.")
    st.stop()

# ── Tabs ──────────────────────────────────────────────────────────────────────
_MIN_DATE = _date(2026, 1, 1)
_today = _date.today()

tab_orders, tab_offices, tab_users, tab_names, tab_products, tab_distributors, tab_stats = st.tabs([
    "📋 Orders", "🏢 Offices", "👥 Users", "📝 Allowed Names", "🛒 Products", "🚚 Distributors", "📊 Stats"
])

# ═══ ORDERS ══════════════════════════════════════════════════════════════════
with tab_orders:
    # Office selector for cross-office view
    s_offices, r_offices = admin_list_offices(admin_pw)
    offices_list = r_offices.get("offices", []) if s_offices == 200 else []
    office_options = {o["name"]: o["id"] for o in offices_list}
    office_options_list = ["All Offices"] + list(office_options.keys())

    sel_office_name = st.selectbox("Office", office_options_list, key="orders_office_sel")
    sel_office_id = office_options.get(sel_office_name) if sel_office_name != "All Offices" else None

    col_refresh, col_reset = st.columns([3, 1])
    with col_refresh:
        if st.button("🔄 Refresh", key="refresh_orders"):
            st.rerun()
    with col_reset:
        if st.button("🗑️ Reset ALL Orders", type="primary", key="reset_all"):
            s, r = admin_reset(admin_pw, sel_office_id)
            if s == 200:
                st.success("All orders reset.")
                st.rerun()
            else:
                st.error(r.get("detail", "Error."))

    try:
        bd = get_orders_breakdown(token)
        orders = bd.get("orders", [])
        totals = bd.get("totals", {})

        if totals:
            cols = st.columns(len(totals) + 1)
            for i, (pname, info) in enumerate(totals.items()):
                emoji = info.get("emoji", "") if isinstance(info, dict) else ""
                total = info.get("total", info) if isinstance(info, dict) else info
                cols[i].metric(f"{emoji} {pname}", total)
            cols[-1].metric("👥 Orders", bd.get("order_count", len(orders)))

        if orders:
            st.markdown("---")
            for order in orders:
                bev = f"{order.get('product_emoji','☕')} {order.get('product_name','')} ×{order.get('qty',1)}"
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
        st.warning(f"Could not load orders: {exc}")

    st.markdown("---")
    with st.container(border=True):
        st.markdown("<h4 style='margin:0 0 10px'>Place Order for User</h4>", unsafe_allow_html=True)
        po_name = st.text_input("User name", key="po_name", placeholder="User name…", label_visibility="collapsed")
        # Load products
        prods = get_office_products(token)
        if prods:
            prod_labels = [f"{p['emoji']} {p['name']} (max {p['max_qty']})" for p in prods]
            po_prod_label = st.selectbox("Product", prod_labels, key="po_prod", label_visibility="collapsed")
            po_prod_idx = prod_labels.index(po_prod_label)
            po_prod = prods[po_prod_idx]
            po_qty = st.number_input("Qty", min_value=1, max_value=po_prod["max_qty"], value=1, key="po_qty")
            if st.button("PLACE ORDER", key="po_btn", use_container_width=True, type="primary"):
                if po_name.strip():
                    s, r = admin_place_order(po_name.strip(), admin_pw, po_prod["id"], po_qty)
                    if s == 200 and r.get("success"):
                        st.success(r["message"])
                        st.rerun()
                    elif s == 409:
                        st.warning(r.get("detail", "Already ordered."))
                    else:
                        st.error(r.get("detail", r.get("message", "Error.")))


# ═══ OFFICES ═════════════════════════════════════════════════════════════════
with tab_offices:
    st.markdown("#### Offices")
    if st.button("🔄 Load Offices", key="load_offices"):
        s, r = admin_list_offices(admin_pw)
        if s == 200:
            st.session_state["_offices"] = r.get("offices", [])
        else:
            st.error(r.get("detail", "Error."))

    for o in st.session_state.get("_offices", []):
        c1, c2, c3, c4 = st.columns([4, 2, 1, 1])
        c1.write(f"**{o['name']}** `{o['slug']}`")
        c2.write("🟢 Active" if o.get("is_active") else "🔴 Inactive")
        with c3:
            toggle_label = "Deactivate" if o.get("is_active") else "Activate"
            if st.button(toggle_label, key=f"off_toggle_{o['id']}"):
                s, r = admin_set_office_active(o["id"], not o.get("is_active", True), admin_pw)
                if s == 200:
                    st.success(r.get("message", "Updated."))
                    st.session_state.pop("_offices", None)
                    st.rerun()
                else:
                    st.error(r.get("detail", "Error"))
        c4.write(f"`{o['id'][:8]}…`")

    st.markdown("---")
    oc1, oc2 = st.columns(2, gap="large")

    with oc1:
        with st.container(border=True):
            st.markdown("<h4 style='margin:0 0 10px'>Create New Office</h4>", unsafe_allow_html=True)
            new_office_name = st.text_input("Office name", key="new_office_name", placeholder="e.g. Implevision", label_visibility="collapsed")
            new_office_slug = st.text_input("Slug", key="new_office_slug", placeholder="e.g. implevision (lowercase, no spaces)", label_visibility="collapsed")
            if st.button("Create Office", key="create_office_btn", use_container_width=True):
                if new_office_name.strip() and new_office_slug.strip():
                    s, r = admin_create_office(new_office_name.strip(), new_office_slug.strip(), admin_pw)
                    if s == 200 and r.get("success"):
                        st.success(r["message"])
                        st.session_state.pop("_offices", None)
                        st.rerun()
                    else:
                        st.error(r.get("detail", "Error."))

    with oc2:
        with st.container(border=True):
            st.markdown("<h4 style='margin:0 0 10px'>Rename Office</h4>", unsafe_allow_html=True)
            s_off_r, r_off_r = admin_list_offices(admin_pw)
            off_r_list = r_off_r.get("offices", []) if s_off_r == 200 else []
            off_r_opts = {o["name"]: o["id"] for o in off_r_list}
            if off_r_opts:
                rename_off_sel = st.selectbox("Select office", list(off_r_opts.keys()), key="rename_off_sel",
                                              label_visibility="collapsed")
                rename_off_id = off_r_opts[rename_off_sel]
                rename_off_new = st.text_input("New name", key="rename_off_new",
                                               label_visibility="collapsed", placeholder="New office name…")
                if st.button("Rename", key="rename_off_btn", use_container_width=True):
                    if rename_off_new.strip():
                        s, r = admin_update_office(rename_off_id, rename_off_new.strip(), admin_pw)
                        if s == 200 and r.get("success"):
                            st.success(r["message"])
                            st.session_state.pop("_offices", None)
                            st.rerun()
                        else:
                            st.error(r.get("detail", "Error"))
            else:
                st.info("No offices loaded yet.")


# ═══ USERS ═══════════════════════════════════════════════════════════════════
with tab_users:
    # Office filter
    s_off, r_off = admin_list_offices(admin_pw)
    off_list = r_off.get("offices", []) if s_off == 200 else []
    off_opts = {"All": None} | {o["name"]: o["id"] for o in off_list}
    u_sel_off = st.selectbox("Filter by office", list(off_opts.keys()), key="u_off_sel")
    u_off_id = off_opts[u_sel_off]

    if st.button("🔄 Load Users", key="load_users"):
        s, r = admin_list_users(admin_pw, u_off_id)
        if s == 200:
            st.session_state["_users_list"] = r.get("users", [])
        else:
            st.error(r.get("detail", "Error."))

    users_data = st.session_state.get("_users_list", [])
    if users_data:
        role_colors = {
            "main_admin": "#7c3aed", "office_admin": "#2563eb",
            "office_hr": "#16a34a", "user": "#475569",
            "company_admin": "#ea580c", "distributor_staff": "#d97706",
        }
        for u in users_data:
            uc1, uc2, uc3, uc4 = st.columns([3, 2, 2, 2])
            uc1.write(f"**{u['name']}**")
            role_c = role_colors.get(u.get("role", "user"), "#475569")
            uc2.markdown(f"<span style='color:{role_c};font-weight:600'>{u.get('role','user')}</span>", unsafe_allow_html=True)
            uc3.write("🔴 Disabled" if u.get("is_disabled") else "🟢 Active")
            uc4.write(u.get("office_id", "—")[:12] if u.get("office_id") else "distributor")

    st.markdown("---")
    col_u1, col_u2 = st.columns(2, gap="large")

    with col_u1:
        with st.container(border=True):
            st.markdown("<h4 style='margin:0 0 8px'>Set User Role</h4>", unsafe_allow_html=True)
            role_name = st.text_input("Name", key="role_name", label_visibility="collapsed", placeholder="User name…")
            role_sel = st.selectbox("Role", ["user", "office_hr", "office_admin", "main_admin",
                                              "company_admin", "distributor_staff"], key="role_sel",
                                    label_visibility="collapsed")
            if st.button("Set Role", key="role_btn", use_container_width=True):
                if role_name.strip():
                    s, r = admin_set_role(role_name.strip(), role_sel, admin_pw)
                    if s == 200 and r.get("success"):
                        st.success(r["message"])
                        st.session_state.pop("_users_list", None)
                    else:
                        st.error(r.get("detail", r.get("message", "Error")))

    with col_u2:
        with st.container(border=True):
            st.markdown("<h4 style='margin:0 0 8px'>Disable / Enable User</h4>", unsafe_allow_html=True)
            dis_name = st.text_input("Name", key="dis_name", label_visibility="collapsed", placeholder="User name…")
            dis_action = st.selectbox("Action", ["Disable", "Enable"], key="dis_action", label_visibility="collapsed")
            if st.button("Apply", key="dis_btn", use_container_width=True):
                if dis_name.strip():
                    s, r = admin_set_disabled(dis_name.strip(), admin_pw, dis_action == "Disable")
                    if s == 200 and r.get("success"):
                        st.success(r["message"])
                    else:
                        st.error(r.get("message", "Error"))

    st.markdown("---")
    col_u3, col_u4 = st.columns(2, gap="large")

    with col_u3:
        with st.container(border=True):
            st.markdown("<h4 style='margin:0 0 8px'>Rename User</h4>", unsafe_allow_html=True)
            old_name = st.text_input("Current name", key="old_name", label_visibility="collapsed", placeholder="Current name…")
            new_name = st.text_input("New name", key="new_name", label_visibility="collapsed", placeholder="New name…")
            if st.button("Rename", key="rename_btn", use_container_width=True):
                if old_name.strip() and new_name.strip():
                    s, r = admin_rename_user(old_name.strip(), new_name.strip(), admin_pw)
                    if s == 200 and r.get("success"):
                        st.success(f"{r['old_name']} → {r['new_name']}")
                    else:
                        st.error(r.get("message", "Error"))

    with col_u4:
        with st.container(border=True):
            st.markdown("<h4 style='margin:0 0 8px'>Unbind Session</h4>", unsafe_allow_html=True)
            ub_name = st.text_input("Name", key="ub_name", label_visibility="collapsed", placeholder="User name…")
            if st.button("Unbind", key="ub_btn", use_container_width=True):
                if ub_name.strip():
                    s, r = admin_unbind(ub_name.strip(), admin_pw)
                    if s == 200 and r.get("success"):
                        st.success(r["message"])
                    else:
                        st.error(r.get("message", "Error"))

    st.markdown("---")
    col_u5, col_u6 = st.columns(2, gap="large")

    with col_u5:
        with st.container(border=True):
            st.markdown("<h4 style='margin:0 0 8px'>Set Nickname</h4>", unsafe_allow_html=True)
            nick_user = st.text_input("Name", key="nick_user", label_visibility="collapsed", placeholder="User name…")
            nick_val = st.text_input("Nickname", key="nick_val", label_visibility="collapsed", placeholder="Nickname (blank to clear)…")
            if st.button("Save", key="nick_btn", use_container_width=True):
                if nick_user.strip():
                    s, r = admin_set_nickname(nick_user.strip(), nick_val.strip() or None, admin_pw)
                    if s == 200 and r.get("success"):
                        st.success(r["message"])
                    elif s == 409:
                        st.warning(r.get("detail", "Nickname taken."))
                    else:
                        st.error(r.get("detail", "Error"))

    with col_u6:
        with st.container(border=True):
            st.markdown("<h4 style='margin:0 0 8px'>Remove All Sessions</h4>", unsafe_allow_html=True)
            st.caption("Forces everyone to re-login.")
            if st.button("⚠️ Logout All", key="rm_all_logins", use_container_width=True, type="primary"):
                s, r = admin_remove_all_logins(admin_pw)
                if s == 200:
                    st.success(r.get("message", "Done."))
                    st.session_state.clear()
                else:
                    st.error(r.get("detail", "Error"))

    st.markdown("---")
    st.markdown("#### Users Without Password")
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


# ═══ ALLOWED NAMES ═══════════════════════════════════════════════════════════
with tab_names:
    s_off2, r_off2 = admin_list_offices(admin_pw)
    off2 = r_off2.get("offices", []) if s_off2 == 200 else []
    off2_opts = {"All": None} | {o["name"]: o["id"] for o in off2}
    n_sel_off = st.selectbox("Filter by office", list(off2_opts.keys()), key="n_off_sel")
    n_off_id = off2_opts[n_sel_off]

    if st.button("🔄 Load Names", key="load_names"):
        s, r = admin_get_allowed_names(admin_pw, n_off_id)
        if s == 200:
            st.session_state["_names_list"] = r.get("names", [])
        else:
            st.error(r.get("detail", "Error."))

    for n in st.session_state.get("_names_list", []):
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
    with st.container(border=True):
        st.markdown("<h4 style='margin:0 0 8px'>Add Allowed Name</h4>", unsafe_allow_html=True)
        s_off3, r_off3 = admin_list_offices(admin_pw)
        off3 = r_off3.get("offices", []) if s_off3 == 200 else []
        add_off_opts = {o["name"]: o["id"] for o in off3}
        add_off_sel = st.selectbox("Office", list(add_off_opts.keys()), key="add_name_off")
        add_off_id = add_off_opts.get(add_off_sel)
        new_allowed = st.text_input("Name", key="new_allowed", label_visibility="collapsed", placeholder="Full name…")
        if st.button("Add Name", key="add_name_btn", use_container_width=True):
            if new_allowed.strip() and add_off_id:
                s, r = admin_add_name(new_allowed.strip(), admin_pw, add_off_id)
                if s == 200 and r.get("success"):
                    st.success(r["message"])
                    st.session_state.pop("_names_list", None)
                elif s == 409:
                    st.warning(r.get("message", "Already exists."))
                else:
                    st.error(r.get("message", "Error"))


# ═══ PRODUCTS ════════════════════════════════════════════════════════════════
with tab_products:
    s_off4, r_off4 = admin_list_offices(admin_pw)
    off4 = r_off4.get("offices", []) if s_off4 == 200 else []
    off4_opts = {o["name"]: o["id"] for o in off4}
    p_sel_off = st.selectbox("Office", list(off4_opts.keys()), key="p_off_sel")
    p_off_id = off4_opts.get(p_sel_off)

    if st.button("🔄 Load Products", key="load_products"):
        s_pl, r_pl = products_list(token)
        st.session_state["_prods_list_admin"] = r_pl.get("products", []) if s_pl == 200 else []

    prods_admin = st.session_state.get("_prods_list_admin", [])
    if prods_admin:
        for p in prods_admin:
            pc1, pc2, pc3, pc4 = st.columns([1, 3, 2, 2])
            pc1.write(p.get("emoji", ""))
            pc2.write(f"**{p['name']}** (max {p['max_qty']})")
            pc3.write("🟢 Active" if p.get("is_active", True) else "🔴 Inactive")
            with pc4:
                if p.get("is_active", True):
                    if st.button("Deactivate", key=f"deact_{p['id']}"):
                        s, r = products_set_active(token, p["id"], False, admin_pw)
                        if s == 200:
                            st.session_state.pop("_prods_list_admin", None)
                            st.session_state.pop("products_cache", None)
                            st.rerun()
                        else:
                            st.error(r.get("detail", "Error"))
                else:
                    if st.button("Activate", key=f"act_{p['id']}"):
                        s, r = products_set_active(token, p["id"], True, admin_pw)
                        if s == 200:
                            st.session_state.pop("_prods_list_admin", None)
                            st.session_state.pop("products_cache", None)
                            st.rerun()
                        else:
                            st.error(r.get("detail", "Error"))

    st.markdown("---")
    prod_c1, prod_c2 = st.columns(2, gap="large")

    with prod_c1:
        with st.container(border=True):
            st.markdown("<h4 style='margin:0 0 8px'>Add Product</h4>", unsafe_allow_html=True)
            p_name = st.text_input("Product name", key="p_name", label_visibility="collapsed", placeholder="e.g. Juice")
            p_emoji = st.text_input("Emoji", key="p_emoji", label_visibility="collapsed", placeholder="e.g. 🧃")
            p_max_qty = st.number_input("Max quantity per order", min_value=1, max_value=10, value=1, key="p_max_qty")
            if st.button("Add Product", key="add_prod_btn", use_container_width=True):
                if p_name.strip() and p_off_id:
                    s, r = products_add(token, p_off_id, p_name.strip(), p_emoji.strip() or "🍶", p_max_qty, admin_pw)
                    if s == 200 and r.get("success"):
                        st.success(r["message"])
                        st.session_state.pop("_prods_list_admin", None)
                        st.session_state.pop("products_cache", None)
                        st.rerun()
                    else:
                        st.error(r.get("detail", "Error"))

    with prod_c2:
        with st.container(border=True):
            st.markdown("<h4 style='margin:0 0 8px'>Edit Product</h4>", unsafe_allow_html=True)
            if prods_admin:
                edit_prod_opts = {f"{p.get('emoji','')} {p['name']}": p for p in prods_admin}
                edit_prod_label = st.selectbox("Product to edit", list(edit_prod_opts.keys()),
                                               key="edit_prod_sel", label_visibility="collapsed")
                edit_prod = edit_prod_opts[edit_prod_label]
                ep_name = st.text_input("Name", key="ep_name", value=edit_prod["name"], label_visibility="collapsed")
                ep_emoji = st.text_input("Emoji", key="ep_emoji", value=edit_prod.get("emoji", ""), label_visibility="collapsed")
                ep_max_qty = st.number_input("Max qty", min_value=1, max_value=10,
                                             value=edit_prod["max_qty"], key="ep_max_qty")
                if st.button("Save Changes", key="ep_save_btn", use_container_width=True):
                    if ep_name.strip():
                        s, r = products_update(token, edit_prod["id"], ep_name.strip(),
                                               ep_emoji.strip() or "🍶", ep_max_qty, admin_pw)
                        if s == 200 and r.get("success"):
                            st.success(r["message"])
                            st.session_state.pop("_prods_list_admin", None)
                            st.session_state.pop("products_cache", None)
                            st.rerun()
                        else:
                            st.error(r.get("detail", "Error"))
            else:
                st.info("Load products first to edit them.")


# ═══ DISTRIBUTORS ════════════════════════════════════════════════════════════
with tab_distributors:
    if st.button("🔄 Load Companies", key="load_companies"):
        s, r = dist_list_companies(token)
        if s == 200:
            st.session_state["_companies"] = r.get("companies", [])
        else:
            st.error(r.get("detail", "Error."))

    for c in st.session_state.get("_companies", []):
        cc1, cc2 = st.columns([4, 2])
        cc1.write(f"**{c['name']}**")
        cc2.write(f"Office: `{c.get('office_id','')[:12]}`")

    st.markdown("---")
    with st.container(border=True):
        st.markdown("<h4 style='margin:0 0 8px'>Add Distributor Company</h4>", unsafe_allow_html=True)
        s_off5, r_off5 = admin_list_offices(admin_pw)
        off5 = r_off5.get("offices", []) if s_off5 == 200 else []
        dist_off_opts = {o["name"]: o["id"] for o in off5}
        dist_off_sel = st.selectbox("Serves Office", list(dist_off_opts.keys()), key="dist_off_sel")
        dist_off_id = dist_off_opts.get(dist_off_sel)
        dist_name = st.text_input("Company name", key="dist_name", label_visibility="collapsed", placeholder="e.g. Zaff")
        if st.button("Add Company", key="add_company_btn", use_container_width=True):
            if dist_name.strip() and dist_off_id:
                s, r = dist_create_company(token, dist_name.strip(), dist_off_id, admin_pw)
                if s == 200 and r.get("success"):
                    st.success(r["message"])
                    st.session_state.pop("_companies", None)
                    st.rerun()
                elif s == 409:
                    st.warning(r.get("detail", "Already exists."))
                else:
                    st.error(r.get("detail", "Error"))


# ═══ STATS ═══════════════════════════════════════════════════════════════════
with tab_stats:
    s_off6, r_off6 = admin_list_offices(admin_pw)
    off6 = r_off6.get("offices", []) if s_off6 == 200 else []
    off6_opts = {"All Offices": None} | {o["name"]: o["id"] for o in off6}
    stat_off_sel = st.selectbox("Office", list(off6_opts.keys()), key="stat_off_sel")
    stat_off_id = off6_opts[stat_off_sel]

    if st.button("Open Full Stats →", type="primary"):
        st.switch_page("pages/4_Stats.py")

    st.markdown("---")
    qs_c1, qs_c2, qs_c3 = st.columns(3)
    with qs_c1:
        qs_start = st.date_input("From", value=_today - timedelta(days=6), min_value=_MIN_DATE, max_value=_today, key="qs_s")
    with qs_c2:
        qs_end = st.date_input("To", value=_today, min_value=_MIN_DATE, max_value=_today, key="qs_e")
    with qs_c3:
        st.markdown("<div style='padding-top:28px'></div>", unsafe_allow_html=True)
        qs_load = st.button("Load", key="qs_load", use_container_width=True)

    if qs_load and qs_start <= qs_end:
        qs, qr = admin_get_stats_daily(admin_pw, qs_start.isoformat(), qs_end.isoformat(), stat_off_id)
        if qs == 200:
            days = qr.get("days", [])
            if days:
                df = pd.DataFrame(days).set_index("date")
                cols_to_show = [c for c in df.columns if c not in ("products",)]
                df = df[["tea", "coffee"]].rename(columns={"tea": "Tea", "coffee": "Coffee"})
                total_t, total_c = int(df["Tea"].sum()), int(df["Coffee"].sum())
                mc1, mc2 = st.columns(2)
                mc1.metric("🍵 Tea", total_t)
                mc2.metric("☕ Coffee", total_c)
                st.bar_chart(df.sort_index(), color=["#3B82F6", "#F97316"])
            else:
                st.info("No orders in this range.")
        else:
            st.error(qr.get("detail", "Error."))
