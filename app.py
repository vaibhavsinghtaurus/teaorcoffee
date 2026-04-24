import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from streamlit_utils.api import login as api_login
from streamlit_utils.styles import THEME_CSS

st.set_page_config(
    page_title="Tea or Coffee ☕",
    page_icon="☕",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(THEME_CSS, unsafe_allow_html=True)

for key, default in [("token", None), ("username", None)]:
    if key not in st.session_state:
        st.session_state[key] = default

if st.session_state.token:
    st.switch_page("pages/1_Order.py")

# ── Login card ────────────────────────────────────────────────────────────────
_, center, _ = st.columns([1, 1.6, 1])
with center:
    with st.container(border=True):
        st.markdown(
            "<h1 style='text-align:center;color:white;margin:0;padding:8px 0 4px'>☕ Tea or Coffee</h1>"
            "<p style='text-align:center;color:rgba(255,255,255,0.75);margin:0 0 20px'>Sign in to place your order</p>",
            unsafe_allow_html=True,
        )

        name = st.text_input(
            "Name", placeholder="Enter your name…", label_visibility="collapsed"
        )
        password = st.text_input(
            "Password",
            placeholder="Password (leave blank if first login)…",
            type="password",
            label_visibility="collapsed",
        )

        if st.button("SIGN IN", use_container_width=True, type="primary"):
            if not name.strip():
                st.error("Please enter your name.")
            else:
                with st.spinner("Signing in…"):
                    try:
                        result = api_login(name.strip(), password.strip() or None)
                        if result.get("success"):
                            st.session_state.token = result["token"]
                            st.session_state.username = result["name"]
                            st.rerun()
                        elif result.get("password_required"):
                            st.error("Password required — please enter your password.")
                        else:
                            st.error(result.get("message", "Login failed. Check your name."))
                    except Exception as exc:
                        st.error(f"Cannot reach server: {exc}")
