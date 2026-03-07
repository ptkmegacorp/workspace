#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';

const ROOT = '/home/bot/.openclaw/workspace/projects/audio-relay-lite';
const PUBLIC = path.join(ROOT, 'public');
const STATE_FILE = '/tmp/audio-relay-lite/state.json';
const EVENTS_FILE = '/tmp/audio-relay-lite/events.jsonl';
const PORT = Number(process.env.WEB_PORT || 3092);

function send(res, code, obj) {
  res.writeHead(code, { 'content-type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(obj));
}

function serveStatic(req, res) {
  const p = req.url === '/' ? '/index.html' : req.url;
  const fp = path.join(PUBLIC, p);
  if (!fp.startsWith(PUBLIC) || !fs.existsSync(fp)) {
    res.writeHead(404); res.end('not found'); return;
  }
  const ext = path.extname(fp);
  const ct = ext === '.html' ? 'text/html; charset=utf-8' : ext === '.js' ? 'text/javascript; charset=utf-8' : 'text/css; charset=utf-8';
  res.writeHead(200, { 'content-type': ct });
  fs.createReadStream(fp).pipe(res);
}

const server = http.createServer((req, res) => {
  if (req.url.startsWith('/api/state')) {
    let st = { recording: false, status: 'unknown' };
    try { st = JSON.parse(fs.readFileSync(STATE_FILE, 'utf8')); } catch {}
    return send(res, 200, st);
  }

  if (req.url.startsWith('/api/events')) {
    const u = new URL(req.url, 'http://localhost');
    const after = Number(u.searchParams.get('after') || 0);
    const out = [];
    try {
      const lines = fs.readFileSync(EVENTS_FILE, 'utf8').split(/\r?\n/).filter(Boolean);
      for (const line of lines) {
        const e = JSON.parse(line);
        if ((e.ts || 0) > after) out.push(e);
      }
    } catch {}
    return send(res, 200, { events: out });
  }

  serveStatic(req, res);
});

server.listen(PORT, () => console.log(`audio-relay-lite web on http://127.0.0.1:${PORT}`));
