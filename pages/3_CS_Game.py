import streamlit as st

if not st.session_state.get("token"):
    st.warning("Please sign in first.")
    st.stop()

st.set_page_config(page_title="CS 1.6", page_icon="🎮", layout="wide")

st.components.v1.iframe(
    "/app/static/game.html",
    height=700,
    scrolling=False,
)
