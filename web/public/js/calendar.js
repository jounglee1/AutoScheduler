const MONTHS = ['January','February','March','April','May','June',
                'July','August','September','October','November','December'];
const DAYS   = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];

let calYear, calMonth, calEvents = [], calCandidates = [];
const calFilters = { confirmed: true, predicted: true, tentative: true };
let hiddenTitles = new Set();
let highlightedTitle = null;

function toggleFilter(type) {
  calFilters[type] = !calFilters[type];
  document.getElementById(`toggle-${type}`).classList.toggle('active', calFilters[type]);
  renderCalGrid();
}

function visibleEvents() {
  return calEvents.filter(e => {
    if (hiddenTitles.has(e.title)) return false;
    if (e.status === 'predicted') return calFilters.predicted;
    if (e.status === 'tentative') return calFilters.tentative;
    return calFilters.confirmed;
  });
}

function setTitleVisible(title, visible) {
  if (visible) hiddenTitles.delete(title);
  else hiddenTitles.add(title);
  renderCalGrid();
}

function highlightTitle(title) {
  highlightedTitle = highlightedTitle === title ? null : title;
  document.querySelectorAll('.pending-item').forEach(el => {
    el.classList.toggle('active', el.dataset.title === highlightedTitle);
  });
  renderCalGrid();
}

// ── Candidates (in-memory map for slotIndex lookup) ────────────────────────

function setCandidates(results) {
  calCandidates = [];
  for (const [title, { slots }] of Object.entries(results)) {
    slots.forEach((slot, i) => {
      calCandidates.push({ title, slotIndex: i, start: slot.start, end: slot.end, score: slot.score });
    });
  }
}

function clearCandidates(title) {
  calCandidates = calCandidates.filter(c => c.title !== title);
}

// ── Calendar ───────────────────────────────────────────────────────────────

function renderCalHeader() {
  document.getElementById('cal-title').textContent = `${MONTHS[calMonth - 1]} ${calYear}`;
  document.getElementById('cal-dow').innerHTML = DAYS.map(d => `<div class="cal-dow">${d}</div>`).join('');
}

async function loadEvents() {
  const res = await fetch(`${API}/events?year=${calYear}&month=${calMonth}`);
  calEvents = await res.json();
  renderCalGrid();
}

function renderCalGrid() {
  const grid  = document.getElementById('cal-grid');
  const today = new Date();
  const first = new Date(calYear, calMonth - 1, 1).getDay();
  const days  = new Date(calYear, calMonth, 0).getDate();

  let cells = '';
  for (let i = 0; i < first; i++) {
    cells += `<div class="cal-day other-month"></div>`;
  }
  for (let d = 1; d <= days; d++) {
    const isToday = d === today.getDate() && calMonth === today.getMonth() + 1 && calYear === today.getFullYear();
    const dayEvents = visibleEvents().filter(e => {
      const s = new Date(e.start);
      return s.getFullYear() === calYear && s.getMonth() + 1 === calMonth && s.getDate() === d;
    });
    const visible = dayEvents.slice(0, 2);
    const extra   = dayEvents.length - visible.length;
    const evHtml  = visible.map(e => {
      const cls = e.status === 'predicted' ? 'predicted' : e.status === 'tentative' ? 'tentative' : '';
      return `<div class="cal-event ${cls}" title="${esc(e.title)}">${esc(e.title)}</div>`;
    }).join('') + (extra > 0 ? `<div class="cal-more">+${extra} more</div>` : '');

    const isHighlighted = highlightedTitle && dayEvents.some(e => e.title === highlightedTitle);
    cells += `<div class="cal-day${isToday ? ' today' : ''}${isHighlighted ? ' highlighted' : ''}" onclick="openModal(${d})">
      <div class="cal-day-num">${d}</div>${evHtml}
    </div>`;
  }
  grid.innerHTML = cells;
}

function changeMonth(delta) {
  calMonth += delta;
  if (calMonth > 12) { calMonth = 1;  calYear++; }
  if (calMonth < 1)  { calMonth = 12; calYear--; }
  renderCalHeader();
  loadEvents();
}

async function syncCal() {
  const btn = document.getElementById('sync-btn');
  btn.disabled = true;
  try {
    btn.textContent = 'Syncing…';
    await fetch(`${API}/sync`, { method: 'POST' });
    btn.textContent = 'Predicting…';
    await fetch(`${API}/predict`, { method: 'POST' });
    await loadEvents();
  } finally {
    btn.disabled = false;
    btn.textContent = 'Sync';
  }
}

async function clearTentative() {
  const btn = document.getElementById('clear-tentative-btn');
  btn.disabled = true;
  try {
    await fetch(`${API}/events/clear-tentative`, { method: 'POST' });
    await loadEvents();
  } finally {
    btn.disabled = false;
  }
}

async function clearPredicted() {
  const btn = document.getElementById('clear-predicted-btn');
  btn.disabled = true;
  try {
    await fetch(`${API}/events/clear-predicted`, { method: 'POST' });
    await loadEvents();
  } finally {
    btn.disabled = false;
  }
}

function selectTentative(i) {
  document.querySelectorAll('.modal-event.tentative').forEach(el => el.classList.remove('selected'));
  document.getElementById(`mev-${i}`).classList.add('selected');
}

