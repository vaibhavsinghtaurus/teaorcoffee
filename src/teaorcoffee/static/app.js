// Shared: Auth, API, Theme, Toast, Utilities

const Auth = {
  getToken: () => localStorage.getItem('toc_token'),
  getUser: () => { try { return JSON.parse(localStorage.getItem('toc_user') || '{}'); } catch { return {}; } },
  setSession(data) {
    localStorage.setItem('toc_token', data.token || '');
    localStorage.setItem('toc_user', JSON.stringify({
      username: data.name || '', role: data.role || 'user',
      office_id: data.office_id || '', office_name: data.office_name || '',
      company_id: data.company_id || '', position: data.position || '',
    }));
  },
  clearSession() { localStorage.removeItem('toc_token'); localStorage.removeItem('toc_user'); window.location.href = '/'; },
  require(roles) {
    const token = this.getToken();
    if (!token) { window.location.href = '/'; return null; }
    const user = this.getUser();
    if (roles && roles.length && !roles.includes(user.role)) { window.location.href = '/'; return null; }
    return { token, ...user };
  },
};

const API = {
  async _fetch(path, opts = {}) {
    const token = Auth.getToken();
    const headers = { 'Content-Type': 'application/json', ...(opts.headers || {}) };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    try {
      const res = await fetch(path, { ...opts, headers });
      const data = await res.json().catch(() => ({}));
      if (res.status === 401) { Auth.clearSession(); return [401, data]; }
      return [res.status, data];
    } catch (e) { return [0, { detail: e.message }]; }
  },
  get: (path) => API._fetch(path),
  post: (path, body) => API._fetch(path, { method: 'POST', body: JSON.stringify(body) }),
  put:  (path, body) => API._fetch(path, { method: 'PUT',  body: JSON.stringify(body) }),
  del:  (path, body) => API._fetch(path, { method: 'DELETE', body: JSON.stringify(body) }),

  // Public endpoints (no Authorization header)
  async publicGet(path) {
    try {
      const res = await fetch(path, { headers: { 'Content-Type': 'application/json' } });
      const data = await res.json().catch(() => ({}));
      return [res.status, data];
    } catch (e) { return [0, { detail: e.message }]; }
  },
  async publicPost(path, body) {
    try {
      const res = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      const data = await res.json().catch(() => ({}));
      return [res.status, data];
    } catch (e) { return [0, { detail: e.message }]; }
  },
};

const Theme = {
  current: localStorage.getItem('toc_theme') || 'dark',
  apply() { document.documentElement.setAttribute('data-theme', this.current); },
  applyBtn(id) {
    const btn = document.getElementById(id);
    if (btn) btn.textContent = this.current === 'dark' ? '☀️' : '🌙';
  },
  toggle() {
    this.current = this.current === 'dark' ? 'light' : 'dark';
    localStorage.setItem('toc_theme', this.current);
    this.apply();
    const btn = document.getElementById('theme-btn');
    if (btn) btn.textContent = this.current === 'dark' ? '☀️' : '🌙';
  },
  init() {
    this.apply();
    const btn = document.getElementById('theme-btn');
    if (btn) { btn.textContent = this.current === 'dark' ? '☀️' : '🌙'; btn.onclick = () => this.toggle(); }
  },
};

const Toast = {
  show(msg, type = 'info', ms = 3500) {
    let c = document.getElementById('toasts');
    if (!c) { c = document.createElement('div'); c.id = 'toasts'; document.body.appendChild(c); }
    const t = document.createElement('div');
    t.className = `toast alert-${type}`;
    t.textContent = msg;
    c.appendChild(t);
    setTimeout(() => t.remove(), ms);
  },
  ok:   (m) => Toast.show(m, 'ok'),
  err:  (m) => Toast.show(m, 'err'),
  warn: (m) => Toast.show(m, 'warn'),
  info: (m) => Toast.show(m, 'info'),
};

function initTabs(containerId) {
  const el = document.getElementById(containerId);
  if (!el) return;
  const btns = el.querySelectorAll('.tab-btn');
  const panes = el.querySelectorAll('.tab-pane');
  btns.forEach((btn, i) => {
    btn.onclick = () => {
      btns.forEach(b => b.classList.remove('active'));
      panes.forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      panes[i].classList.add('active');
      if (btn.dataset.onshow) window[btn.dataset.onshow]?.();
    };
  });
  if (btns[0]) btns[0].click();
}

