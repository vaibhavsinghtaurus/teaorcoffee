import streamlit as st

if not st.session_state.get("token"):
    st.switch_page("app.py")

st.set_page_config(page_title="CS 1.6", page_icon="🎮", layout="wide")

st.iframe(
    "/app/static/game.html",
    height=700,
    scrolling=False,
)
