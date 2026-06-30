import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date, timedelta
import pandas as pd
import streamlit as st
from streamlit_utils.api import get_stats_daily, get_stats_users_day, get_stat_user_names, get_stats_user_range
from streamlit_utils.styles import get_css
from streamlit_utils.session import require_auth, do_logout

_MIN_DATE = date(2026, 1, 1)

st.set_page_config(page_title="Stats — Tea or Coffee", page_icon="📊",
                   layout="wide", initial_sidebar_state="collapsed")

if "theme" not in st.session_state:
    st.session_state.theme = "dark"
st.markdown(get_css(st.session_state.theme), unsafe_allow_html=True)

sess = require_auth()
token = sess["token"]
username = sess["username"]
role = sess["role"]
office_name = sess["office_name"] or "Office"

bar_l, bar_m, bar_r = st.columns([5, 1, 2])
with bar_l:
    st.markdown(f"<div class='topbar-title'>📊 Stats <span class='office-tag'>{office_name}</span></div>",
                unsafe_allow_html=True)
with bar_m:
    is_dark = st.toggle("🌙", value=st.session_state.theme == "dark", key="theme_t_stats")
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

today = date.today()

# ── Date range presets ────────────────────────────────────────────────────────
p1, p2, p3, p4 = st.columns(4)
if "stats_start" not in st.session_state:
    st.session_state.stats_start = today - timedelta(days=6)
if "stats_end" not in st.session_state:
    st.session_state.stats_end = today
with p1:
    if st.button("This Week", use_container_width=True):
        st.session_state.stats_start = today - timedelta(days=today.weekday())
        st.session_state.stats_end = today
        st.rerun()
with p2:
    if st.button("Last 7 Days", use_container_width=True):
        st.session_state.stats_start = today - timedelta(days=6)
        st.session_state.stats_end = today
        st.rerun()
with p3:
    if st.button("This Month", use_container_width=True):
        st.session_state.stats_start = today.replace(day=1)
        st.session_state.stats_end = today
        st.rerun()
with p4:
    if st.button("Last Month", use_container_width=True):
        first = today.replace(day=1)
        end = first - timedelta(days=1)
        st.session_state.stats_start = end.replace(day=1)
        st.session_state.stats_end = end
        st.rerun()

dc1, dc2 = st.columns(2)
with dc1:
    range_start = st.date_input("From", value=st.session_state.stats_start,
                                min_value=_MIN_DATE, max_value=today, key="range_start")
with dc2:
    range_end = st.date_input("To", value=st.session_state.stats_end,
                              min_value=_MIN_DATE, max_value=today, key="range_end")

if range_start > range_end:
    st.error("'From' must be on or before 'To'.")
    st.stop()
st.session_state.stats_start = range_start
st.session_state.stats_end = range_end

# ── Daily totals ──────────────────────────────────────────────────────────────
status_code, resp = get_stats_daily(token, range_start.isoformat(), range_end.isoformat())
if status_code != 200:
    st.error(resp.get("detail", "Failed to load stats."))
    st.stop()

days = resp.get("days", [])
st.markdown("---")

total_tea = sum(d["tea"] for d in days)
total_coffee = sum(d["coffee"] for d in days)
m1, m2, m3 = st.columns(3)
m1.metric("🍵 Tea", total_tea)
m2.metric("☕ Coffee", total_coffee)
m3.metric("📅 Active Days", len(days))

st.markdown("---")
st.markdown("### Daily Orders")
if not days:
    st.info("No orders in this date range.")
else:
    df = pd.DataFrame(days).set_index("date")
    df.index.name = "Date"
    df = df[["tea", "coffee"]].rename(columns={"tea": "Tea", "coffee": "Coffee"}).sort_index()
    t1, t2 = st.tabs(["Bar Chart", "Line Chart"])
    with t1:
        st.bar_chart(df, color=["#3B82F6", "#F97316"])
    with t2:
        st.line_chart(df, color=["#3B82F6", "#F97316"])

# ── Day breakdown ─────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### Who Ordered on a Specific Day")
day_c1, day_c2 = st.columns([2, 1])
with day_c1:
    sel_day = st.date_input("Day", value=today, min_value=_MIN_DATE, max_value=today, key="breakdown_day")
with day_c2:
    st.markdown("<div style='padding-top:28px'></div>", unsafe_allow_html=True)
    load_btn = st.button("Load Breakdown", use_container_width=True, type="primary")

if load_btn:
    st.session_state["_bd_day"] = sel_day.isoformat()
    st.session_state.pop("_bd_data", None)

if "_bd_day" in st.session_state and "_bd_data" not in st.session_state:
    s2, r2 = get_stats_users_day(token, st.session_state["_bd_day"])
    if s2 == 200:
        st.session_state["_bd_data"] = r2
    else:
        st.error(r2.get("detail", "Failed."))

