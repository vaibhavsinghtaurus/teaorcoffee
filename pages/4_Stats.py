import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from streamlit_utils.api import get_stat_user_names, get_stats_daily, get_stats_user_range, get_stats_users_day
from streamlit_utils.styles import get_css

_MIN_DATE = date(2026, 1, 1)

st.set_page_config(
    page_title="Stats — Tea or Coffee",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

if "theme" not in st.session_state:
    st.session_state.theme = "dark"

st.markdown(get_css(st.session_state.theme), unsafe_allow_html=True)

# ── Top bar ───────────────────────────────────────────────────────────────────
bar_l, bar_mid, bar_r = st.columns([4, 1, 1])
with bar_l:
    st.markdown("<h2 style='margin:0'>📊 Order Stats</h2>", unsafe_allow_html=True)
with bar_mid:
    is_dark = st.toggle("🌙", value=st.session_state.theme == "dark", key="theme_toggle_stats")
    if (is_dark and st.session_state.theme != "dark") or (not is_dark and st.session_state.theme != "light"):
        st.session_state.theme = "dark" if is_dark else "light"
        st.rerun()
with bar_r:
    if st.button("← Orders", use_container_width=True):
        st.switch_page("pages/1_Order.py")

st.markdown("<div style='margin:8px 0'></div>", unsafe_allow_html=True)

# ── Date range selection ──────────────────────────────────────────────────────
today = date.today()

st.markdown("### Date Range")

preset_col1, preset_col2, preset_col3, preset_col4 = st.columns(4)

if "stats_start" not in st.session_state:
    st.session_state.stats_start = today - timedelta(days=6)
if "stats_end" not in st.session_state:
    st.session_state.stats_end = today

with preset_col1:
    if st.button("This Week", use_container_width=True):
        st.session_state.stats_start = today - timedelta(days=today.weekday())
        st.session_state.stats_end = today
        st.rerun()
with preset_col2:
    if st.button("Last 7 Days", use_container_width=True):
        st.session_state.stats_start = today - timedelta(days=6)
        st.session_state.stats_end = today
        st.rerun()
with preset_col3:
    if st.button("Last Month", use_container_width=True):
        first_of_month = today.replace(day=1)
        last_month_end = first_of_month - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        st.session_state.stats_start = last_month_start
        st.session_state.stats_end = last_month_end
        st.rerun()
with preset_col4:
    if st.button("This Month", use_container_width=True):
        st.session_state.stats_start = today.replace(day=1)
        st.session_state.stats_end = today
        st.rerun()

date_col1, date_col2 = st.columns(2)
with date_col1:
    range_start = st.date_input(
        "From",
        value=st.session_state.stats_start,
        min_value=_MIN_DATE,
        max_value=today,
        key="range_start",
    )
with date_col2:
    range_end = st.date_input(
        "To",
        value=st.session_state.stats_end,
        min_value=_MIN_DATE,
        max_value=today,
        key="range_end",
    )

if range_start > range_end:
    st.error("'From' date must be on or before 'To' date.")
    st.stop()

st.session_state.stats_start = range_start
st.session_state.stats_end = range_end

# ── Fetch daily totals ────────────────────────────────────────────────────────
status_code, resp = get_stats_daily("", range_start.isoformat(), range_end.isoformat())

if status_code == 401:
    st.error("Wrong password.")
    st.stop()
elif status_code != 200:
    st.error(resp.get("detail", "Failed to load stats."))
    st.stop()

days = resp.get("days", [])

st.markdown("---")

# ── Summary metrics ───────────────────────────────────────────────────────────
total_tea = sum(d["tea"] for d in days)
total_coffee = sum(d["coffee"] for d in days)
active_days = len(days)

m1, m2, m3 = st.columns(3)
m1.metric("🍵 Total Tea", total_tea)
m2.metric("☕ Total Coffee", total_coffee)
m3.metric("📅 Active Days", active_days)

st.markdown("---")

# ── Daily chart ───────────────────────────────────────────────────────────────
st.markdown("### Daily Orders")

if not days:
    st.info("No orders found for this date range.")
else:
    df = pd.DataFrame(days).set_index("date")
    df.index.name = "Date"
    df.rename(columns={"tea": "Tea", "coffee": "Coffee"}, inplace=True)
    df = df.sort_index()

    chart_tab1, chart_tab2 = st.tabs(["Bar Chart", "Line Chart"])
    with chart_tab1:
        st.bar_chart(df, color=["#4CAF50", "#FF9800"])
    with chart_tab2:
        st.line_chart(df, color=["#4CAF50", "#FF9800"])

st.markdown("---")

# ── Per-user breakdown for a specific day ─────────────────────────────────────
st.markdown("### Who Ordered What on a Specific Day")

day_col1, day_col2 = st.columns([2, 1])
with day_col1:
    selected_day = st.date_input(
        "Select a day",
        value=today,
        min_value=_MIN_DATE,
        max_value=today,
        key="breakdown_day",
    )
with day_col2:
    st.markdown("<div style='padding-top:28px'></div>", unsafe_allow_html=True)
    load_btn = st.button("Load Breakdown", use_container_width=True, type="primary")

if load_btn:
    st.session_state["_breakdown_day"] = selected_day.isoformat()
    st.session_state.pop("_breakdown_data", None)

if "_breakdown_day" in st.session_state and "_breakdown_data" not in st.session_state:
    s2, r2 = get_stats_users_day("", st.session_state["_breakdown_day"])
    if s2 == 200:
        st.session_state["_breakdown_data"] = r2
    else:
        st.error(r2.get("detail", "Failed to load breakdown."))

if "_breakdown_data" in st.session_state:
    bd = st.session_state["_breakdown_data"]
    orders = bd.get("orders", [])

    st.markdown(f"**{bd['date']}** — 🍵 {bd['total_tea']} tea &nbsp;|&nbsp; ☕ {bd['total_coffee']} coffee")

    if not orders:
        st.info("No orders on this day.")
    else:
        bd_df = pd.DataFrame(orders)
        bd_df.rename(columns={"name": "Name", "tea": "Tea", "coffee": "Coffee"}, inplace=True)
        bd_df = bd_df.sort_values("Name")

        bd_tab1, bd_tab2 = st.tabs(["Table", "Chart"])
        with bd_tab1:
            st.dataframe(
                bd_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Tea": st.column_config.NumberColumn("🍵 Tea"),
                    "Coffee": st.column_config.NumberColumn("☕ Coffee"),
                },
            )
        with bd_tab2:
            chart_df = bd_df.set_index("Name")[["Tea", "Coffee"]]
            st.bar_chart(chart_df, color=["#4CAF50", "#FF9800"])

