import streamlit as st
from streamlit_utils.api import _base

if not st.session_state.get("token"):
    st.switch_page("app.py")

st.set_page_config(page_title="CS 1.6", page_icon="🎮", layout="wide")

st.markdown("### 🎮 Counter-Strike 1.6")


@st.fragment(run_every=2)
def download_status():
    import requests
    try:
        r = requests.get(
            f"{_base()}/cs/download/progress",
            headers={"Authorization": f"Bearer {st.session_state.token}"},
            timeout=2,
        )
        if r.ok:
            d = r.json()
            if d["done"]:
                st.success("✅ Game assets loaded — enjoy!")
            elif d["pct"] > 0:
                st.progress(d["pct"] / 100, text=f"Downloading game assets… {d['pct']}% ({d['mb']} MB / ~412 MB)")
            else:
                st.info("⏳ Waiting for game to start loading…")
    except Exception:
        pass


download_status()

st.iframe("/app/static/game.html", height=700)