if "_bd_data" in st.session_state:
    bd = st.session_state["_bd_data"]
    orders_bd = bd.get("orders", [])
    st.markdown(f"**{bd['date']}** — 🍵 {bd['total_tea']} | ☕ {bd['total_coffee']}")
    if not orders_bd:
        st.info("No orders on this day.")
    else:
        bd_df = pd.DataFrame(orders_bd)
        bd_df.rename(columns={"name": "Name", "product_name": "Product", "qty": "Qty"}, inplace=True)
        cols_show = [c for c in ["Name", "Product", "Qty", "tea", "coffee"] if c in bd_df.columns]
        bt1, bt2 = st.tabs(["Table", "Chart"])
        with bt1:
            st.dataframe(bd_df[cols_show].sort_values("Name"), use_container_width=True, hide_index=True)
        with bt2:
            if "tea" in bd_df.columns:
                chart_df = bd_df.set_index("Name")[["tea", "coffee"]].rename(columns={"tea": "Tea", "coffee": "Coffee"})
                st.bar_chart(chart_df, color=["#3B82F6", "#F97316"])

# ── User stats ────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### User Stats")

_is_elevated = role in ("main_admin", "office_admin", "office_hr")
if _is_elevated:
    ns, nr = get_stat_user_names(token)
    user_names = nr.get("names", []) if ns == 200 else []
    if user_names:
        sel_user = st.selectbox("Select user", user_names, key="user_sel")
    elif username:
        sel_user = username
        st.markdown(f"Showing stats for **{sel_user}**")
    else:
        st.info("No users available.")
        st.stop()
else:
    sel_user = username
    st.markdown(f"Showing stats for **{sel_user}**")

up1, up2, up3, up4, up5 = st.columns(5)
if "u_s_start" not in st.session_state:
    st.session_state.u_s_start = today - timedelta(days=6)
if "u_s_end" not in st.session_state:
    st.session_state.u_s_end = today
with up1:
    if st.button("This Week", use_container_width=True, key="u_week"):
        st.session_state.u_s_start = today - timedelta(days=today.weekday())
        st.session_state.u_s_end = today
        st.rerun()
with up2:
    if st.button("Last 7 Days", use_container_width=True, key="u_last7"):
        st.session_state.u_s_start = today - timedelta(days=6)
        st.session_state.u_s_end = today
        st.rerun()
with up3:
    if st.button("This Month", use_container_width=True, key="u_month"):
        st.session_state.u_s_start = today.replace(day=1)
        st.session_state.u_s_end = today
        st.rerun()
with up4:
    if st.button("Last Month", use_container_width=True, key="u_lmonth"):
        first = today.replace(day=1)
        end = first - timedelta(days=1)
        st.session_state.u_s_start = end.replace(day=1)
        st.session_state.u_s_end = end
        st.rerun()
with up5:
    if st.button("This Year", use_container_width=True, key="u_year"):
        st.session_state.u_s_start = today.replace(month=1, day=1)
        st.session_state.u_s_end = today
        st.rerun()

uc1, uc2 = st.columns(2)
with uc1:
    u_start = st.date_input("From", value=st.session_state.u_s_start,
                            min_value=_MIN_DATE, max_value=today, key="u_range_s")
with uc2:
    u_end = st.date_input("To", value=st.session_state.u_s_end,
                          min_value=_MIN_DATE, max_value=today, key="u_range_e")

if u_start > u_end:
    st.error("'From' must be on or before 'To'.")
else:
    st.session_state.u_s_start = u_start
    st.session_state.u_s_end = u_end
    u_code, u_resp = get_stats_user_range(token, sel_user, u_start.isoformat(), u_end.isoformat())
    if u_code != 200:
        st.error(u_resp.get("detail", "Failed."))
    else:
        u_days = u_resp.get("days", [])
        um1, um2, um3 = st.columns(3)
        um1.metric("🍵 Tea", u_resp.get("total_tea", 0))
        um2.metric("☕ Coffee", u_resp.get("total_coffee", 0))
        um3.metric("📅 Days Ordered", u_resp.get("order_days", 0))
        if u_days:
            u_df = pd.DataFrame(u_days).set_index("date")
            u_df.index.name = "Date"
            if "tea" in u_df.columns and "coffee" in u_df.columns:
                u_df = u_df[["tea", "coffee"]].rename(columns={"tea": "Tea", "coffee": "Coffee"}).sort_index()
                u_t1, u_t2 = st.tabs(["Bar Chart", "Line Chart"])
                with u_t1:
                    st.bar_chart(u_df, color=["#3B82F6", "#F97316"])
                with u_t2:
                    st.line_chart(u_df, color=["#3B82F6", "#F97316"])
        else:
            st.info(f"No orders for {sel_user} in this range.")