st.markdown("---")

# ── Per-user stats ────────────────────────────────────────────────────────────
st.markdown("### User Stats")

_logged_username: str = st.session_state.get("username", "")
_is_admin = _logged_username == "Vaibhav"

if _is_admin:
    names_code, names_resp = get_stat_user_names()
    if names_code != 200:
        st.warning(names_resp.get("detail", "Could not load user list — showing your own stats."))
        user_names = []
    else:
        user_names = names_resp.get("names", [])

    if user_names:
        selected_user = st.selectbox("Select a user", user_names, key="user_stats_select")
    elif _logged_username:
        selected_user = _logged_username
        st.markdown(f"Showing stats for **{selected_user}**")
    else:
        st.info("No users available.")
        st.stop()
elif _logged_username:
    selected_user = _logged_username
    st.markdown(f"Showing stats for **{selected_user}**")
else:
    st.info("Log in to view your personal stats.")
    st.stop()

st.markdown("#### Date Range")

u_preset1, u_preset2, u_preset3, u_preset4, u_preset5 = st.columns(5)

if "user_stats_start" not in st.session_state:
    st.session_state.user_stats_start = today - timedelta(days=6)
if "user_stats_end" not in st.session_state:
    st.session_state.user_stats_end = today

with u_preset1:
    if st.button("This Week", use_container_width=True, key="u_this_week"):
        st.session_state.user_stats_start = today - timedelta(days=today.weekday())
        st.session_state.user_stats_end = today
        st.rerun()
with u_preset2:
    if st.button("Last 7 Days", use_container_width=True, key="u_last7"):
        st.session_state.user_stats_start = today - timedelta(days=6)
        st.session_state.user_stats_end = today
        st.rerun()
with u_preset3:
    if st.button("This Month", use_container_width=True, key="u_this_month"):
        st.session_state.user_stats_start = today.replace(day=1)
        st.session_state.user_stats_end = today
        st.rerun()
with u_preset4:
    if st.button("Last Month", use_container_width=True, key="u_last_month"):
        first_of_month = today.replace(day=1)
        last_month_end = first_of_month - timedelta(days=1)
        st.session_state.user_stats_start = last_month_end.replace(day=1)
        st.session_state.user_stats_end = last_month_end
        st.rerun()
with u_preset5:
    if st.button("This Year", use_container_width=True, key="u_this_year"):
        st.session_state.user_stats_start = today.replace(month=1, day=1)
        st.session_state.user_stats_end = today
        st.rerun()

u_col1, u_col2 = st.columns(2)
with u_col1:
    user_start = st.date_input(
        "From",
        value=st.session_state.user_stats_start,
        min_value=_MIN_DATE,
        max_value=today,
        key="user_range_start",
    )
with u_col2:
    user_end = st.date_input(
        "To",
        value=st.session_state.user_stats_end,
        min_value=_MIN_DATE,
        max_value=today,
        key="user_range_end",
    )

if user_start > user_end:
    st.error("'From' date must be on or before 'To' date.")
else:
    st.session_state.user_stats_start = user_start
    st.session_state.user_stats_end = user_end

    u_code, u_resp = get_stats_user_range(
        selected_user, user_start.isoformat(), user_end.isoformat()
    )

    if u_code != 200:
        st.error(u_resp.get("detail", "Failed to load user stats."))
    else:
        u_days = u_resp.get("days", [])
        u_total_tea = u_resp.get("total_tea", 0)
        u_total_coffee = u_resp.get("total_coffee", 0)
        u_order_days = u_resp.get("order_days", 0)

        um1, um2, um3 = st.columns(3)
        um1.metric("🍵 Tea", u_total_tea)
        um2.metric("☕ Coffee", u_total_coffee)
        um3.metric("📅 Days Ordered", u_order_days)

        if not u_days:
            st.info(f"No orders for {selected_user} in this date range.")
        else:
            u_df = pd.DataFrame(u_days).set_index("date")
            u_df.index.name = "Date"
            u_df.rename(columns={"tea": "Tea", "coffee": "Coffee"}, inplace=True)
            u_df = u_df.sort_index()

            u_tab1, u_tab2 = st.tabs(["Bar Chart", "Line Chart"])
            with u_tab1:
                st.bar_chart(u_df, color=["#4CAF50", "#FF9800"])
            with u_tab2:
                st.line_chart(u_df, color=["#4CAF50", "#FF9800"])
