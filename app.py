import os
import sys
import socket
import subprocess
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import streamlit.components.v1 as components


def _port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) != 0


def _start_backend() -> None:
    if not _port_free(8000):
        return  # already running

    def _run() -> None:
        subprocess.run(
            [sys.executable, "-m", "uvicorn", "src.teaorcoffee.main:app",
             "--host", "0.0.0.0", "--port", "8000"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )

    threading.Thread(target=_run, daemon=True).start()
    time.sleep(2)


_start_backend()

from streamlit_utils.api import login as api_login
from streamlit_utils.styles import get_css

st.set_page_config(
    page_title="Tea or Coffee ☕",
    page_icon="☕",
    layout="centered",
    initial_sidebar_state="collapsed",
)

for key, default in [("token", None), ("username", None), ("theme", "dark")]:
    if key not in st.session_state:
        st.session_state[key] = default

st.markdown(get_css(st.session_state.theme), unsafe_allow_html=True)

if st.session_state.token:
    st.switch_page("pages/1_Order.py")

# ── Theme toggle ──────────────────────────────────────────────────────────────
_, toggle_col = st.columns([5, 1])
with toggle_col:
    is_dark = st.toggle("🌙", value=st.session_state.theme == "dark", key="theme_toggle_login")
    st.session_state.theme = "dark" if is_dark else "light"

# ── Login card ────────────────────────────────────────────────────────────────
_, center, _ = st.columns([1, 1.6, 1])
with center:
    with st.container(border=True):
        st.markdown(
            "<h2 style='text-align:center;margin:0;padding:8px 0 4px'>☕ Tea or Coffee</h2>"
            "<p style='text-align:center;opacity:0.6;margin:0 0 20px'>Sign in to place your order</p>",
            unsafe_allow_html=True,
        )

        name = st.text_input("Name", placeholder="Enter your name…", label_visibility="collapsed")
        password = st.text_input(
            "Password", placeholder="Password (leave blank if first login)…",
            type="password", label_visibility="collapsed",
        )

        # Fix browser autofill not triggering React's onChange: poll for autofilled
        # inputs and dispatch a native input event so React syncs its controlled state.
        components.html(
            """
            <script>
            (function() {
                const setter = Object.getOwnPropertyDescriptor(
                    window.parent.HTMLInputElement.prototype, 'value'
                ).set;
                function syncAutofill() {
                    window.parent.document
                        .querySelectorAll('input[type="text"], input[type="password"]')
                        .forEach(function(el) {
                            if (el.value && el.dataset.autofillSynced !== el.value) {
                                setter.call(el, el.value);
                                el.dispatchEvent(new Event('input', { bubbles: true }));
                                el.dataset.autofillSynced = el.value;
                            }
                        });
                }
                const intervalId = setInterval(syncAutofill, 300);
                window.addEventListener('beforeunload', function() {
                    clearInterval(intervalId);
                });
            })();
            </script>
            """,
            height=0,
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
