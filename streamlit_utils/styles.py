THEME_CSS = """
<style>
/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }
[data-testid="stSidebarNav"] { display: none; }

/* Page background */
.stApp { background: linear-gradient(160deg, #EDE9FE 0%, #F3F0FF 60%, #EDE9FE 100%); }

/* ── Purple gradient cards ── */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: linear-gradient(145deg, #9333EA 0%, #7C3AED 50%, #6D28D9 100%) !important;
    border-radius: 22px !important;
    border: none !important;
    box-shadow: 0 10px 40px rgba(109, 40, 217, 0.28) !important;
    overflow: hidden !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] > div {
    border: none !important;
    background: transparent !important;
}

/* White text inside cards */
div[data-testid="stVerticalBlockBorderWrapper"] p,
div[data-testid="stVerticalBlockBorderWrapper"] span,
div[data-testid="stVerticalBlockBorderWrapper"] label,
div[data-testid="stVerticalBlockBorderWrapper"] .stMarkdown p {
    color: rgba(255,255,255,0.95) !important;
}

/* Selectbox inside card */
div[data-testid="stVerticalBlockBorderWrapper"] [data-baseweb="select"] > div {
    background: white !important;
    border: none !important;
    border-radius: 12px !important;
}

/* Inputs inside card */
div[data-testid="stVerticalBlockBorderWrapper"] input,
div[data-testid="stVerticalBlockBorderWrapper"] textarea {
    background: white !important;
    border-radius: 12px !important;
    border: none !important;
    color: #1F2937 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] input[type="number"] {
    text-align: center !important;
    font-size: 22px !important;
    font-weight: 700 !important;
}

/* Buttons inside card */
div[data-testid="stVerticalBlockBorderWrapper"] button {
    background: white !important;
    color: #7C3AED !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
    letter-spacing: 1.5px !important;
    font-size: 13px !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] button:hover {
    background: #EDE9FE !important;
}

/* ── Chat box ── */
.chat-box {
    background: white;
    border-radius: 14px;
    padding: 14px 16px;
    min-height: 260px;
    max-height: 260px;
    overflow-y: auto;
    font-size: 13px;
    line-height: 1.5;
}
.chat-empty {
    color: #9CA3AF;
    font-style: italic;
    text-align: center;
    padding-top: 90px;
}
.chat-msg { padding: 5px 0; border-bottom: 1px solid #F3F4F6; }
.chat-msg:last-child { border-bottom: none; }
.chat-msg .name { font-weight: 700; color: #7C3AED; }
.chat-msg.sys { color: #9CA3AF; font-style: italic; text-align: center; font-size: 11px; }

/* ── Order preview badge ── */
.order-preview {
    background: rgba(255,255,255,0.18);
    border-radius: 12px;
    padding: 14px 18px;
    margin: 10px 0;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.order-badge {
    background: white;
    color: #7C3AED;
    border-radius: 8px;
    padding: 5px 14px;
    font-weight: 700;
    font-size: 17px;
}
</style>
"""
