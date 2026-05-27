import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date as _date, timedelta

import pandas as pd
import streamlit as st

from streamlit_utils.api import (
    hr_get_orders,
    hr_get_stats_daily,
    hr_get_stats_user,
    hr_get_stats_users_day,
    hr_get_user_names,
    hr_place_order,
    hr_remove_order,
)
from streamlit_utils.styles import get_css

st.set_page_config(
    page_title="HR Panel — Tea or Coffee",
    page_icon="👔",
    layout="wide",
    initial_sidebar_state="collapsed",
)

if "theme" not in st.session_state:
    st.session_state.theme = "dark"

st.markdown(get_css(st.session_state.theme), unsafe_allow_html=True)

# ── Top bar ───────────────────────────────────────────────────────────────────
bar_l, bar_mid, bar_r = st.columns([4, 1, 1])
with bar_l:
    st.markdown("<h2 style='margin:0'>👔 HR / Manager Panel</h2>", unsafe_allow_html=True)
with bar_mid:
    is_dark = st.toggle("🌙", value=st.session_state.theme == "dark", key="theme_toggle_hr")
    if (is_dark and st.session_state.theme != "dark") or (
        not is_dark and st.session_state.theme != "light"
    ):
        st.session_state.theme = "dark" if is_dark else "light"
        st.rerun()
with bar_r:
    if st.button("← Orders", use_container_width=True):
        st.switch_page("pages/1_Order.py")

st.markdown("<div style='margin:8px 0'></div>", unsafe_allow_html=True)

# ── Password gate ─────────────────────────────────────────────────────────────
with st.container(border=True):
    st.markdown(
        "<h3 style='color:white;margin:0 0 8px'>HR Password</h3>",
        unsafe_allow_html=True,
    )
    hr_pw = st.text_input(
        "Password",
        type="password",
        placeholder="Enter HR password…",
        label_visibility="collapsed",
        key="hr_pw",
    )

if not hr_pw:
    st.info("Enter the HR password above to unlock the panel.")
    st.stop()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_orders, tab_stats = st.tabs(["📋 Orders", "📊 Stats"])


# ═══════════════════════ ORDERS TAB ══════════════════════════════════════════
with tab_orders:
    st.markdown("#### Today's Orders")

    if st.button("🔄 Refresh", key="hr_refresh_orders"):
        st.rerun()

    status_o, resp_o = hr_get_orders(hr_pw)

    if status_o == 401:
        st.error("Wrong HR password.")
        st.stop()
    elif status_o == 503:
        st.error("HR access is not configured on this server.")
        st.stop()
    elif status_o != 200:
        st.error(resp_o.get("detail", "Could not load orders."))
    else:
        m1, m2 = st.columns(2)
        m1.metric("🍵 Total Tea", resp_o.get("total_tea", 0))
        m2.metric("☕ Total Coffee", resp_o.get("total_coffee", 0))

        orders = resp_o.get("orders", [])
        if orders:
            st.markdown("---")
            for order in orders:
                bev = (
                    f"🍵 Tea ×{order['tea']}"
                    if order["tea"] > 0
                    else f"☕ Coffee ×{order['coffee']}"
                )
                c1, c2, c3 = st.columns([3, 3, 2])
                c1.write(f"**{order['name']}**")
                c2.write(bev)
                with c3:
                    if st.button("Remove", key=f"hr_rm_{order['name']}"):
                        s, r = hr_remove_order(order["name"], hr_pw)
                        if s == 200:
                            st.success(f"Removed {order['name']}'s order.")
                            st.rerun()
                        else:
                            st.error(r.get("detail", r.get("message", "Error")))
        else:
            st.info("No orders today.")

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
                "User name",
                key="hr_po_name",
                placeholder="User name…",
                label_visibility="collapsed",
            )
        with po_col2:
            po_bev = st.selectbox(
                "Beverage",
                ["🍵 Tea (max 2)", "☕ Coffee (max 1)"],
                key="hr_po_bev",
                label_visibility="collapsed",
            )

        po_qty = st.number_input(
            "Quantity",
            min_value=1,
            max_value=2 if "Tea" in po_bev else 1,
            value=1,
            step=1,
            key="hr_po_qty",
        )

        if st.button("PLACE ORDER", key="hr_po_btn", use_container_width=True, type="primary"):
            if not po_name.strip():
                st.error("Enter a user name.")
            else:
                tea = po_qty if "Tea" in po_bev else 0
                coffee = po_qty if "Coffee" in po_bev else 0
                s, r = hr_place_order(po_name.strip(), hr_pw, tea, coffee)
                if s == 200 and r.get("success"):
                    st.success(r["message"])
                    st.rerun()
                elif s == 409:
                    st.warning(r.get("detail", "User already ordered today."))
                else:
                    st.error(r.get("detail", r.get("message", "Error.")))