// ── Day modal ──────────────────────────────────────────────────────────────

let _modalEvents = [];

function openModal(day) {
  _modalEvents = visibleEvents().filter(e => {
    const s = new Date(e.start);
    return s.getFullYear() === calYear && s.getMonth() + 1 === calMonth && s.getDate() === day;
  });

  document.getElementById('modal-title').textContent = `${MONTHS[calMonth - 1]} ${day}, ${calYear}`;

  const dotColor = e => {
    if (e.status === 'predicted') return '#7c3aed';
    if (e.status === 'tentative') return '#f59e0b';
    return '#2563eb';
  };
  const typeLabel = e => {
    if (e.status === 'predicted') return 'Predicted';
    if (e.status === 'tentative') return 'Tentative';
    return 'Confirmed';
  };

  document.getElementById('modal-body').innerHTML = _modalEvents.length
    ? _modalEvents.map((e, i) => {
        const actions = e.status === 'tentative'
          ? `<button class="btn btn-success modal-confirm-schedule-btn" onclick="confirmCandidateFromModal(${i})">Confirm</button>`
          : e.status === 'predicted'
          ? `<div class="modal-remove-wrap" style="display:flex;gap:0.4rem;align-items:center">
               <button class="btn btn-success modal-confirm-schedule-btn" onclick="confirmPredicted(${i})" title="Add to Google Calendar">Confirm</button>
               <button class="modal-remove-btn" onclick="askRemove(${i})" title="Remove">&#10005;</button>
               <span class="modal-confirm-row" id="confirm-${i}" style="display:none">
                 <button class="modal-confirm-btn" onclick="removeEvent(${i})" title="Confirm delete">&#10003;</button>
                 <button class="modal-cancel-btn" onclick="cancelRemove(${i})" title="Cancel">&#8592;</button>
               </span>
             </div>`
          : `<div class="modal-remove-wrap">
               <button class="modal-remove-btn" onclick="askRemove(${i})" title="Remove">&#10005;</button>
               <span class="modal-confirm-row" id="confirm-${i}" style="display:none">
                 <button class="modal-confirm-btn" onclick="removeEvent(${i})" title="Confirm delete">&#10003;</button>
                 <button class="modal-cancel-btn" onclick="cancelRemove(${i})" title="Cancel">&#8592;</button>
               </span>
             </div>`;
        const tentativeCls = e.status === 'tentative' ? ' tentative' : '';
        const tentativeClick = e.status === 'tentative' ? `onclick="selectTentative(${i})"` : '';
        return `
          <div class="modal-event${tentativeCls}" id="mev-${i}" ${tentativeClick}>
            <div class="modal-dot" style="background:${dotColor(e)}"></div>
            <div class="modal-event-info">
              <div class="modal-event-title">${esc(e.title)}</div>
              <div class="modal-event-time">${fmtTime(e.start)} – ${fmtTime(e.end)}</div>
              <div class="modal-event-type">${typeLabel(e)}</div>
            </div>
            ${actions}
          </div>`;
      }).join('')
    : `<div class="modal-empty">No events</div>`;

  document.getElementById('modal-backdrop').classList.add('open');
}

async function confirmPredicted(i) {
  const e = _modalEvents[i];
  const res = await fetch(`${API}/events/confirm-predicted`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id: e.id }),
  });
  const data = await res.json();
  if (data.error) { setStatus(`Error: ${data.error}`, 'error'); return; }
  document.getElementById('modal-backdrop').classList.remove('open');
  loadEvents();
}

async function confirmCandidateFromModal(i) {
  const e = _modalEvents[i];
  const c = calCandidates.find(c => c.title === e.title && c.start === e.start);
  if (!c) { setStatus('Session expired — please re-analyze.', 'error'); return; }
  await confirmCandidate(e.title, c.slotIndex);
}

async function confirmCandidate(title, slotIndex) {
  const res = await fetch(`${API}/confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, slot_index: slotIndex }),
  });
  const data = await res.json();
  if (data.error) { setStatus(`Error: ${data.error}`, 'error'); return; }
  document.getElementById('modal-backdrop').classList.remove('open');
  clearCandidates(title);
  const el = document.getElementById(`pending-${CSS.escape(title)}`);
  if (el) el.remove();
  if (!calCandidates.length) setStatus('', '');
  loadEvents();
}

function closeModal(e) {
  if (e && e.target !== document.getElementById('modal-backdrop')) return;
  document.getElementById('modal-backdrop').classList.remove('open');
}

function askRemove(i) {
  document.querySelector(`#mev-${i} .modal-remove-btn`).style.display = 'none';
  document.getElementById(`confirm-${i}`).style.display = 'inline-flex';
}

function cancelRemove(i) {
  document.getElementById(`confirm-${i}`).style.display = 'none';
  document.querySelector(`#mev-${i} .modal-remove-btn`).style.display = '';
}

async function removeEvent(i) {
  const e = _modalEvents[i];
  await fetch(`${API}/events/remove`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id: e.id }),
  });
  document.getElementById('modal-backdrop').classList.remove('open');
  await loadEvents();
}

function fmtTime(iso) {
  return new Date(iso).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
}
