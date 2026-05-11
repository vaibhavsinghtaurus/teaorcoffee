import streamlit as st

if not st.session_state.get("token"):
    st.switch_page("app.py")

st.set_page_config(page_title="CS 1.6", page_icon="🎮", layout="wide")

st.markdown("### 🎮 Launching Counter-Strike 1.6…")
st.info("⏳ First load downloads ~412 MB of game assets. Subsequent loads are instant (cached).")

# Redirect top-level window to the static game page, escaping Streamlit's iframe
st.html("""
<script>
    window.top.location.href = window.top.location.origin + '/app/static/game.html';
</script>
""")
