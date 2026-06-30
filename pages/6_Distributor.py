import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
from streamlit_utils.api import (
    dist_get_orders,
    dist_list_companies, dist_create_company, dist_set_company_active,
    dist_list_staff, dist_add_staff, dist_remove_staff,
    dist_list_positions, dist_add_position, dist_remove_position,
)
from streamlit_utils.styles import get_css
from streamlit_utils.session import require_auth, do_logout

st.set_page_config(page_title="Distributor — Tea or Coffee", page_icon="🚚",
                   layout="wide", initial_sidebar_state="collapsed")

if "theme" not in st.session_state:
    st.session_state.theme = "dark"
st.markdown(get_css(st.session_state.theme), unsafe_allow_html=True)

sess = require_auth(allowed_roles=["main_admin", "company_admin", "distributor_staff"])
token = sess["token"]
role = sess["role"]
username = sess["username"]
company_id = sess.get("company_id", "")
position = sess.get("position", "")

_is_company_admin = role in ("main_admin", "company_admin")

bar_l, bar_m, bar_r = st.columns([5, 1, 2])
with bar_l:
    role_label = "Distributor Admin" if _is_company_admin else f"Distributor — {position or 'Staff'}"
    st.markdown(
        f"<div class='topbar-title'>🚚 {role_label} <span style='opacity:0.5;font-size:13px;margin-left:8px'>{username}</span></div>",
        unsafe_allow_html=True,
    )
with bar_m:
    is_dark = st.toggle("🌙", value=st.session_state.theme == "dark", key="theme_t_dist")
    if (is_dark and st.session_state.theme != "dark") or (not is_dark and st.session_state.theme != "light"):
        st.session_state.theme = "dark" if is_dark else "light"
        st.rerun()
with bar_r:
    if st.button("Logout", use_container_width=True):
        do_logout()

st.markdown("<div style='margin:8px 0'></div>", unsafe_allow_html=True)

# Build tab list based on role
_tabs = ["📋 Today's Orders"]
if _is_company_admin:
    _tabs += ["👥 Staff", "📌 Positions", "🏢 Companies"]

tabs = st.tabs(_tabs)

# ═══ TODAY'S ORDERS ══════════════════════════════════════════════════════════
with tabs[0]:
    if st.button("🔄 Refresh", key="dist_refresh"):
        st.rerun()

    s_o, r_o = dist_get_orders(token)
    if s_o != 200:
        st.error(r_o.get("detail", "Could not load orders."))
    else:
        totals = r_o.get("totals", {})
        orders = r_o.get("orders", [])
        order_count = r_o.get("order_count", len(orders))

        if totals:
            metric_cols = st.columns(len(totals) + 1)
            for i, (pname, info) in enumerate(totals.items()):
                emoji = info.get("emoji", "") if isinstance(info, dict) else ""
                total = info.get("total", info) if isinstance(info, dict) else info
                metric_cols[i].metric(f"{emoji} {pname}", total)
            metric_cols[-1].metric("👥 Total Orders", order_count)
        else:
            st.metric("👥 Total Orders", order_count)

        if orders:
            st.markdown("---")
            rows = []
            for o in orders:
                rows.append({
                    "Name": o["name"],
                    "Order": f"{o.get('product_emoji','☕')} {o.get('product_name','')}",
                    "Qty": o.get("qty", 1),
                })
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.info("No orders today.")


