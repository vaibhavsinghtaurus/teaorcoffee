import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date as _date, timedelta
import pandas as pd
import streamlit as st
from streamlit_utils.api import (
    hr_get_orders, hr_remove_order, hr_place_order,
    hr_stats_daily, hr_stats_users_day, hr_user_names, hr_user_stats,
    get_office_products,
)
from streamlit_utils.styles import get_css
from streamlit_utils.session import require_auth, do_logout

st.set_page_config(page_title="HR Panel — Tea or Coffee", page_icon="👔",
                   layout="wide", initial_sidebar_state="collapsed")

if "theme" not in st.session_state:
    st.session_state.theme = "dark"
st.markdown(get_css(st.session_state.theme), unsafe_allow_html=True)

sess = require_auth(allowed_roles=["main_admin", "office_admin", "office_hr"])
token = sess["token"]
office_name = sess["office_name"] or "Office"

bar_l, bar_m, bar_r = st.columns([5, 1, 2])
with bar_l:
    st.markdown(f"<div class='topbar-title'>👔 HR Panel <span class='office-tag'>{office_name}</span></div>",
                unsafe_allow_html=True)
with bar_m:
    is_dark = st.toggle("🌙", value=st.session_state.theme == "dark", key="theme_t_hr")
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

_MIN_DATE = _date(2026, 1, 1)
_today = _date.today()

tab_orders, tab_stats = st.tabs(["📋 Orders", "📊 Stats"])

# ═══ ORDERS ══════════════════════════════════════════════════════════════════
with tab_orders:
    if st.button("🔄 Refresh", key="hr_refresh"):
        st.rerun()

    s_o, r_o = hr_get_orders(token)
    if s_o == 403:
        st.error("Access denied.")
        st.stop()
    elif s_o != 200:
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
            metric_cols[-1].metric("👥 Orders", order_count)

        if orders:
            st.markdown("---")
            for order in orders:
                bev = f"{order.get('product_emoji','☕')} {order.get('product_name','')} ×{order.get('qty',1)}"
                c1, c2, c3 = st.columns([3, 3, 2])
                c1.write(f"**{order['name']}**")
                c2.write(bev)
                with c3:
                    if st.button("Remove", key=f"hr_rm_{order['name']}"):
                        s, r = hr_remove_order(token, order["name"])
                        if s == 200:
                            st.success(f"Removed {order['name']}'s order.")
                            st.rerun()
                        else:
                            st.error(r.get("detail", r.get("message", "Error")))
        else:
            st.info("No orders today.")

    st.markdown("---")
    with st.container(border=True):
        st.markdown("<h4 style='margin:0 0 10px'>Place Order for User</h4>", unsafe_allow_html=True)
        po_c1, po_c2 = st.columns(2)
        with po_c1:
            po_name = st.text_input("User name", key="hr_po_name", placeholder="User name…", label_visibility="collapsed")
        prods = get_office_products(token)
        if prods:
            prod_labels = [f"{p['emoji']} {p['name']} (max {p['max_qty']})" for p in prods]
            with po_c2:
                po_prod_label = st.selectbox("Product", prod_labels, key="hr_po_prod", label_visibility="collapsed")
            po_prod_idx = prod_labels.index(po_prod_label)
            po_prod = prods[po_prod_idx]
            po_qty = st.number_input("Qty", min_value=1, max_value=po_prod["max_qty"], value=1, key="hr_po_qty")
            if st.button("PLACE ORDER", key="hr_po_btn", use_container_width=True, type="primary"):
                if po_name.strip():
                    s, r = hr_place_order(token, po_name.strip(), po_prod["id"], po_qty)
                    if s == 200 and r.get("success"):
                        st.success(r["message"])
                        st.rerun()
                    elif s == 409:
                        st.warning(r.get("detail", "Already ordered."))
                    else:
                        st.error(r.get("detail", r.get("message", "Error.")))


