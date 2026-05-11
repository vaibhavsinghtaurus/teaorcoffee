import streamlit as st

if not st.session_state.get("token"):
    st.switch_page("app.py")

st.set_page_config(page_title="CS 1.6", page_icon="🎮", layout="wide")

host   = st.context.headers.get("host", "localhost:8501")
scheme = "https" if "streamlit.app" in host else "http"
game_url = f"{scheme}://{host}/app/static/game.html"

st.markdown("### 🎮 Counter-Strike 1.6")
st.info("⚠️ First load downloads ~412 MB of game assets. Subsequent loads are instant (cached).")
st.link_button("▶ Launch Game (Full Page)", game_url, use_container_width=True, type="primary")
