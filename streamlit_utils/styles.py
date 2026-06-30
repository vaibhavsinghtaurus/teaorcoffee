_COMMON = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }
[data-testid="stSidebarNav"] { display: none; }

* { font-family: 'Inter', system-ui, sans-serif !important; }

/* ── Metrics ── */
[data-testid="stMetric"] { border-radius: 10px; padding: 14px 18px; }
[data-testid="stMetricValue"] { font-size: 26px !important; font-weight: 700 !important; }
[data-testid="stMetricLabel"] { font-size: 11px !important; font-weight: 500 !important; letter-spacing: 0.5px; text-transform: uppercase; }

/* ── Tables ── */
[data-testid="stTable"] table { border-radius: 8px; font-size: 13px; }
[data-testid="stTable"] th { padding: 10px 14px !important; font-weight: 600 !important; }
[data-testid="stTable"] td { padding: 9px 14px !important; }

/* ── Tabs ── */
[data-testid="stTabs"] button {
    font-size: 13px !important; font-weight: 500 !important;
    background: transparent !important; border: none !important;
}

/* ── Chat ── */
.chat-box {
    border-radius: 10px; padding: 14px 16px;
    min-height: 260px; max-height: 280px; overflow-y: auto;
    font-size: 13px; line-height: 1.65;
}
.chat-empty { font-style: italic; text-align: center; padding-top: 90px; font-size: 12px; }
.chat-msg { padding: 5px 0; }
.chat-msg:last-child { border-bottom: none; }
.chat-msg.sys { font-style: italic; text-align: center; font-size: 11px; }

/* ── Order card ── */
.order-preview {
    border-radius: 10px; padding: 14px 18px; margin: 10px 0;
    display: flex; justify-content: space-between; align-items: center;
}
.order-badge { border-radius: 8px; padding: 5px 14px; font-weight: 700; font-size: 15px; }

