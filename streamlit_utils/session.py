"""
Session management with localStorage persistence.
Every page calls require_auth() before anything else — it handles:
  1. Token already in session_state → pass through
  2. ?ls_token query param (from JS bridge redirect) → restore session
  3. Nothing → inject JS to read localStorage, redirect to SAME page with params, stop
"""
import streamlit as st

_LS_KEYS = {
    "ls_token":      "token",
    "ls_user":       "username",
    "ls_role":       "role",
    "ls_office_id":  "office_id",
    "ls_office_name":"office_name",
    "ls_company_id": "company_id",
    "ls_position":   "position",
}

_LS_BRIDGE_JS = """
<img src="" style="display:none" onerror="(function(){{
  var t=localStorage.getItem('toc_token');
  if(!t){{window.location.href='/';return;}}
  var url=new URL(window.location.href);
  url.searchParams.set('ls_token',t);
  url.searchParams.set('ls_user',localStorage.getItem('toc_username')||'');
  url.searchParams.set('ls_role',localStorage.getItem('toc_role')||'user');
  url.searchParams.set('ls_office_id',localStorage.getItem('toc_office_id')||'');
  url.searchParams.set('ls_office_name',localStorage.getItem('toc_office_name')||'');
  url.searchParams.set('ls_company_id',localStorage.getItem('toc_company_id')||'');
  url.searchParams.set('ls_position',localStorage.getItem('toc_position')||'');
  window.location.replace(url.toString());
}})()"/>
"""


def _restore_from_params() -> bool:
    ls_token = st.query_params.get("ls_token", "")
    if not ls_token:
        return False
    st.session_state.token = ls_token
    st.session_state.username = st.query_params.get("ls_user", "")
    st.session_state.role = st.query_params.get("ls_role", "user")
    st.session_state.office_id = st.query_params.get("ls_office_id", "")
    st.session_state.office_name = st.query_params.get("ls_office_name", "")
    st.session_state.company_id = st.query_params.get("ls_company_id", "")
    st.session_state.position = st.query_params.get("ls_position", "")
    st.query_params.clear()
    return True


def require_auth(allowed_roles: list[str] | None = None) -> dict:
    """
    Ensures user is authenticated. Returns session dict.
    Stops page execution if not authenticated.
    """
    # Step 1: already authenticated
    if st.session_state.get("token"):
        session = _current_session()
        if allowed_roles and session["role"] not in allowed_roles:
            st.error("Access denied — you don't have permission to view this page.")
            st.stop()
        return session

    # Step 2: restore from query params (JS bridge redirect)
    if _restore_from_params():
        session = _current_session()
        if allowed_roles and session["role"] not in allowed_roles:
            st.error("Access denied.")
            st.stop()
        return session

    # Step 3: inject JS bridge — redirects back to THIS page with ls_token params
    st.html(_LS_BRIDGE_JS)
    st.stop()
    return {}  # unreachable


def _current_session() -> dict:
    return {
        "token":       st.session_state.get("token", ""),
        "username":    st.session_state.get("username", ""),
        "role":        st.session_state.get("role", "user"),
        "office_id":   st.session_state.get("office_id", ""),
        "office_name": st.session_state.get("office_name", ""),
        "company_id":  st.session_state.get("company_id", ""),
        "position":    st.session_state.get("position", ""),
    }


def save_session_to_localStorage(result: dict) -> str:
    """Returns HTML snippet that saves login result to localStorage."""
    tok = result.get("token", "").replace("'", "\\'")
    usr = result.get("name", "").replace("'", "\\'")
    role = result.get("role", "user").replace("'", "\\'")
    oid = result.get("office_id", "").replace("'", "\\'") if result.get("office_id") else ""
    oname = result.get("office_name", "").replace("'", "\\'") if result.get("office_name") else ""
    cid = result.get("company_id", "").replace("'", "\\'") if result.get("company_id") else ""
    pos = result.get("position", "").replace("'", "\\'") if result.get("position") else ""
    return (
        f"<img src='' style='display:none' onerror=\""
        f"localStorage.setItem('toc_token','{tok}');"
        f"localStorage.setItem('toc_username','{usr}');"
        f"localStorage.setItem('toc_role','{role}');"
        f"localStorage.setItem('toc_office_id','{oid}');"
        f"localStorage.setItem('toc_office_name','{oname}');"
        f"localStorage.setItem('toc_company_id','{cid}');"
        f"localStorage.setItem('toc_position','{pos}');"
        f"\"/>"
    )


def clear_localStorage() -> str:
    """Returns HTML snippet that clears all toc_* keys from localStorage."""
    return (
        "<img src='' style='display:none' onerror=\""
        "['toc_token','toc_username','toc_role','toc_office_id',"
        "'toc_office_name','toc_company_id','toc_position']"
        ".forEach(function(k){{localStorage.removeItem(k)}});"
        "window.location.href='/';\">"
    )


def do_logout():
    st.session_state.clear()
    st.html(clear_localStorage())
    st.stop()
