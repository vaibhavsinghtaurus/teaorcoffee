import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
from streamlit_utils.api import (
    get_orders_breakdown,
    get_my_vote,
    get_votes,
    place_vote,
    ws_base,
)
from streamlit_utils.chat_client import get_session
from streamlit_utils.styles import get_css

st.set_page_config(
    page_title="Order — Tea or Coffee",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="collapsed",
)

if "theme" not in st.session_state:
    st.session_state.theme = "dark"

st.markdown(get_css(st.session_state.theme), unsafe_allow_html=True)

if not st.session_state.get("token"):
    st.switch_page("app.py")

token: str = st.session_state.token
username: str = st.session_state.username

# ── Top bar ───────────────────────────────────────────────────────────────────
bar_left, bar_mid, bar_right = st.columns([4, 1, 1])
with bar_left:
    st.markdown(f"<h3 style='margin:0'>Good day, <b>{username}</b> 👋</h3>", unsafe_allow_html=True)
with bar_mid:
    is_dark = st.toggle("🌙", value=st.session_state.theme == "dark", key="theme_toggle")
    if (is_dark and st.session_state.theme != "dark") or (not is_dark and st.session_state.theme != "light"):
        st.session_state.theme = "dark" if is_dark else "light"
        st.rerun()
with bar_right:
    if username == "Vaibhav" and st.button("Admin →", use_container_width=True):
        st.switch_page("pages/2_Admin.py")
    if st.button("Logout", use_container_width=True):
        st.session_state.clear()
        st.switch_page("app.py")

st.markdown("<div style='margin:8px 0'></div>", unsafe_allow_html=True)

# ── Main columns ─────────────────────────────────────────────────────────────
left, right = st.columns(2, gap="large")

# ── ORDER CARD ────────────────────────────────────────────────────────────────
with left:
    with st.container(border=True):
        st.markdown(
            "<h2 style='text-align:center;color:white;margin:0'>Place Your Order</h2>"
            "<p style='text-align:center;color:rgba(255,255,255,0.75);margin:4px 0 16px'>Select your beverage and quantity</p>",
            unsafe_allow_html=True,
        )

        try:
            my_vote = get_my_vote(token)
        except Exception:
            my_vote = None

        if my_vote:
            tea_qty = my_vote["tea"]
            coffee_qty = my_vote["coffee"]
            if tea_qty > 0:
                emoji, qty, bev = "🍵", tea_qty, "Tea"
            else:
                emoji, qty, bev = "☕", coffee_qty, "Coffee"

            st.markdown(
                f"<div class='order-preview'>"
                f"  <span style='color:white;font-size:15px'>Your order:</span>"
                f"  <span class='order-badge'>{qty} {emoji} {bev}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
            st.success("✅ Order placed for today!")
        else:
            BEVERAGES = {
                "🍵  Tea (max 2)": ("tea", 2),
                "☕  Coffee (max 1)": ("coffee", 1),
            }

            bev_label = st.selectbox(
                "Beverage Type",
                list(BEVERAGES.keys()),
            )
            bev_type, max_qty = BEVERAGES[bev_label]

            qty = st.number_input("Quantity", min_value=1, max_value=max_qty, value=1, step=1)

            emoji = "🍵" if bev_type == "tea" else "☕"
            st.markdown(
                f"<div class='order-preview'>"
                f"  <span style='color:white;font-size:15px'>Your order:</span>"
                f"  <span class='order-badge'>{qty} {emoji}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

            if st.button("PLACE ORDER", use_container_width=True, type="primary"):
                tea = qty if bev_type == "tea" else 0
                coffee = qty if bev_type == "coffee" else 0
                with st.spinner("Placing order…"):
                    status, resp = place_vote(token, tea, coffee)
                if status == 201:
                    st.rerun()
                elif status == 409:
                    st.warning("You've already ordered today!")
                    st.rerun()
                elif status == 400:
                    st.error(resp.get("detail", "Invalid order."))
                else:
                    st.error(resp.get("detail", "Something went wrong."))


# ── CHAT CARD ─────────────────────────────────────────────────────────────────
with right:
    ws_url = f"{ws_base()}/ws/chat?token={token}"
    chat = get_session(token, ws_url)

    @st.fragment(run_every=3)
    def chat_card() -> None:
        messages = list(chat.messages[-30:])

        with st.container(border=True):
            st.markdown(
                f"<h2 style='text-align:center;color:white;margin:0'>💬 Live Chat</h2>"
                f"<p style='text-align:center;color:rgba(255,255,255,0.75);margin:4px 0 16px'>"
                f"You are: <b>{username}</b></p>",
                unsafe_allow_html=True,
            )

            if not messages:
                msgs_html = "<div class='chat-empty'>No messages yet. Start the conversation! 💬</div>"
            else:
                rows = []
                for m in messages:
                    name = m.get("name", "")
                    text = m.get("message", "")
                    if name == "system":
                        rows.append(f"<div class='chat-msg sys'>{text}</div>")
                    else:
                        safe_text = text.replace("<", "&lt;").replace(">", "&gt;")
                        rows.append(
                            f"<div class='chat-msg'><span class='name'>{name}</span>: {safe_text}</div>"
                        )
                msgs_html = "".join(rows)

            st.markdown(f"<div class='chat-box'>{msgs_html}</div>", unsafe_allow_html=True)

            if chat.error:
                st.warning(f"Chat disconnected: {chat.error}")

            send_col, btn_col = st.columns([4, 1])
            with send_col:
                if "chat_input" not in st.session_state:
                    st.session_state.chat_input = ""
                msg_text = st.text_input(
                    "msg",
                    placeholder="Type a message…",
                    label_visibility="collapsed",
                    key="chat_input",
                )
            with btn_col:
                if st.button("SEND", use_container_width=True, type="primary", key="chat_send"):
                    if msg_text.strip():
                        chat.send(msg_text.strip())
                        st.session_state.chat_input = ""
                        st.rerun()

    chat_card()


# ── LIVE TOTALS ───────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### 📊 Total Orders (Live)")


@st.fragment(run_every=5)
def live_totals() -> None:
    try:
        votes = get_votes(token)
        breakdown = get_orders_breakdown(token)

        m1, m2, m3 = st.columns(3)
        m1.metric("🍵 Tea", votes["tea"])
        m2.metric("☕ Coffee", votes["coffee"])
        m3.metric("👥 Total Orders", len(breakdown["orders"]))

        if breakdown["orders"]:
            rows = []
            for o in breakdown["orders"]:
                if o["tea"] > 0:
                    bev = f"🍵 Tea ×{o['tea']}"
                else:
                    bev = f"☕ Coffee ×{o['coffee']}"
                rows.append({"Name": o["name"], "Order": bev})
            st.table(rows)
        else:
            st.info("No orders placed today yet.")
    except Exception as exc:
        st.warning(f"Could not load totals: {exc}")


live_totals()
