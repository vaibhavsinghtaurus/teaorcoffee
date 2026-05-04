import os
import sys
import socket
import subprocess
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st


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

# ── Restore session from localStorage (via query-param bridge) ────────────────
if not st.session_state.token:
    ls_token = st.query_params.get("ls_token")
    ls_user = st.query_params.get("ls_user", "")
    if ls_token:
        st.session_state.token = ls_token
        st.session_state.username = ls_user
        st.query_params.clear()

if st.session_state.token:
    st.switch_page("pages/1_Order.py")

# No token — inject JS to check localStorage and redirect back with it as a query param
st.html("""<img src="" onerror="(function(){
    const t=localStorage.getItem('toc_token');
    const u=localStorage.getItem('toc_username')||'';
    if(t){
        const url=new URL(window.location.href);
        url.searchParams.set('ls_token',t);
        url.searchParams.set('ls_user',u);
        window.location.replace(url.toString());
    }
})()" style="display:none"/>""")

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

        with st.form("login_form"):
            name = st.text_input("Name", placeholder="Enter your name…", label_visibility="collapsed", autocomplete="username")
            password = st.text_input(
                "Password", placeholder="Password (leave blank if first login)…",
                type="password", label_visibility="collapsed", autocomplete="current-password",
            )
            submitted = st.form_submit_button("SIGN IN", use_container_width=True, type="primary")

        if submitted:
            if not name.strip():
                st.error("Please enter your name.")
            else:
                with st.spinner("Signing in…"):
                    try:
                        result = api_login(name.strip(), password.strip() or None)
                        if result.get("success"):
                            _tok = result["token"]
                            _usr = result["name"].replace("'", "\\'")
                            st.session_state.token = _tok
                            st.session_state.username = result["name"]
                            st.html(f"<img src='' onerror=\"localStorage.setItem('toc_token','{_tok}');localStorage.setItem('toc_username','{_usr}');\" style='display:none'/>")
                            st.rerun()
                        elif result.get("password_required"):
                            st.error("Password required — please enter your password.")
                        else:
                            st.error(result.get("message", "Login failed. Check your name."))
                    except Exception as exc:
                        st.error(f"Cannot reach server: {exc}")