// Date utilities
const D = {
  today: () => new Date().toISOString().split('T')[0],
  addDays(d, n) { const x = new Date(d + 'T12:00:00'); x.setDate(x.getDate() + n); return x.toISOString().split('T')[0]; },
  weekStart() { const d = new Date(); d.setDate(d.getDate() - ((d.getDay() + 6) % 7)); return d.toISOString().split('T')[0]; },
  monthStart() { const d = new Date(); d.setDate(1); return d.toISOString().split('T')[0]; },
  lastMonth() {
    const d = new Date(); d.setDate(1); d.setDate(d.getDate() - 1);
    const end = d.toISOString().split('T')[0];
    d.setDate(1);
    return { start: d.toISOString().split('T')[0], end };
  },
};

// WS base
function wsBase() { return (location.protocol === 'https:' ? 'wss' : 'ws') + '://' + location.host; }

// Render metrics
function renderMetrics(containerId, items) {
  const el = document.getElementById(containerId);
  if (!el) return;
  el.innerHTML = items.map(({ label, value }) =>
    `<div class="metric"><div class="metric-label">${label}</div><div class="metric-value">${value}</div></div>`
  ).join('');
}

// Render a simple table
function renderTable(tbodyId, rows, cols) {
  const el = document.getElementById(tbodyId);
  if (!el) return;
  el.innerHTML = rows.map(r =>
    '<tr>' + cols.map(c => `<td>${c(r)}</td>`).join('') + '</tr>'
  ).join('') || '<tr><td colspan="100" style="text-align:center;color:var(--muted)">No data</td></tr>';
}

// Alert helper
function showAlert(containerId, msg, type = 'info') {
  const el = document.getElementById(containerId);
  if (!el) return;
  el.innerHTML = `<div class="alert alert-${type}">${msg}</div>`;
  setTimeout(() => { if (el) el.innerHTML = ''; }, 4000);
}

// Chart.js helpers
function buildChart(canvasId, labels, datasets, type = 'bar') {
  const el = document.getElementById(canvasId);
  if (!el) return null;
  if (el._chart) el._chart.destroy();
  const chart = new Chart(el, {
    type,
    data: { labels, datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { labels: { color: getComputedStyle(document.documentElement).getPropertyValue('--text').trim() } } },
      scales: {
        x: { ticks: { color: getComputedStyle(document.documentElement).getPropertyValue('--muted').trim() }, grid: { color: getComputedStyle(document.documentElement).getPropertyValue('--border').trim() } },
        y: { ticks: { color: getComputedStyle(document.documentElement).getPropertyValue('--muted').trim() }, grid: { color: getComputedStyle(document.documentElement).getPropertyValue('--border').trim() } },
      },
    },
  });
  el._chart = chart;
  return chart;
}

function teaCoffeeChart(canvasId, days, type = 'bar') {
  const labels = days.map(d => d.date);
  return buildChart(canvasId, labels, [
    { label: 'Tea', data: days.map(d => d.tea || 0), backgroundColor: '#3B82F6', borderColor: '#3B82F6', tension: 0.3 },
    { label: 'Coffee', data: days.map(d => d.coffee || 0), backgroundColor: '#F97316', borderColor: '#F97316', tension: 0.3 },
  ], type);
}

// Stats date range widget
function statsDateRange(prefix, onLoad) {
  const today = D.today();
  let start = D.addDays(today, -6), end = today;

  function setRange(s, e) {
    start = s; end = e;
    document.getElementById(prefix + '-from').value = s;
    document.getElementById(prefix + '-to').value = e;
    onLoad(s, e);
  }

  document.getElementById(prefix + '-from').value = start;
  document.getElementById(prefix + '-to').value = end;

  document.getElementById(prefix + '-week')?.addEventListener('click', () => setRange(D.weekStart(), today));
  document.getElementById(prefix + '-7d')?.addEventListener('click',  () => setRange(D.addDays(today, -6), today));
  document.getElementById(prefix + '-month')?.addEventListener('click', () => setRange(D.monthStart(), today));
  document.getElementById(prefix + '-lmonth')?.addEventListener('click', () => { const r = D.lastMonth(); setRange(r.start, r.end); });
  document.getElementById(prefix + '-from')?.addEventListener('change', e => { start = e.target.value; onLoad(start, end); });
  document.getElementById(prefix + '-to')?.addEventListener('change', e => { end = e.target.value; onLoad(start, end); });

  onLoad(start, end);
}
