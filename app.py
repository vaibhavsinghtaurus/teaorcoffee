import os
import sys
import socket
import subprocess
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) != 0


def _start_backend() -> None:
    if not _port_free(8000):
        return
    def _run() -> None:
        subprocess.run(
            [sys.executable, "-m", "uvicorn", "src.teaorcoffee.main:app",
             "--host", "0.0.0.0", "--port", "8000"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
    threading.Thread(target=_run, daemon=True).start()
    time.sleep(2)


_start_backend()

import streamlit as st
from streamlit_utils.api import login as api_login
from streamlit_utils.styles import get_css
from streamlit_utils.session import save_session_to_localStorage, _restore_from_params

st.set_page_config(
    page_title="Tea or Coffee",
    page_icon="☕",
    layout="centered",
    initial_sidebar_state="collapsed",
)

for key, default in [("token", None), ("username", None), ("role", "user"),
                     ("office_id", ""), ("office_name", ""),
                     ("company_id", ""), ("position", ""), ("theme", "dark")]:
    if key not in st.session_state:
        st.session_state[key] = default

st.markdown(get_css(st.session_state.theme), unsafe_allow_html=True)

# ── Restore from query params (localStorage bridge) ───────────────────────────
if not st.session_state.token:
    _restore_from_params()

# ── Already logged in — route by role ─────────────────────────────────────────
if st.session_state.token:
    role = st.session_state.get("role", "user")
    if role == "main_admin":
        st.switch_page("pages/2_Admin.py")
    elif role == "office_admin":
        st.switch_page("pages/5_Office_Admin.py")
    elif role == "office_hr":
        st.switch_page("pages/3_HR.py")
    elif role in ("company_admin", "distributor_staff"):
        st.switch_page("pages/6_Distributor.py")
    else:
        st.switch_page("pages/1_Order.py")

# ── No token — inject localStorage bridge JS ──────────────────────────────────
st.html("""<img src="" style="display:none" onerror="(function(){
    var t=localStorage.getItem('toc_token');
    if(t){
        var url=new URL(window.location.href);
        url.searchParams.set('ls_token',t);
        url.searchParams.set('ls_user',localStorage.getItem('toc_username')||'');
        url.searchParams.set('ls_role',localStorage.getItem('toc_role')||'user');
        url.searchParams.set('ls_office_id',localStorage.getItem('toc_office_id')||'');
        url.searchParams.set('ls_office_name',localStorage.getItem('toc_office_name')||'');
        url.searchParams.set('ls_company_id',localStorage.getItem('toc_company_id')||'');
        url.searchParams.set('ls_position',localStorage.getItem('toc_position')||'');
        window.location.replace(url.toString());
    }
})()"/>""")

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
            "<h2 style='text-align:center;margin:0;padding:10px 0 4px'>☕ Tea or Coffee</h2>"
            "<p style='text-align:center;opacity:0.5;margin:0 0 22px;font-size:13px'>Sign in to place your order</p>",
            unsafe_allow_html=True,
        )
        with st.form("login_form"):
            name = st.text_input("Name", placeholder="Your name or nickname…",
                                 label_visibility="collapsed", autocomplete="username")
            password = st.text_input("Password", placeholder="Password…",
                                     type="password", label_visibility="collapsed",
                                     autocomplete="current-password")
            submitted = st.form_submit_button("SIGN IN", use_container_width=True, type="primary")

        if submitted:
            if not name.strip():
                st.error("Please enter your name.")
            else:
                with st.spinner("Signing in…"):
                    try:
                        result = api_login(name.strip(), password.strip() or None)
                        if result.get("success"):
                            st.session_state.token = result["token"]
                            st.session_state.username = result["name"]
                            st.session_state.role = result.get("role", "user")
                            st.session_state.office_id = result.get("office_id", "")
                            st.session_state.office_name = result.get("office_name", "")
                            st.session_state.company_id = result.get("company_id", "")
                            st.session_state.position = result.get("position", "")
                            st.html(save_session_to_localStorage(result))
                            st.rerun()
                        elif result.get("password_required"):
                            st.error("Password required — please enter your password.")
                        else:
                            st.error(result.get("message", "Login failed."))
                    except Exception as exc:
                        st.error(f"Cannot reach server: {exc}")