# ═══════════════════════ STATS TAB ═══════════════════════════════════════════
with tab_stats:
    _MIN_DATE = _date(2026, 1, 1)
    _today = _date.today()

    st.markdown("#### Daily Totals")

    preset_col1, preset_col2, preset_col3, preset_col4 = st.columns(4)

    if "hr_stats_start" not in st.session_state:
        st.session_state.hr_stats_start = _today - timedelta(days=6)
    if "hr_stats_end" not in st.session_state:
        st.session_state.hr_stats_end = _today

    with preset_col1:
        if st.button("This Week", use_container_width=True, key="hr_this_week"):
            st.session_state.hr_stats_start = _today - timedelta(days=_today.weekday())
            st.session_state.hr_stats_end = _today
            st.rerun()
    with preset_col2:
        if st.button("Last 7 Days", use_container_width=True, key="hr_last7"):
            st.session_state.hr_stats_start = _today - timedelta(days=6)
            st.session_state.hr_stats_end = _today
            st.rerun()
    with preset_col3:
        if st.button("This Month", use_container_width=True, key="hr_this_month"):
            st.session_state.hr_stats_start = _today.replace(day=1)
            st.session_state.hr_stats_end = _today
            st.rerun()
    with preset_col4:
        if st.button("Last Month", use_container_width=True, key="hr_last_month"):
            first = _today.replace(day=1)
            last_end = first - timedelta(days=1)
            st.session_state.hr_stats_start = last_end.replace(day=1)
            st.session_state.hr_stats_end = last_end
            st.rerun()

    dc1, dc2 = st.columns(2)
    with dc1:
        range_start = st.date_input(
            "From",
            value=st.session_state.hr_stats_start,
            min_value=_MIN_DATE,
            max_value=_today,
            key="hr_range_start",
        )
    with dc2:
        range_end = st.date_input(
            "To",
            value=st.session_state.hr_stats_end,
            min_value=_MIN_DATE,
            max_value=_today,
            key="hr_range_end",
        )

    if range_start > range_end:
        st.error("'From' date must be on or before 'To' date.")
    else:
        st.session_state.hr_stats_start = range_start
        st.session_state.hr_stats_end = range_end

        ds, dr = hr_get_stats_daily(hr_pw, range_start.isoformat(), range_end.isoformat())
        if ds == 401:
            st.error("Wrong HR password.")
        elif ds != 200:
            st.error(dr.get("detail", "Failed to load stats."))
        else:
            days = dr.get("days", [])
            total_tea = sum(d["tea"] for d in days)
            total_coffee = sum(d["coffee"] for d in days)

            sm1, sm2, sm3 = st.columns(3)
            sm1.metric("🍵 Total Tea", total_tea)
            sm2.metric("☕ Total Coffee", total_coffee)
            sm3.metric("📅 Active Days", len(days))

            if days:
                df = pd.DataFrame(days).set_index("date")
                df.index.name = "Date"
                df.rename(columns={"tea": "Tea", "coffee": "Coffee"}, inplace=True)
                st.bar_chart(df.sort_index(), color=["#4CAF50", "#FF9800"])

    st.markdown("---")

    # ── Who ordered on a specific day ─────────────────────────────────────
    st.markdown("#### Who Ordered on a Specific Day")

    bd_col1, bd_col2 = st.columns([2, 1])
    with bd_col1:
        selected_day = st.date_input(
            "Select a day",
            value=_today,
            min_value=_MIN_DATE,
            max_value=_today,
            key="hr_breakdown_day",
        )
    with bd_col2:
        st.markdown("<div style='padding-top:28px'></div>", unsafe_allow_html=True)
        load_day = st.button("Load Breakdown", use_container_width=True, type="primary", key="hr_load_day")

    if load_day:
        ds2, dr2 = hr_get_stats_users_day(hr_pw, selected_day.isoformat())
        if ds2 == 200:
            orders2 = dr2.get("orders", [])
            st.markdown(
                f"**{dr2['date']}** — 🍵 {dr2['total_tea']} &nbsp;|&nbsp; ☕ {dr2['total_coffee']}"
            )
            if orders2:
                odf = pd.DataFrame(orders2)
                odf.rename(columns={"name": "Name", "tea": "Tea", "coffee": "Coffee"}, inplace=True)
                st.dataframe(odf.sort_values("Name"), use_container_width=True, hide_index=True)
            else:
                st.info("No orders on this day.")
        else:
            st.error(dr2.get("detail", "Failed to load breakdown."))

    st.markdown("---")

    # ── Per-user stats ────────────────────────────────────────────────────
    st.markdown("#### User Stats")

    names_s, names_r = hr_get_user_names(hr_pw)
    if names_s == 200:
        user_names = names_r.get("names", [])
        if user_names:
            selected_user = st.selectbox("Select a user", user_names, key="hr_user_select")
        else:
            st.info("No users found.")
            st.stop()
    else:
        st.warning(names_r.get("detail", "Could not load user list."))
        st.stop()

    if "hr_user_start" not in st.session_state:
        st.session_state.hr_user_start = _today - timedelta(days=6)
    if "hr_user_end" not in st.session_state:
        st.session_state.hr_user_end = _today

    u_p1, u_p2, u_p3, u_p4 = st.columns(4)
    with u_p1:
        if st.button("This Week", use_container_width=True, key="hr_u_week"):
            st.session_state.hr_user_start = _today - timedelta(days=_today.weekday())
            st.session_state.hr_user_end = _today
            st.rerun()
    with u_p2:
        if st.button("Last 7 Days", use_container_width=True, key="hr_u_last7"):
            st.session_state.hr_user_start = _today - timedelta(days=6)
            st.session_state.hr_user_end = _today
            st.rerun()
    with u_p3:
        if st.button("This Month", use_container_width=True, key="hr_u_month"):
            st.session_state.hr_user_start = _today.replace(day=1)
            st.session_state.hr_user_end = _today
            st.rerun()
    with u_p4:
        if st.button("Last Month", use_container_width=True, key="hr_u_last_month"):
            first = _today.replace(day=1)
            last_end = first - timedelta(days=1)
            st.session_state.hr_user_start = last_end.replace(day=1)
            st.session_state.hr_user_end = last_end
            st.rerun()

    u_col1, u_col2 = st.columns(2)
    with u_col1:
        user_start = st.date_input(
            "From",
            value=st.session_state.hr_user_start,
            min_value=_MIN_DATE,
            max_value=_today,
            key="hr_user_range_start",
        )
    with u_col2:
        user_end = st.date_input(
            "To",
            value=st.session_state.hr_user_end,
            min_value=_MIN_DATE,
            max_value=_today,
            key="hr_user_range_end",
        )

    if user_start > user_end:
        st.error("'From' date must be on or before 'To' date.")
    else:
        st.session_state.hr_user_start = user_start
        st.session_state.hr_user_end = user_end

        us, ur = hr_get_stats_user(
            hr_pw, selected_user, user_start.isoformat(), user_end.isoformat()
        )
        if us != 200:
            st.error(ur.get("detail", "Failed to load user stats."))
        else:
            u_days = ur.get("days", [])
            um1, um2, um3 = st.columns(3)
            um1.metric("🍵 Tea", ur.get("total_tea", 0))
            um2.metric("☕ Coffee", ur.get("total_coffee", 0))
            um3.metric("📅 Days Ordered", ur.get("order_days", 0))

            if u_days:
                u_df = pd.DataFrame(u_days).set_index("date")
                u_df.index.name = "Date"
                u_df.rename(columns={"tea": "Tea", "coffee": "Coffee"}, inplace=True)
                u_tab1, u_tab2 = st.tabs(["Bar Chart", "Line Chart"])
                with u_tab1:
                    st.bar_chart(u_df.sort_index(), color=["#4CAF50", "#FF9800"])
                with u_tab2:
                    st.line_chart(u_df.sort_index(), color=["#4CAF50", "#FF9800"])
            else:
                st.info(f"No orders for {selected_user} in this date range.")