# ═══ STATS ═══════════════════════════════════════════════════════════════════
with tab_stats:
    preset_c1, preset_c2, preset_c3, preset_c4 = st.columns(4)
    if "hr_s_start" not in st.session_state:
        st.session_state.hr_s_start = _today - timedelta(days=6)
    if "hr_s_end" not in st.session_state:
        st.session_state.hr_s_end = _today
    with preset_c1:
        if st.button("This Week", use_container_width=True, key="hr_week"):
            st.session_state.hr_s_start = _today - timedelta(days=_today.weekday())
            st.session_state.hr_s_end = _today
            st.rerun()
    with preset_c2:
        if st.button("Last 7 Days", use_container_width=True, key="hr_last7"):
            st.session_state.hr_s_start = _today - timedelta(days=6)
            st.session_state.hr_s_end = _today
            st.rerun()
    with preset_c3:
        if st.button("This Month", use_container_width=True, key="hr_month"):
            st.session_state.hr_s_start = _today.replace(day=1)
            st.session_state.hr_s_end = _today
            st.rerun()
    with preset_c4:
        if st.button("Last Month", use_container_width=True, key="hr_lastmonth"):
            first = _today.replace(day=1)
            end = first - timedelta(days=1)
            st.session_state.hr_s_start = end.replace(day=1)
            st.session_state.hr_s_end = end
            st.rerun()

    dc1, dc2 = st.columns(2)
    with dc1:
        range_start = st.date_input("From", value=st.session_state.hr_s_start,
                                    min_value=_MIN_DATE, max_value=_today, key="hr_rng_s")
    with dc2:
        range_end = st.date_input("To", value=st.session_state.hr_s_end,
                                  min_value=_MIN_DATE, max_value=_today, key="hr_rng_e")

    if range_start > range_end:
        st.error("'From' must be on or before 'To'.")
    else:
        st.session_state.hr_s_start = range_start
        st.session_state.hr_s_end = range_end
        ds, dr = hr_stats_daily(token, range_start.isoformat(), range_end.isoformat())
        if ds != 200:
            st.error(dr.get("detail", "Failed."))
        else:
            days = dr.get("days", [])
            total_t = sum(d["tea"] for d in days)
            total_c = sum(d["coffee"] for d in days)
            sm1, sm2, sm3 = st.columns(3)
            sm1.metric("🍵 Tea", total_t)
            sm2.metric("☕ Coffee", total_c)
            sm3.metric("📅 Active Days", len(days))
            if days:
                df = pd.DataFrame(days).set_index("date")
                df = df[["tea", "coffee"]].rename(columns={"tea": "Tea", "coffee": "Coffee"})
                st.bar_chart(df.sort_index(), color=["#3B82F6", "#F97316"])

    st.markdown("---")
    st.markdown("#### Who Ordered on a Specific Day")
    bd_c1, bd_c2 = st.columns([2, 1])
    with bd_c1:
        sel_day = st.date_input("Day", value=_today, min_value=_MIN_DATE, max_value=_today, key="hr_bd_day")
    with bd_c2:
        st.markdown("<div style='padding-top:28px'></div>", unsafe_allow_html=True)
        load_day = st.button("Load Breakdown", use_container_width=True, type="primary", key="hr_load_day")
    if load_day:
        ds2, dr2 = hr_stats_users_day(token, sel_day.isoformat())
        if ds2 == 200:
            ords2 = dr2.get("orders", [])
            st.markdown(f"**{dr2['date']}** — 🍵 {dr2['total_tea']} | ☕ {dr2['total_coffee']}")
            if ords2:
                odf = pd.DataFrame(ords2)
                odf.rename(columns={"name": "Name", "product_name": "Product", "qty": "Qty"}, inplace=True)
                st.dataframe(odf[["Name", "Product", "Qty"]].sort_values("Name"),
                             use_container_width=True, hide_index=True)
        else:
            st.error(dr2.get("detail", "Failed."))

    st.markdown("---")
    st.markdown("#### User Stats")
    ns, nr = hr_user_names(token)
    if ns == 200:
        user_names = nr.get("names", [])
        if user_names:
            sel_user = st.selectbox("Select user", user_names, key="hr_user_sel")
        else:
            st.info("No users found.")
            st.stop()
    else:
        st.warning("Could not load user names.")
        st.stop()

    if "hr_u_start" not in st.session_state:
        st.session_state.hr_u_start = _today - timedelta(days=6)
    if "hr_u_end" not in st.session_state:
        st.session_state.hr_u_end = _today

    uc1, uc2 = st.columns(2)
    with uc1:
        u_start = st.date_input("From", value=st.session_state.hr_u_start,
                                min_value=_MIN_DATE, max_value=_today, key="hr_u_s")
    with uc2:
        u_end = st.date_input("To", value=st.session_state.hr_u_end,
                              min_value=_MIN_DATE, max_value=_today, key="hr_u_e")

    if u_start > u_end:
        st.error("'From' must be on or before 'To'.")
    else:
        st.session_state.hr_u_start = u_start
        st.session_state.hr_u_end = u_end
        us, ur = hr_user_stats(token, sel_user, u_start.isoformat(), u_end.isoformat())
        if us != 200:
            st.error(ur.get("detail", "Failed."))
        else:
            u_days = ur.get("days", [])
            um1, um2, um3 = st.columns(3)
            um1.metric("🍵 Tea", ur.get("total_tea", 0))
            um2.metric("☕ Coffee", ur.get("total_coffee", 0))
            um3.metric("📅 Days", ur.get("order_days", 0))
            if u_days:
                udf = pd.DataFrame(u_days).set_index("date")
                udf = udf[["tea", "coffee"]].rename(columns={"tea": "Tea", "coffee": "Coffee"})
                u_t1, u_t2 = st.tabs(["Bar", "Line"])
                with u_t1:
                    st.bar_chart(udf.sort_index(), color=["#3B82F6", "#F97316"])
                with u_t2:
                    st.line_chart(udf.sort_index(), color=["#3B82F6", "#F97316"])
