import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
from streamlit_utils.api import get_my_vote, place_vote, get_office_products, ws_base
from streamlit_utils.chat_client import get_session, get_vote_session
from streamlit_utils.styles import get_css
from streamlit_utils.session import require_auth, do_logout

st.set_page_config(page_title="Order — Tea or Coffee", page_icon="☕",
                   layout="wide", initial_sidebar_state="collapsed")

if "theme" not in st.session_state:
    st.session_state.theme = "dark"
st.markdown(get_css(st.session_state.theme), unsafe_allow_html=True)

sess = require_auth()
token = sess["token"]
username = sess["username"]
role = sess["role"]
office_name = sess["office_name"] or "Office"

if st.session_state.pop("_do_logout", False):
    do_logout()

# ── Top bar ───────────────────────────────────────────────────────────────────
bar_l, bar_m, bar_r = st.columns([5, 1, 2])
with bar_l:
    st.markdown(
        f"<div class='topbar-title'>☕ <span>Good day, <b>{username}</b></span>"
        f"<span class='office-tag'>{office_name}</span></div>",
        unsafe_allow_html=True,
    )
with bar_m:
    is_dark = st.toggle("🌙", value=st.session_state.theme == "dark", key="theme_t")
    if (is_dark and st.session_state.theme != "dark") or (not is_dark and st.session_state.theme != "light"):
        st.session_state.theme = "dark" if is_dark else "light"
        st.rerun()

with bar_r:
    btn_cols = st.columns([1, 1, 1])
    with btn_cols[0]:
        if st.button("📊 Stats", use_container_width=True):
            st.switch_page("pages/4_Stats.py")
    with btn_cols[1]:
        # Role-aware nav button
        if role == "main_admin" and st.button("⚙️ Admin", use_container_width=True):
            st.switch_page("pages/2_Admin.py")
        elif role == "office_admin" and st.button("🏢 Office", use_container_width=True):
            st.switch_page("pages/5_Office_Admin.py")
        elif role == "office_hr" and st.button("👔 HR", use_container_width=True):
            st.switch_page("pages/3_HR.py")
    with btn_cols[2]:
        if st.button("Logout", use_container_width=True):
            st.session_state._do_logout = True
            st.rerun()

st.markdown("<div style='margin:8px 0'></div>", unsafe_allow_html=True)

# ── Load products ─────────────────────────────────────────────────────────────
if "products_cache" not in st.session_state:
    st.session_state.products_cache = get_office_products(token)
products = st.session_state.products_cache

left, right = st.columns(2, gap="large")

