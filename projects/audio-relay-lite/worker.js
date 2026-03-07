#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);

const QUEUE_DIR = process.env.QUEUE_DIR || '/tmp/audio-relay-lite/queue';
const ARCHIVE_DIR = process.env.ARCHIVE_DIR || '/tmp/audio-relay-lite/archive';
const WHISPER_MODEL = process.env.WHISPER_MODEL || 'tiny.en';
// wake phrase gating removed (always forward transcripts)
const OPENCLAW_REPLY_CHANNEL = process.env.OPENCLAW_REPLY_CHANNEL || 'telegram';
const OPENCLAW_REPLY_TO = process.env.OPENCLAW_REPLY_TO || '';
const OPENCLAW_BIN = process.env.OPENCLAW_BIN || '/home/bot/.npm-global/bin/openclaw';
const OPENCLAW_FORWARD_MODE = process.env.OPENCLAW_FORWARD_MODE || 'agent_only';
const EVENTS_FILE = process.env.EVENTS_FILE || '/tmp/audio-relay-lite/events.jsonl';

fs.mkdirSync(QUEUE_DIR, { recursive: true });
fs.mkdirSync(ARCHIVE_DIR, { recursive: true });

function log(msg) { console.log(`[worker] ${msg}`); }

function appendEvent(evt) {
  const line = JSON.stringify({ ts: Date.now(), ...evt }) + '\n';
  fs.appendFileSync(EVENTS_FILE, line);
}

async function transcribe(file) {
  const py = [
    'import sys',
    'from faster_whisper import WhisperModel',
    `m=WhisperModel("${WHISPER_MODEL}", device="cpu", compute_type="int8")`,
    'segments,info=m.transcribe(sys.argv[1], beam_size=5, vad_filter=False, condition_on_previous_text=False)',
    'print(" ".join([s.text.strip() for s in segments if s.text.strip()]))',
  ].join('; ');
  const { stdout } = await execFileAsync('python3', ['-c', py, file], { timeout: 120000, maxBuffer: 1024 * 1024 });
  return String(stdout || '').trim();
}

async function forwardToOpenClaw(text) {
  const env = { ...process.env, PATH: `/home/bot/.npm-global/bin:${process.env.PATH || ''}` };

  if (OPENCLAW_FORWARD_MODE === 'message_send') {
    if (!OPENCLAW_REPLY_TO) throw new Error('OPENCLAW_REPLY_TO missing for message_send mode');
    const args = [
      'message', 'send',
      '--channel', OPENCLAW_REPLY_CHANNEL,
      '--target', OPENCLAW_REPLY_TO,
      '--message', text,
    ];
    const { stdout } = await execFileAsync(OPENCLAW_BIN, args, { timeout: 90000, maxBuffer: 1024 * 1024, env });
    return String(stdout || '').trim();
  }

  // default: keep relay isolated in OpenClaw session flow (no direct Telegram delivery)
  const args = [
    'agent', '--agent', 'main',
    '--message', text,
    '--timeout', '45',
  ];
  const { stdout } = await execFileAsync(OPENCLAW_BIN, args, { timeout: 90000, maxBuffer: 1024 * 1024, env });
  return String(stdout || '').trim();
}

let busy = false;
async function tick() {
  if (busy) return;
  busy = true;
  let file = '';
  try {
    const files = fs.readdirSync(QUEUE_DIR)
      .filter((f) => f.endsWith('.wav'))
      .sort()
      .map((f) => path.join(QUEUE_DIR, f));

    if (files.length === 0) return;
    file = files[0];
    log(`processing ${path.basename(file)}`);

    const text = await transcribe(file);
    log(`TRANSCRIPT >>> ${text || '(empty)'}`);

    if (text) {
      const rawReply = await forwardToOpenClaw(text);
      const reply = (rawReply || '').trim();
      if (reply) log(`REPLY <<< ${reply}`);
      log('forwarded -> openclaw');
      appendEvent({ type: 'chat', transcript: text, reply });
    } else {
      appendEvent({ type: 'chat', transcript: '', reply: '' });
    }

    const dest = path.join(ARCHIVE_DIR, path.basename(file));
    fs.renameSync(file, dest);
  } catch (e) {
    log(`error: ${e.message}`);
    appendEvent({ type: 'error', error: e.message });
    try {
      if (file && fs.existsSync(file)) {
        const failed = path.join(ARCHIVE_DIR, path.basename(file, '.wav') + '.failed.wav');
        fs.renameSync(file, failed);
        log(`moved to archive as failed: ${path.basename(failed)}`);
      }
    } catch {}
  } finally {
    busy = false;
  }
}

log('ready (queue polling every 1s)');
setInterval(tick, 1000);
