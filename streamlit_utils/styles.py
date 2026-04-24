_COMMON = """
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&display=swap');

#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }
[data-testid="stSidebarNav"] { display: none; }

* { font-family: 'JetBrains Mono', 'Fira Code', monospace !important; }

[data-testid="stMetric"] { border-radius: 8px; padding: 12px 16px; }
[data-testid="stMetricValue"] { font-size: 28px !important; }
[data-testid="stMetricLabel"] { font-size: 12px !important; }

[data-testid="stTable"] table { border-radius: 8px; font-size: 13px; }
[data-testid="stTable"] th { padding: 10px 14px !important; }
[data-testid="stTable"] td { padding: 8px 14px !important; }

[data-testid="stTabs"] button {
    font-size: 13px !important;
    background: transparent !important;
    border: none !important;
}

.chat-box {
    border-radius: 8px;
    padding: 14px 16px;
    min-height: 260px;
    max-height: 260px;
    overflow-y: auto;
    font-size: 13px;
    line-height: 1.6;
}
.chat-empty { font-style: italic; text-align: center; padding-top: 90px; font-size: 12px; }
.chat-msg { padding: 5px 0; }
.chat-msg:last-child { border-bottom: none; }
.chat-msg.sys { font-style: italic; text-align: center; font-size: 11px; }

.order-preview {
    border-radius: 8px;
    padding: 12px 16px;
    margin: 10px 0;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.order-badge {
    border-radius: 6px;
    padding: 4px 12px;
    font-weight: 700;
    font-size: 15px;
}

hr { margin: 16px 0; }
"""

_DARK = """
.stApp { background: #0D1117; }
p, span, label, div, h1, h2, h3, h4, h5, li { color: #E6EDF3; }

div[data-testid="stVerticalBlockBorderWrapper"] {
    background: #161B22 !important;
    border-radius: 10px !important;
    border: 1px solid #30363D !important;
    box-shadow: 0 4px 24px rgba(0,0,0,0.4) !important;
    overflow: hidden !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] > div { border: none !important; background: transparent !important; }
div[data-testid="stVerticalBlockBorderWrapper"] p,
div[data-testid="stVerticalBlockBorderWrapper"] span,
div[data-testid="stVerticalBlockBorderWrapper"] label { color: #E6EDF3 !important; }
div[data-testid="stVerticalBlockBorderWrapper"] [data-baseweb="select"] > div {
    background: #0D1117 !important; border: 1px solid #30363D !important; border-radius: 6px !important; color: #E6EDF3 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] input,
div[data-testid="stVerticalBlockBorderWrapper"] textarea {
    background: #0D1117 !important; border: 1px solid #30363D !important;
    border-radius: 6px !important; color: #E6EDF3 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] input[type="number"] {
    text-align: center !important; font-size: 20px !important; font-weight: 600 !important; color: #58A6FF !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] input:focus,
div[data-testid="stVerticalBlockBorderWrapper"] textarea:focus {
    border-color: #58A6FF !important; box-shadow: 0 0 0 2px rgba(88,166,255,0.15) !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] button {
    background: #21262D !important; color: #58A6FF !important;
    border: 1px solid #30363D !important; border-radius: 6px !important;
    font-weight: 600 !important; letter-spacing: 1px !important; font-size: 12px !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] button:hover { background: #30363D !important; border-color: #58A6FF !important; }
div[data-testid="stVerticalBlockBorderWrapper"] button[kind="primary"] {
    background: #238636 !important; color: #fff !important; border: 1px solid #2EA043 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] button[kind="primary"]:hover { background: #2EA043 !important; }

input, textarea, [data-baseweb="select"] > div {
    background: #161B22 !important; border: 1px solid #30363D !important;
    border-radius: 6px !important; color: #E6EDF3 !important;
}
button[kind="secondary"] {
    background: #21262D !important; color: #E6EDF3 !important;
    border: 1px solid #30363D !important; border-radius: 6px !important;
}
button[kind="primary"] {
    background: #238636 !important; color: #fff !important;
    border: 1px solid #2EA043 !important; border-radius: 6px !important;
}

[data-testid="stMetric"] { background: #161B22; border: 1px solid #30363D; }
[data-testid="stMetricValue"] { color: #58A6FF !important; }
[data-testid="stMetricLabel"] { color: #8B949E !important; }

[data-testid="stTable"] table { background: #161B22; border: 1px solid #30363D; }
[data-testid="stTable"] th { background: #21262D !important; color: #8B949E !important; border-bottom: 1px solid #30363D !important; }
[data-testid="stTable"] td { color: #E6EDF3 !important; border-bottom: 1px solid #21262D !important; }

[data-testid="stTabs"] button { color: #8B949E !important; border-bottom: 2px solid transparent !important; }
[data-testid="stTabs"] button[aria-selected="true"] { color: #58A6FF !important; border-bottom: 2px solid #58A6FF !important; }

[data-testid="stSuccess"] { background: #0F2518 !important; border: 1px solid #2EA043 !important; border-radius: 6px !important; }
[data-testid="stError"]   { background: #2D1117 !important; border: 1px solid #F85149 !important; border-radius: 6px !important; }
[data-testid="stWarning"] { background: #271D0A !important; border: 1px solid #D29922 !important; border-radius: 6px !important; }
[data-testid="stInfo"]    { background: #0C1929 !important; border: 1px solid #58A6FF !important; border-radius: 6px !important; }

hr { border-color: #21262D !important; }

.chat-box { background: #0D1117; border: 1px solid #30363D; }
.chat-empty { color: #484F58; }
.chat-msg { border-bottom: 1px solid #21262D; color: #E6EDF3; }
.chat-msg .name { font-weight: 700; color: #58A6FF; }
.chat-msg.sys { color: #484F58; }

.order-preview { background: #0D1117; border: 1px solid #30363D; }
.order-preview span { color: #8B949E; }
.order-badge { background: #238636; color: #fff; border: 1px solid #2EA043; }
"""

