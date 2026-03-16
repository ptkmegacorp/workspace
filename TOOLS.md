
## Default CLI Path (Run First)

For local CLI work, prefer `run(command)` (OpenClaw Unix harness) before ad-hoc shell execution.

Examples:
- `run("ls -la /home/bot/mothership")`
- `run("grep -RIn 'mgrep' /home/bot/openclaw-unix-harness-tool/src")`
- `run("dom query --url http://home.local --selector '.scoreboard-block'")`

Common run-first recipes (thin wrappers by convention):
- Code search: `run("mgrep -r 'query' /path")`
- Fast endpoint check: `run("curl -s http://127.0.0.1:3096/api/harness-scoreboard")`
- DOM inspect: `run("dom glance --url http://home.local")`
- Index refresh: `run("mgrep index /path --status")`

Use raw `exec` only for process/session control or service-management edge cases.

# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

### CLI Tools (Global)

- `agent-browser` installed globally via npm (`/usr/bin/agent-browser`)
- Install/update:
  - `sudo npm install -g agent-browser`
  - `agent-browser install --with-deps`
- Quick smoke test:
  - `agent-browser open https://example.com`
  - `agent-browser get title`
  - `agent-browser snapshot`
  - `agent-browser close`

### Moltbook

- Username: byte-bot
- API Key: moltbook_sk_DIr0ePRX4HyzEjrnKYT28AHmm0OJpej4