/* ── Role badge ── */
.role-badge {
    display: inline-block; border-radius: 20px; padding: 3px 12px;
    font-size: 11px; font-weight: 600; letter-spacing: 0.5px; text-transform: uppercase;
}
.role-main_admin   { background: #3b1f6e; color: #c4b5fd; border: 1px solid #7c3aed; }
.role-office_admin { background: #1e3a5f; color: #93c5fd; border: 1px solid #2563eb; }
.role-office_hr    { background: #1a4731; color: #86efac; border: 1px solid #16a34a; }
.role-user         { background: #1e2a3a; color: #94a3b8; border: 1px solid #475569; }
.role-company_admin     { background: #3d1a00; color: #fdba74; border: 1px solid #ea580c; }
.role-distributor_staff { background: #2d1b00; color: #fbbf24; border: 1px solid #d97706; }

/* ── Nav bar ── */
.topbar { display: flex; align-items: center; justify-content: space-between; padding: 0 0 16px; }
.topbar-title { font-size: 20px; font-weight: 700; display: flex; align-items: center; gap: 10px; }
.office-tag { font-size: 12px; font-weight: 500; padding: 3px 10px; border-radius: 12px; }

hr { margin: 16px 0; }
"""

_DARK = """
.stApp { background: #0A0D13; }
p, span, label, div, h1, h2, h3, h4, h5, li { color: #E2E8F0; }

/* Cards */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: #141920 !important;
    border-radius: 12px !important;
    border: 1px solid #1E2635 !important;
    box-shadow: 0 4px 24px rgba(0,0,0,0.5) !important;
    overflow: hidden !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] > div { border: none !important; background: transparent !important; }
div[data-testid="stVerticalBlockBorderWrapper"] p,
div[data-testid="stVerticalBlockBorderWrapper"] span,
div[data-testid="stVerticalBlockBorderWrapper"] label { color: #E2E8F0 !important; }
div[data-testid="stVerticalBlockBorderWrapper"] [data-baseweb="select"] > div {
    background: #0A0D13 !important; border: 1px solid #1E2635 !important; border-radius: 8px !important; color: #E2E8F0 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] input,
div[data-testid="stVerticalBlockBorderWrapper"] textarea {
    background: #0A0D13 !important; border: 1px solid #1E2635 !important; border-radius: 8px !important; color: #E2E8F0 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] input[type="number"] {
    text-align: center !important; font-size: 22px !important; font-weight: 700 !important; color: #60A5FA !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] input:focus,
div[data-testid="stVerticalBlockBorderWrapper"] textarea:focus {
    border-color: #3B82F6 !important; box-shadow: 0 0 0 3px rgba(59,130,246,0.15) !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] button {
    background: #1E2635 !important; color: #60A5FA !important;
    border: 1px solid #2D3748 !important; border-radius: 8px !important;
    font-weight: 600 !important; font-size: 12px !important; letter-spacing: 0.5px;
}
div[data-testid="stVerticalBlockBorderWrapper"] button:hover { background: #2D3748 !important; border-color: #3B82F6 !important; }
div[data-testid="stVerticalBlockBorderWrapper"] button[kind="primary"] {
    background: #1D4ED8 !important; color: #fff !important; border: 1px solid #2563EB !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] button[kind="primary"]:hover { background: #2563EB !important; }

input, textarea, [data-baseweb="select"] > div {
    background: #141920 !important; border: 1px solid #1E2635 !important;
    border-radius: 8px !important; color: #E2E8F0 !important;
}
button[kind="secondary"] {
    background: #1E2635 !important; color: #E2E8F0 !important;
    border: 1px solid #2D3748 !important; border-radius: 8px !important;
}
button[kind="primary"] {
    background: #1D4ED8 !important; color: #fff !important;
    border: 1px solid #2563EB !important; border-radius: 8px !important;
}

[data-testid="stMetric"] { background: #141920; border: 1px solid #1E2635; }
[data-testid="stMetricValue"] { color: #60A5FA !important; }
[data-testid="stMetricLabel"] { color: #64748B !important; }

[data-testid="stTable"] table { background: #141920; border: 1px solid #1E2635; }
[data-testid="stTable"] th { background: #1E2635 !important; color: #64748B !important; border-bottom: 1px solid #2D3748 !important; }
[data-testid="stTable"] td { color: #E2E8F0 !important; border-bottom: 1px solid #1E2635 !important; }

[data-testid="stTabs"] button { color: #64748B !important; border-bottom: 2px solid transparent !important; }
[data-testid="stTabs"] button[aria-selected="true"] { color: #60A5FA !important; border-bottom: 2px solid #3B82F6 !important; }

[data-testid="stSuccess"] { background: #0D2219 !important; border: 1px solid #16A34A !important; border-radius: 8px !important; }
[data-testid="stError"]   { background: #220D0D !important; border: 1px solid #DC2626 !important; border-radius: 8px !important; }
[data-testid="stWarning"] { background: #221A0D !important; border: 1px solid #D97706 !important; border-radius: 8px !important; }
[data-testid="stInfo"]    { background: #0D1929 !important; border: 1px solid #2563EB !important; border-radius: 8px !important; }

hr { border-color: #1E2635 !important; }

.chat-box { background: #0A0D13; border: 1px solid #1E2635; }
.chat-empty { color: #374151; }
.chat-msg { border-bottom: 1px solid #1E2635; color: #E2E8F0; }
.chat-msg .name { font-weight: 700; color: #60A5FA; }
.chat-msg.sys { color: #374151; }

.order-preview { background: #0A0D13; border: 1px solid #1E2635; }
.order-preview span { color: #64748B; }
.order-badge { background: #1D4ED8; color: #fff; border: 1px solid #2563EB; }

.office-tag { background: #1E2635; color: #64748B; }
"""

_LIGHT = """
.stApp { background: #F1F5F9; }
p, span, label, div, h1, h2, h3, h4, h5, li { color: #0F172A; }

div[data-testid="stVerticalBlockBorderWrapper"] {
    background: #FFFFFF !important;
    border-radius: 12px !important;
    border: 1px solid #E2E8F0 !important;
    box-shadow: 0 2px 16px rgba(0,0,0,0.06) !important;
    overflow: hidden !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] > div { border: none !important; background: transparent !important; }
div[data-testid="stVerticalBlockBorderWrapper"] p,
div[data-testid="stVerticalBlockBorderWrapper"] span,
div[data-testid="stVerticalBlockBorderWrapper"] label { color: #0F172A !important; }
div[data-testid="stVerticalBlockBorderWrapper"] [data-baseweb="select"] > div {
    background: #F8FAFC !important; border: 1px solid #E2E8F0 !important; border-radius: 8px !important; color: #0F172A !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] input,
div[data-testid="stVerticalBlockBorderWrapper"] textarea {
    background: #F8FAFC !important; border: 1px solid #E2E8F0 !important; border-radius: 8px !important; color: #0F172A !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] input[type="number"] {
    text-align: center !important; font-size: 22px !important; font-weight: 700 !important; color: #1D4ED8 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] input:focus,
div[data-testid="stVerticalBlockBorderWrapper"] textarea:focus {
    border-color: #2563EB !important; box-shadow: 0 0 0 3px rgba(37,99,235,0.12) !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] button {
    background: #F8FAFC !important; color: #1D4ED8 !important;
    border: 1px solid #E2E8F0 !important; border-radius: 8px !important;
    font-weight: 600 !important; font-size: 12px !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] button:hover { background: #EFF6FF !important; border-color: #2563EB !important; }
div[data-testid="stVerticalBlockBorderWrapper"] button[kind="primary"] {
    background: #1D4ED8 !important; color: #fff !important; border: 1px solid #1D4ED8 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] button[kind="primary"]:hover { background: #2563EB !important; }

input, textarea, [data-baseweb="select"] > div {
    background: #FFFFFF !important; border: 1px solid #E2E8F0 !important;
    border-radius: 8px !important; color: #0F172A !important;
}
button[kind="secondary"] {
    background: #F8FAFC !important; color: #0F172A !important;
    border: 1px solid #E2E8F0 !important; border-radius: 8px !important;
}
button[kind="primary"] {
    background: #1D4ED8 !important; color: #fff !important;
    border: 1px solid #1D4ED8 !important; border-radius: 8px !important;
}

[data-testid="stMetric"] { background: #FFFFFF; border: 1px solid #E2E8F0; }
[data-testid="stMetricValue"] { color: #1D4ED8 !important; }
[data-testid="stMetricLabel"] { color: #64748B !important; }

[data-testid="stTable"] table { background: #FFFFFF; border: 1px solid #E2E8F0; }
[data-testid="stTable"] th { background: #F8FAFC !important; color: #64748B !important; border-bottom: 1px solid #E2E8F0 !important; }
[data-testid="stTable"] td { color: #0F172A !important; border-bottom: 1px solid #F1F5F9 !important; }

[data-testid="stTabs"] button { color: #64748B !important; border-bottom: 2px solid transparent !important; }
[data-testid="stTabs"] button[aria-selected="true"] { color: #1D4ED8 !important; border-bottom: 2px solid #1D4ED8 !important; }

[data-testid="stSuccess"] { background: #F0FDF4 !important; border: 1px solid #16A34A !important; border-radius: 8px !important; }
[data-testid="stError"]   { background: #FEF2F2 !important; border: 1px solid #DC2626 !important; border-radius: 8px !important; }
[data-testid="stWarning"] { background: #FFFBEB !important; border: 1px solid #D97706 !important; border-radius: 8px !important; }
[data-testid="stInfo"]    { background: #EFF6FF !important; border: 1px solid #2563EB !important; border-radius: 8px !important; }

hr { border-color: #E2E8F0 !important; }

.chat-box { background: #F8FAFC; border: 1px solid #E2E8F0; }
.chat-empty { color: #94A3B8; }
.chat-msg { border-bottom: 1px solid #F1F5F9; color: #0F172A; }
.chat-msg .name { font-weight: 700; color: #1D4ED8; }
.chat-msg.sys { color: #94A3B8; }

.order-preview { background: #F8FAFC; border: 1px solid #E2E8F0; }
.order-preview span { color: #64748B; }
.order-badge { background: #1D4ED8; color: #fff; border: 1px solid #1D4ED8; }

.office-tag { background: #E2E8F0; color: #64748B; }
"""


def get_css(theme: str = "dark") -> str:
    palette = _DARK if theme == "dark" else _LIGHT
    return f"<style>{_COMMON}{palette}</style>"


THEME_CSS = get_css("dark")
