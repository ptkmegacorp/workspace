#!/usr/bin/env node
import { spawn } from 'node:child_process';
import fs from 'node:fs';

const QUEUE_DIR = process.env.QUEUE_DIR || '/tmp/audio-relay-lite/queue';
const TMP_DIR = process.env.TMP_DIR || '/tmp/audio-relay-lite/tmp';
const SOURCE_ENV = process.env.AUDIO_RELAY_SOURCE || '';
const DOUBLE_TAP_MS = Number(process.env.DOUBLE_TAP_MS || 450);

fs.mkdirSync(QUEUE_DIR, { recursive: true });
fs.mkdirSync(TMP_DIR, { recursive: true });

let lastCtrlAt = 0;
let recProc = null;
let recPathTmp = '';
let recPathFinal = '';

function ts() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}${p(d.getMonth()+1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`;
}

function log(msg) {
  console.log(`[rec] ${msg}`);
}

function discoverPulseSource() {
  if (SOURCE_ENV) return SOURCE_ENV;
  try {
    const out = spawn('pactl', ['list', 'short', 'sources'], { stdio: ['ignore', 'pipe', 'ignore'] });
    let data = '';
    out.stdout.on('data', (b) => { data += String(b); });
    return new Promise((resolve) => {
      out.on('exit', () => {
        const lines = data.split(/\r?\n/).filter(Boolean);
        // prefer true input devices, avoid .monitor
        for (const line of lines) {
          const cols = line.split('\t');
          const name = cols[1] || '';
          if (name.includes('.monitor')) continue;
          if (name.includes('input')) return resolve(name);
        }
        for (const line of lines) {
          const cols = line.split('\t');
          const name = cols[1] || '';
          if (!name.includes('.monitor')) return resolve(name);
        }
        resolve('default');
      });
    });
  } catch {
    return Promise.resolve('default');
  }
}

async function startRec() {
  const id = `manual-${ts()}`;
  recPathTmp = `${TMP_DIR}/${id}.wav`;
  recPathFinal = `${QUEUE_DIR}/${id}.wav`;
  const source = await discoverPulseSource();

  recProc = spawn('ffmpeg', [
    '-hide_banner','-loglevel','error','-nostdin',
    '-f','pulse','-i', source,
    '-ac','1','-ar','16000','-c:a','pcm_s16le',
    recPathTmp,
  ], { stdio: ['ignore','pipe','pipe'] });

  recProc.stderr.on('data', () => {});
  log(`REC START -> ${recPathTmp} (source=${source})`);
}

function stopRec() {
  if (!recProc) return;
  const p = recProc;
  recProc = null;
  p.kill('SIGINT');
  p.on('exit', () => {
    try {
      if (fs.existsSync(recPathTmp) && fs.statSync(recPathTmp).size > 2048) {
        fs.renameSync(recPathTmp, recPathFinal);
        log(`REC STOP -> QUEUED: ${recPathFinal}`);
      } else {
        if (fs.existsSync(recPathTmp)) fs.unlinkSync(recPathTmp);
        log('REC STOP -> DROPPED (too short)');
      }
    } catch (e) {
      log(`REC STOP error: ${e.message}`);
    }
  });
}

async function toggle() {
  if (recProc) stopRec(); else await startRec();
}

async function handleCtrlPress() {
  const now = Date.now();
  if (now - lastCtrlAt <= DOUBLE_TAP_MS) {
    await toggle();
    lastCtrlAt = 0;
  } else {
    lastCtrlAt = now;
  }
}

function discoverKeyboardEventDevice() {
  try {
    const txt = fs.readFileSync('/proc/bus/input/devices', 'utf8');
    const blocks = txt.split(/\n\n+/);

    const candidates = [];
    for (const b of blocks) {
      const name = (b.match(/N: Name="([^"]+)"/) || [,''])[1];
      const handlers = (b.match(/H: Handlers=([^\n]+)/) || [,''])[1];
      const ev = (b.match(/B: EV=([^\n]+)/) || [,''])[1];
      const eventMatch = handlers.match(/\bevent\d+\b/);
      if (!eventMatch) continue;

      const lname = name.toLowerCase();
      const looksBad = lname.includes('power button') || lname.includes('video bus') || lname.includes('pc speaker');
      const looksKeyboard = lname.includes('keyboard') || handlers.includes('kbd');
      if (!looksKeyboard || looksBad) continue;

      let score = 0;
      if (lname.includes('usb')) score += 5;
      if (lname.includes('keyboard')) score += 3;
      if (handlers.includes('sysrq')) score += 2;
      if (ev && ev !== '3') score += 1;

      candidates.push({ dev: `/dev/input/${eventMatch[0]}`, name, handlers, score });
    }

    candidates.sort((a, b) => b.score - a.score);
    if (candidates.length) return candidates[0].dev;
  } catch {}
  return '';
}

function runXevFallback() {
  log('Listening for double-tap Ctrl via xev fallback...');
  const xev = spawn('xev', ['-event', 'keyboard', '-root'], { stdio: ['ignore', 'pipe', 'pipe'] });
  let pending = false;

  xev.stdout.on('data', (buf) => {
    const lines = String(buf).split(/\r?\n/);
    for (const line of lines) {
      if (line.includes('KeyPress event')) {
        pending = true;
        continue;
      }
      if (pending && line.includes('keysym')) {
        const isCtrl = line.includes('Control_L') || line.includes('Control_R');
        pending = false;
        if (isCtrl) {
          void handleCtrlPress();
        }
        continue;
      }
      if (line.includes('KeyPress') && (line.includes('Control_L') || line.includes('Control_R'))) {
        void handleCtrlPress();
        pending = false;
      }
    }
  });

  xev.on('exit', (code) => {
    log(`xev exited (${code}).`);
    process.exit(code || 0);
  });

  process.on('SIGINT', () => {
    if (recProc) stopRec();
    try { xev.kill('SIGTERM'); } catch {}
    process.exit(0);
  });
}

function runEvtest() {
  const dev = process.env.AUDIO_RELAY_INPUT_DEVICE || discoverKeyboardEventDevice();
  if (!dev) {
    log('No keyboard input device found for evtest; falling back to xev');
    runXevFallback();
    return;
  }

  log(`Listening for double-tap Ctrl via evtest on ${dev} ...`);
  const p = spawn('sudo', ['evtest', dev], { stdio: ['ignore', 'pipe', 'pipe'] });

  const onData = (buf) => {
    const lines = String(buf).split(/\r?\n/);
    for (const line of lines) {
      if (!line.includes('EV_KEY')) continue;
      if (!(line.includes('KEY_LEFTCTRL') || line.includes('KEY_RIGHTCTRL'))) continue;
      if (!line.includes('value 1')) continue; // key down only
      void handleCtrlPress();
    }
  };

  p.stdout.on('data', onData);
  p.stderr.on('data', onData);

  p.on('exit', (code) => {
    log(`evtest exited (${code}); falling back to xev`);
    runXevFallback();
  });

  process.on('SIGINT', () => {
    if (recProc) stopRec();
    try { p.kill('SIGTERM'); } catch {}
    process.exit(0);
  });
}

runEvtest();
