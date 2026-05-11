import streamlit as st

if not st.session_state.get("token"):
    st.switch_page("app.py")

st.set_page_config(page_title="CS 1.6", page_icon="🎮", layout="wide")

st.markdown("### 🎮 Counter-Strike 1.6")

st.html("""
<div id="cs-progress-wrap" style="margin-bottom:8px">
    <div id="cs-progress-text" style="font-size:13px;color:#aaa;margin-bottom:4px">
        ⏳ Open the game below and assets will start downloading…
    </div>
    <div style="background:#222;border-radius:6px;height:8px;overflow:hidden;display:none" id="cs-bar-bg">
        <div id="cs-bar" style="height:100%;background:#f5a623;width:0%;transition:width 0.3s ease"></div>
    </div>
</div>
<script>
(function() {
    function update() {
        var raw = localStorage.getItem('cs_progress');
        if (!raw) return;
        var d = JSON.parse(raw);
        var text = document.getElementById('cs-progress-text');
        var bar  = document.getElementById('cs-bar');
        var bg   = document.getElementById('cs-bar-bg');
        if (d.done) {
            text.textContent = '✅ Game assets loaded — enjoy!';
            text.style.color = '#4ade80';
            bar.style.width  = '100%';
        } else if (d.pct > 0) {
            text.textContent = 'Downloading game assets… ' + d.pct + '% (' + d.mb + ' MB / ~412 MB)';
            text.style.color = '#aaa';
            bg.style.display = 'block';
            bar.style.width  = d.pct + '%';
        }
    }
    setInterval(update, 1000);
})();
</script>
""")

st.iframe("/app/static/game.html", height=700)
