const API = 'http://localhost:8001';

// ── Utils ──────────────────────────────────────────────────────────────────

function esc(s) {
  if (!s) return '';
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function fmt(iso) {
  return new Date(iso).toLocaleString('en-US', {
    weekday:'short', month:'short', day:'numeric',
    hour:'numeric', minute:'2-digit', hour12:true,
  });
}

function dur(a, b) {
  const m = Math.round((new Date(b) - new Date(a)) / 60000);
  if (m < 60) return `${m}m`;
  const h = Math.floor(m / 60), r = m % 60;
  return r ? `${h}h ${r}m` : `${h}h`;
}

// ── Boot ──────────────────────────────────────────────────────────────────

async function boot() {
  const res  = await fetch(`${API}/auth/status`);
  const data = await res.json();
  if (data.authenticated) {
    showApp();
  } else {
    document.getElementById('login-screen').style.display = 'flex';
  }
}

async function showApp() {
  document.getElementById('login-screen').style.display = 'none';
  document.getElementById('app-screen').style.display   = 'block';
  const now = new Date();
  calYear  = now.getFullYear();
  calMonth = now.getMonth() + 1;
  renderCalHeader();
  renderCalGrid();
  await fetch(`${API}/sync`, { method: 'POST' });
  loadEvents();
}

function logout() {
  window.location.href = `${API}/auth/login`;
}

// ── Scheduler ─────────────────────────────────────────────────────────────

function setStatus(msg, type) {
  const el = document.getElementById('status-msg');
  if (!msg) { el.style.display = 'none'; return; }
  el.className = 'status ' + type;
  el.textContent = msg;
  el.style.display = 'block';
}

async function runScheduler() {
  const conversation = document.getElementById('conversation').value.trim();
  if (!conversation) { setStatus('Please enter a conversation.', 'error'); return; }

  const btn = document.getElementById('run-btn');
  btn.disabled = true;
  btn.textContent = 'Analyzing…';
  setStatus('Extracting schedules and finding available slots…', 'loading');
  document.getElementById('results').innerHTML = '';
  calCandidates = [];
  highlightedTitle = null;
  renderCalGrid();

  try {
    const res = await fetch(`${API}/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ conversation }),
    });
    if (!res.ok) throw new Error(`Server error ${res.status}`);
    const data = await res.json();
    const titles = Object.keys(data);
    if (!titles.length) {
      setStatus('No schedules found in the conversation.', 'error');
    } else {
      setStatus(`Found ${titles.length} schedule${titles.length > 1 ? 's' : ''} — click a highlighted slot on the calendar to confirm.`, 'success');
      showPending(data);
      setCandidates(data);
      // Navigate to month of first slot and reload to show candidates
      const firstSlot = Object.values(data).flatMap(d => d.slots)[0];
      if (firstSlot) {
        const d = new Date(firstSlot.start);
        calYear = d.getFullYear(); calMonth = d.getMonth() + 1;
        renderCalHeader();
      }
      await loadEvents();
    }
  } catch (err) {
    setStatus(`Error: ${err.message}`, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Analyze Schedule';
  }
}

function fmtSlot(start, end) {
  const s = new Date(start), e = new Date(end);
  const date  = s.toLocaleDateString('en-US', { weekday:'short', month:'short', day:'numeric' });
  const tStart = s.toLocaleTimeString('en-US', { hour:'numeric', minute:'2-digit', hour12:true });
  const tEnd   = e.toLocaleTimeString('en-US', { hour:'numeric', minute:'2-digit', hour12:true });
  return `${date},  ${tStart} – ${tEnd}`;
}

function navigateToSlot(isoStart) {
  const d = new Date(isoStart);
  calYear  = d.getFullYear();
  calMonth = d.getMonth() + 1;
  renderCalHeader();
  loadEvents();
}

function showPending(data) {
  const container = document.getElementById('results');
  const titles = Object.keys(data);
  container.innerHTML = `
    <div class="card">
      <h2 style="margin-bottom:0.75rem">Pending Confirmation</h2>
      <p style="font-size:0.83rem;color:#64748b;margin-bottom:0.75rem">Click a title to highlight its slots on the calendar. Click a slot row to navigate to that date.</p>
      ${titles.map(t => {
        const slots = data[t].slots;
        return `
          <div class="pending-group">
            <div class="pending-item" id="pending-${CSS.escape(t)}" data-title="${esc(t)}" onclick="highlightTitle(this.dataset.title)">
              <span class="pending-dot"></span>
              <span class="pending-title">${esc(t)}</span>
            </div>
            <div class="pending-slots">
              ${slots.map(s => `
                <div class="pending-slot" onclick="navigateToSlot('${s.start}')">
                  ${fmtSlot(s.start, s.end)}
                </div>
              `).join('')}
            </div>
          </div>
        `;
      }).join('')}
    </div>
  `;
}

// ── Settings ───────────────────────────────────────────────────────────────

let _settingsSnapshot = null;

function _hoursFromWindows(windows) {
  const active = new Set();
  for (const [s, e] of windows) {
    for (let h = s; h < e; h++) active.add(h);
  }
  return active;
}

function _windowsFromHours(activeHours) {
  const sorted = [...activeHours].sort((a, b) => a - b);
  if (!sorted.length) return [];
  const windows = [];
  let start = sorted[0], prev = sorted[0];
  for (let i = 1; i < sorted.length; i++) {
    if (sorted[i] === prev + 1) { prev = sorted[i]; }
    else { windows.push([start, prev + 1]); start = prev = sorted[i]; }
  }
  windows.push([start, prev + 1]);
  return windows;
}

function _makeBlocks(containerId, activeSet) {
  let html = '';
  for (let h = 0; h < 24; h++) {
    html += `<span class="hour-block${activeSet.has(h) ? ' active' : ''}" data-h="${h}" onclick="toggleHour(this)">${h}</span>`;
  }
  document.getElementById(containerId).innerHTML = html;
}

function _applySettings(cfg) {
  document.getElementById('cfg-timezone').value   = cfg.timezone ?? 'UTC';
  document.getElementById('cfg-days_ahead').value = cfg.days_ahead ?? '';
  document.getElementById('cfg-max_slots').value  = cfg.max_slots ?? '';
  const totalMin = cfg.default_duration_minutes ?? 0;
  document.getElementById('cfg-dur-h').value = Math.floor(totalMin / 60);
  document.getElementById('cfg-dur-m').value = totalMin % 60;

  const activeStart = cfg.valid_hour_start ?? 0;
  const activeEnd   = cfg.valid_hour_end   ?? 24;
  const activeHrs = new Set();
  for (let h = activeStart; h < activeEnd; h++) activeHrs.add(h);
  _makeBlocks('cfg-active-hours', activeHrs);

  const tbody = document.getElementById('cfg-categories-body');
  tbody.innerHTML = '';
  for (const [name, val] of Object.entries(cfg.categories ?? {})) {
    const active = _hoursFromWindows(val.preferred_time ?? []);
    let blocks = '';
    for (let h = 0; h < 24; h++) {
      blocks += `<span class="hour-block${active.has(h) ? ' active' : ''}" data-h="${h}" onclick="toggleHour(this)">${h}</span>`;
    }
    const tr = document.createElement('tr');
    tr.dataset.cat = name;
    tr.innerHTML = `<td class="cat-name">${esc(name)}</td><td><div class="hour-blocks">${blocks}</div></td>`;
    tbody.appendChild(tr);
  }
}

function _foldSettings() {
  document.getElementById('settings-body').style.display = 'none';
  document.getElementById('settings-chevron').innerHTML = '&#9660;';
}

function toggleHour(el) {
  el.classList.toggle('active');
}

async function loadSettings() {
  const cfg = await fetch(`${API}/config`).then(r => r.json());
  _settingsSnapshot = cfg;
  _applySettings(cfg);
}

async function saveSettings() {
  const cfg = JSON.parse(JSON.stringify(_settingsSnapshot));
  cfg.timezone   = document.getElementById('cfg-timezone').value;
  cfg.days_ahead = parseInt(document.getElementById('cfg-days_ahead').value);
  cfg.max_slots  = parseInt(document.getElementById('cfg-max_slots').value);
  cfg.default_duration_minutes = (parseInt(document.getElementById('cfg-dur-h').value) || 0) * 60
                                + (parseInt(document.getElementById('cfg-dur-m').value) || 0);

  const hrs = [...document.querySelectorAll('#cfg-active-hours .hour-block.active')].map(b => parseInt(b.dataset.h));
  if (hrs.length) {
    cfg.valid_hour_start = Math.min(...hrs);
    cfg.valid_hour_end   = Math.max(...hrs) + 1;
  }

  if (!cfg.categories) cfg.categories = {};
  document.querySelectorAll('#cfg-categories-body tr').forEach(tr => {
    const activeHours = [...tr.querySelectorAll('.hour-block.active')].map(b => parseInt(b.dataset.h));
    cfg.categories[tr.dataset.cat] = { preferred_time: _windowsFromHours(activeHours) };
  });

  const res = await fetch(`${API}/config`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(cfg),
  });
  if (res.ok) {
    _settingsSnapshot = cfg;
    _foldSettings();
  } else {
    const msg = document.getElementById('settings-msg');
    msg.textContent = 'Failed to save.';
    msg.style.color = '#dc2626';
    msg.style.display = 'block';
    setTimeout(() => { msg.style.display = 'none'; }, 2000);
  }
}

function cancelSettings() {
  if (_settingsSnapshot) _applySettings(_settingsSnapshot);
  _foldSettings();
}

function toggleSettings() {
  const body = document.getElementById('settings-body');
  const chevron = document.getElementById('settings-chevron');
  const open = body.style.display === 'none';
  body.style.display = open ? 'block' : 'none';
  chevron.innerHTML = open ? '&#9650;' : '&#9660;';
  if (open) loadSettings();
}

document.addEventListener('DOMContentLoaded', () => {
  boot();
  document.getElementById('conversation').addEventListener('keydown', e => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) runScheduler();
  });
});
