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

function showPending(data) {
  const container = document.getElementById('results');
  const titles = Object.keys(data);
  container.innerHTML = `
    <div class="card">
      <h2 style="margin-bottom:0.75rem">Pending Confirmation</h2>
      <p style="font-size:0.83rem;color:#64748b;margin-bottom:0.75rem">Candidate slots are highlighted on the calendar. Click one to confirm.</p>
      ${titles.map(t => `
        <div class="pending-item" id="pending-${CSS.escape(t)}">
          <span class="pending-dot"></span>
          <span>${esc(t)}</span>
        </div>
      `).join('')}
    </div>
  `;
}

document.addEventListener('DOMContentLoaded', () => {
  boot();
  document.getElementById('conversation').addEventListener('keydown', e => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) runScheduler();
  });
});
