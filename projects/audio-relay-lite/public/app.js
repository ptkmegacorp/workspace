const statusEl = document.getElementById('status');
const left = document.getElementById('left');
const right = document.getElementById('right');
let afterTs = 0;

function addBubble(col, text, cls) {
  const d = document.createElement('div');
  d.className = `bubble ${cls}`;
  d.textContent = text || '(empty)';
  const t = document.createElement('div');
  t.className = 'small';
  t.textContent = new Date().toLocaleTimeString();
  d.appendChild(t);
  col.appendChild(d);
  col.scrollTop = col.scrollHeight;
}

async function pollState() {
  try {
    const s = await fetch('/api/state').then(r=>r.json());
    statusEl.textContent = `${s.recording ? '🔴 recording' : '⚪ idle'} · ${s.status || 'unknown'}`;
  } catch {
    statusEl.textContent = 'state unavailable';
  }
}

async function pollEvents() {
  try {
    const r = await fetch(`/api/events?after=${afterTs}`).then(x=>x.json());
    for (const e of (r.events || [])) {
      afterTs = Math.max(afterTs, e.ts || 0);
      if (e.type === 'chat') {
        if (e.transcript) addBubble(right, e.transcript, 'r');
        if (e.reply) addBubble(left, e.reply, 'l');
      }
    }
  } catch {}
}

setInterval(pollState, 1000);
setInterval(pollEvents, 1000);
pollState();
pollEvents();