# ── ORDER CARD ────────────────────────────────────────────────────────────────
with left:
    with st.container(border=True):
        st.markdown(
            "<h2 style='text-align:center;margin:0'>Place Your Order</h2>"
            "<p style='text-align:center;opacity:0.6;margin:4px 0 16px;font-size:13px'>Select your beverage for today</p>",
            unsafe_allow_html=True,
        )

        if "my_vote" not in st.session_state:
            try:
                st.session_state.my_vote = get_my_vote(token)
            except Exception:
                st.session_state.my_vote = None
        my_vote = st.session_state.my_vote

        if my_vote:
            emoji = my_vote.get("product_emoji", "☕")
            name_p = my_vote.get("product_name", "")
            qty = my_vote.get("qty", 1)
            st.markdown(
                f"<div class='order-preview'>"
                f"  <span style='font-size:14px'>Your order today:</span>"
                f"  <span class='order-badge'>{qty} {emoji} {name_p}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
            st.success("✅ Order placed for today!")
        elif not products:
            st.info("No products available yet. Contact your admin.")
        else:
            prod_labels = [f"{p['emoji']}  {p['name']} (max {p['max_qty']})" for p in products]
            selected_label = st.selectbox("Beverage", prod_labels, label_visibility="collapsed")
            selected_idx = prod_labels.index(selected_label)
            selected_prod = products[selected_idx]

            qty = st.number_input("Quantity", min_value=1, max_value=selected_prod["max_qty"], value=1, step=1)

            st.markdown(
                f"<div class='order-preview'>"
                f"  <span style='font-size:14px'>Your order:</span>"
                f"  <span class='order-badge'>{qty} {selected_prod['emoji']}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

            if st.button("PLACE ORDER", use_container_width=True, type="primary"):
                with st.spinner("Placing order…"):
                    status_code, resp = place_vote(token, selected_prod["id"], qty)
                if status_code == 201:
                    st.session_state.pop("my_vote", None)
                    st.rerun()
                elif status_code == 409:
                    st.session_state.pop("my_vote", None)
                    st.warning("You've already ordered today!")
                    st.rerun()
                else:
                    st.error(resp.get("detail", "Something went wrong."))

# ── WebSocket sessions ────────────────────────────────────────────────────────
ws_url = f"{ws_base()}/ws/chat?token={token}"
chat = get_session(token, ws_url)
vote_session = get_vote_session(token, f"{ws_base()}/ws/votes?token={token}")

# ── CHAT ─────────────────────────────────────────────────────────────────────
with right:
    @st.fragment(run_every=3)
    def chat_card() -> None:
        messages = list(chat.messages[-30:])
        with st.container(border=True):
            st.markdown(
                f"<h2 style='text-align:center;margin:0'>💬 Live Chat</h2>"
                f"<p style='text-align:center;opacity:0.6;margin:4px 0 16px;font-size:13px'>You: <b>{username}</b></p>",
                unsafe_allow_html=True,
            )
            if not messages:
                msgs_html = "<div class='chat-empty'>No messages yet. Start the conversation! 💬</div>"
            else:
                rows = []
                for m in messages:
                    n = m.get("name", "")
                    text = m.get("message", "")
                    if n == "system":
                        rows.append(f"<div class='chat-msg sys'>{text}</div>")
                    else:
                        safe = text.replace("<", "&lt;").replace(">", "&gt;")
                        rows.append(f"<div class='chat-msg'><span class='name'>{n}</span>: {safe}</div>")
                msgs_html = "".join(rows)
            st.markdown(f"<div class='chat-box'>{msgs_html}</div>", unsafe_allow_html=True)
            if chat.error:
                st.warning(f"Chat disconnected: {chat.error}")
            if st.session_state.pop("_chat_clear", False):
                st.session_state.chat_input = ""
            send_col, btn_col = st.columns([4, 1])
            with send_col:
                msg_text = st.text_input("msg", placeholder="Type a message…",
                                         label_visibility="collapsed", key="chat_input")
            with btn_col:
                if st.button("SEND", use_container_width=True, type="primary", key="chat_send"):
                    if msg_text.strip():
                        chat.send(msg_text.strip())
                        st.session_state["_chat_clear"] = True
                        st.rerun()
    chat_card()

# ── LIVE TOTALS ───────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### 📊 Total Orders (Live)")


@st.fragment(run_every=3)
def live_totals() -> None:
    data = vote_session.data
    totals = data.get("totals", {})
    orders = data.get("orders", [])
    order_count = data.get("order_count", len(orders))

    if totals:
        cols = st.columns(len(totals) + 1)
        for i, (prod_name, info) in enumerate(totals.items()):
            emoji = info.get("emoji", "") if isinstance(info, dict) else ""
            total = info.get("total", info) if isinstance(info, dict) else info
            cols[i].metric(f"{emoji} {prod_name}", total)
        cols[-1].metric("👥 Total Orders", order_count)
    else:
        st.metric("👥 Total Orders", order_count)

    if orders:
        rows = []
        for o in orders:
            bev = f"{o.get('product_emoji','☕')} {o.get('product_name','')} ×{o.get('qty',1)}"
            rows.append({"Name": o["name"], "Order": bev})
        st.table(rows)
    else:
        st.info("No orders placed today yet.")

    if vote_session.error:
        st.warning(f"Live updates disconnected: {vote_session.error}")


live_totals()