_LIGHT = """
.stApp { background: #F6F8FA; }
p, span, label, div, h1, h2, h3, h4, h5, li { color: #1F2937; }

div[data-testid="stVerticalBlockBorderWrapper"] {
    background: #FFFFFF !important;
    border-radius: 10px !important;
    border: 1px solid #D0D7DE !important;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08) !important;
    overflow: hidden !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] > div { border: none !important; background: transparent !important; }
div[data-testid="stVerticalBlockBorderWrapper"] p,
div[data-testid="stVerticalBlockBorderWrapper"] span,
div[data-testid="stVerticalBlockBorderWrapper"] label { color: #1F2937 !important; }
div[data-testid="stVerticalBlockBorderWrapper"] [data-baseweb="select"] > div {
    background: #F6F8FA !important; border: 1px solid #D0D7DE !important; border-radius: 6px !important; color: #1F2937 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] input,
div[data-testid="stVerticalBlockBorderWrapper"] textarea {
    background: #F6F8FA !important; border: 1px solid #D0D7DE !important;
    border-radius: 6px !important; color: #1F2937 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] input[type="number"] {
    text-align: center !important; font-size: 20px !important; font-weight: 600 !important; color: #0550AE !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] input:focus,
div[data-testid="stVerticalBlockBorderWrapper"] textarea:focus {
    border-color: #0969DA !important; box-shadow: 0 0 0 2px rgba(9,105,218,0.15) !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] button {
    background: #F6F8FA !important; color: #0969DA !important;
    border: 1px solid #D0D7DE !important; border-radius: 6px !important;
    font-weight: 600 !important; letter-spacing: 1px !important; font-size: 12px !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] button:hover { background: #EAF2FF !important; border-color: #0969DA !important; }
div[data-testid="stVerticalBlockBorderWrapper"] button[kind="primary"] {
    background: #1A7F37 !important; color: #fff !important; border: 1px solid #1A7F37 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] button[kind="primary"]:hover { background: #218843 !important; }

input, textarea, [data-baseweb="select"] > div {
    background: #FFFFFF !important; border: 1px solid #D0D7DE !important;
    border-radius: 6px !important; color: #1F2937 !important;
}
button[kind="secondary"] {
    background: #F6F8FA !important; color: #1F2937 !important;
    border: 1px solid #D0D7DE !important; border-radius: 6px !important;
}
button[kind="primary"] {
    background: #1A7F37 !important; color: #fff !important;
    border: 1px solid #1A7F37 !important; border-radius: 6px !important;
}

[data-testid="stMetric"] { background: #FFFFFF; border: 1px solid #D0D7DE; }
[data-testid="stMetricValue"] { color: #0550AE !important; }
[data-testid="stMetricLabel"] { color: #57606A !important; }

[data-testid="stTable"] table { background: #FFFFFF; border: 1px solid #D0D7DE; }
[data-testid="stTable"] th { background: #F6F8FA !important; color: #57606A !important; border-bottom: 1px solid #D0D7DE !important; }
[data-testid="stTable"] td { color: #1F2937 !important; border-bottom: 1px solid #F0F0F0 !important; }

[data-testid="stTabs"] button { color: #57606A !important; border-bottom: 2px solid transparent !important; }
[data-testid="stTabs"] button[aria-selected="true"] { color: #0969DA !important; border-bottom: 2px solid #0969DA !important; }

[data-testid="stSuccess"] { background: #DAFBE1 !important; border: 1px solid #1A7F37 !important; border-radius: 6px !important; }
[data-testid="stError"]   { background: #FFEBE9 !important; border: 1px solid #CF222E !important; border-radius: 6px !important; }
[data-testid="stWarning"] { background: #FFF8C5 !important; border: 1px solid #9A6700 !important; border-radius: 6px !important; }
[data-testid="stInfo"]    { background: #DDF4FF !important; border: 1px solid #0969DA !important; border-radius: 6px !important; }

hr { border-color: #D0D7DE !important; }

.chat-box { background: #F6F8FA; border: 1px solid #D0D7DE; }
.chat-empty { color: #8C959F; }
.chat-msg { border-bottom: 1px solid #EAEEF2; color: #1F2937; }
.chat-msg .name { font-weight: 700; color: #0969DA; }
.chat-msg.sys { color: #8C959F; }

.order-preview { background: #F6F8FA; border: 1px solid #D0D7DE; }
.order-preview span { color: #57606A; }
.order-badge { background: #1A7F37; color: #fff; border: 1px solid #1A7F37; }
"""


def get_css(theme: str = "dark") -> str:
    palette = _DARK if theme == "dark" else _LIGHT
    return f"<style>{_COMMON}{palette}</style>"


# backward-compat alias
THEME_CSS = get_css("dark")