# ═══ STAFF (company admin only) ═══════════════════════════════════════════════
if _is_company_admin:
    with tabs[1]:
        # Pick company
        s_c, r_c = dist_list_companies(token)
        companies = r_c.get("companies", []) if s_c == 200 else []

        if not companies:
            st.info("No companies found. Create one in the Companies tab first.")
        else:
            company_opts = {c["name"]: c["id"] for c in companies}
            sel_company_name = st.selectbox("Company", list(company_opts.keys()), key="staff_company_sel")
            sel_company_id = company_opts[sel_company_name]

            if st.button("🔄 Load Staff", key="load_staff"):
                s_s, r_s = dist_list_staff(token, sel_company_id)
                if s_s == 200:
                    st.session_state[f"_staff_{sel_company_id}"] = r_s.get("staff", [])
                else:
                    st.error(r_s.get("detail", "Error."))

            staff_list = st.session_state.get(f"_staff_{sel_company_id}", [])
            if staff_list:
                st.markdown("---")
                for m in staff_list:
                    mc1, mc2, mc3, mc4 = st.columns([3, 2, 2, 1])
                    mc1.write(f"**{m['name']}**")
                    mc2.write(m.get("position") or "—")
                    mc3.write(m.get("role", "distributor_staff"))
                    with mc4:
                        if st.button("Remove", key=f"rm_staff_{m['id']}"):
                            s, r = dist_remove_staff(token, int(m["id"]), "")
                            if s == 200:
                                st.success(f"Removed {m['name']}")
                                st.session_state.pop(f"_staff_{sel_company_id}", None)
                                st.rerun()
                            else:
                                st.error(r.get("detail", "Error"))

            st.markdown("---")
            with st.container(border=True):
                st.markdown("<h4 style='margin:0 0 8px'>Add Staff Member</h4>", unsafe_allow_html=True)

                # Load positions for this company
                s_p, r_p = dist_list_positions(token, sel_company_id)
                positions_list = r_p.get("positions", []) if s_p == 200 else []

                ac1, ac2 = st.columns(2)
                with ac1:
                    add_staff_name = st.text_input("Name", key="add_staff_name",
                                                   label_visibility="collapsed", placeholder="Full name…")
                with ac2:
                    add_staff_role = st.selectbox("Role", ["distributor_staff", "company_admin"],
                                                  key="add_staff_role", label_visibility="collapsed")

                if positions_list:
                    pos_opts = [p["name"] for p in positions_list]
                    add_staff_pos = st.selectbox("Position", pos_opts, key="add_staff_pos",
                                                 label_visibility="collapsed")
                else:
                    add_staff_pos = st.text_input("Position (no positions defined yet)", key="add_staff_pos_text",
                                                  label_visibility="collapsed",
                                                  placeholder="e.g. Manager")

                if st.button("Add Staff", key="add_staff_btn", use_container_width=True):
                    if add_staff_name.strip() and add_staff_pos:
                        s, r = dist_add_staff(token, sel_company_id, add_staff_name.strip(),
                                              add_staff_role, add_staff_pos, "")
                        if s == 200 and r.get("success"):
                            st.success(r["message"])
                            st.session_state.pop(f"_staff_{sel_company_id}", None)
                            st.rerun()
                        elif s == 409:
                            st.warning(r.get("detail", "User already exists."))
                        else:
                            st.error(r.get("detail", "Error"))

    # ═══ POSITIONS ════════════════════════════════════════════════════════════
    with tabs[2]:
        s_c2, r_c2 = dist_list_companies(token)
        companies2 = r_c2.get("companies", []) if s_c2 == 200 else []

        if not companies2:
            st.info("No companies found.")
        else:
            company_opts2 = {c["name"]: c["id"] for c in companies2}
            sel_company2_name = st.selectbox("Company", list(company_opts2.keys()), key="pos_company_sel")
            sel_company2_id = company_opts2[sel_company2_name]

            if st.button("🔄 Load Positions", key="load_positions"):
                s_pp, r_pp = dist_list_positions(token, sel_company2_id)
                if s_pp == 200:
                    st.session_state[f"_positions_{sel_company2_id}"] = r_pp.get("positions", [])
                else:
                    st.error(r_pp.get("detail", "Error."))

            pos_list = st.session_state.get(f"_positions_{sel_company2_id}", [])
            if pos_list:
                st.markdown("---")
                for p in pos_list:
                    pc1, pc2, pc3 = st.columns([3, 2, 1])
                    pc1.write(f"**{p['name']}**")
                    pc2.write(f"Level {p['level']}")
                    with pc3:
                        if st.button("Remove", key=f"rm_pos_{p['id']}"):
                            s, r = dist_remove_position(token, p["id"], "")
                            if s == 200:
                                st.success(f"Position '{p['name']}' removed")
                                st.session_state.pop(f"_positions_{sel_company2_id}", None)
                                st.rerun()
                            else:
                                st.error(r.get("detail", "Error"))

            st.markdown("---")
            with st.container(border=True):
                st.markdown("<h4 style='margin:0 0 8px'>Add Position</h4>", unsafe_allow_html=True)
                pc1, pc2 = st.columns(2)
                with pc1:
                    new_pos_name = st.text_input("Position name", key="new_pos_name",
                                                 label_visibility="collapsed", placeholder="e.g. Manager")
                with pc2:
                    new_pos_level = st.number_input("Level (1 = highest)", min_value=1, max_value=10,
                                                    value=1, key="new_pos_level")
                if st.button("Add Position", key="add_pos_btn", use_container_width=True):
                    if new_pos_name.strip():
                        s, r = dist_add_position(token, sel_company2_id, new_pos_name.strip(),
                                                 int(new_pos_level), "")
                        if s == 200 and r.get("success"):
                            st.success(r["message"])
                            st.session_state.pop(f"_positions_{sel_company2_id}", None)
                            st.rerun()
                        elif s == 409:
                            st.warning("Position already exists.")
                        else:
                            st.error(r.get("detail", "Error"))

    # ═══ COMPANIES (main admin only) ══════════════════════════════════════════
    with tabs[3]:
        if role == "main_admin":
            if st.button("🔄 Load Companies", key="dist_load_companies"):
                s, r = dist_list_companies(token)
                if s == 200:
                    st.session_state["_dist_companies"] = r.get("companies", [])
                else:
                    st.error(r.get("detail", "Error."))

            for c in st.session_state.get("_dist_companies", []):
                cc1, cc2, cc3 = st.columns([4, 2, 1])
                cc1.write(f"**{c['name']}**")
                cc2.write("🟢 Active" if c.get("is_active", True) else "🔴 Inactive")
                with cc3:
                    btn_label = "Deactivate" if c.get("is_active", True) else "Activate"
                    if st.button(btn_label, key=f"co_toggle_{c['id']}"):
                        s, r = dist_set_company_active(token, c["id"], not c.get("is_active", True))
                        if s == 200:
                            st.success(r.get("message", "Updated."))
                            st.session_state.pop("_dist_companies", None)
                            st.rerun()
                        else:
                            st.error(r.get("detail", "Error"))

            st.markdown("---")
            with st.container(border=True):
                st.markdown("<h4 style='margin:0 0 8px'>Add Distributor Company</h4>", unsafe_allow_html=True)
                from streamlit_utils.api import admin_list_offices
                s_off, r_off = admin_list_offices(st.session_state.get("_admin_pw_cache", ""))
                offices = r_off.get("offices", []) if s_off == 200 else []

                if not offices:
                    st.warning("Admin password required to list offices. Use the Main Admin panel to create companies.")
                else:
                    dist_off_opts = {o["name"]: o["id"] for o in offices}
                    dist_off_sel = st.selectbox("Serves Office", list(dist_off_opts.keys()),
                                                key="dist2_off_sel")
                    dist_off_id = dist_off_opts[dist_off_sel]
                    dist_name = st.text_input("Company name", key="dist2_name",
                                             label_visibility="collapsed", placeholder="e.g. Zaff")
                    dist_pw = st.text_input("Admin password", key="dist2_pw",
                                            type="password", label_visibility="collapsed",
                                            placeholder="Admin password…")
                    if st.button("Create Company", key="dist2_create_btn", use_container_width=True):
                        if dist_name.strip() and dist_off_id and dist_pw:
                            s, r = dist_create_company(token, dist_name.strip(), dist_off_id, dist_pw)
                            if s == 200 and r.get("success"):
                                st.success(r["message"])
                                st.session_state.pop("_dist_companies", None)
                                st.rerun()
                            elif s == 409:
                                st.warning(r.get("detail", "Already exists."))
                            else:
                                st.error(r.get("detail", "Error"))
        else:
            st.info("Only main admin can manage distributor companies.")
