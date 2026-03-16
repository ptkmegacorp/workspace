# MEMORY.md

- Handoff note: we just built/organized the **mothership** project at `/home/bot/mothership`.
- `home.local` now serves from mothership and acts as the module index.
- Useful follow-up: if modules/aliases change, update `modules.json` and run `node /home/bot/mothership/sync-proxy.js`.
- Handoff update (2026-03-09): `telegram-ai-harness` now includes `telegram-lil-byte-add-on`, `oauth-broker`, and `emoji-factory`; MCP-style routing v1 uses two endpoints (`system_info`, `project_recent`) with small local qwen defaults.
- Major build update (2026-03-13): We promoted `run(command)` as the default CLI orchestration pattern and shipped it as first-class OpenClaw tooling (`openclaw_unix_harness_run` / `openclaw_unix_harness_health`). This became the core execution substrate for agent work.
- Expansion milestone (2026-03-13): After user discussion about token efficiency and HTML extraction, we extended the Unix harness into a DOM harness command family (`dom query`, `dom find-text`, `dom extract links`, `dom snapshot`, `dom pick`, `dom near`, `dom diff`, `dom path`, `dom glance`) with local-only Act mode for local services.
- Safety model decision (2026-03-13): Keep UX elegant; Class B no extra “are you sure” barrier, while Class C requires explicit confirm flag + `confirmSure` double-check. VM backend remains optional/plugin-path for future hardening, not required for current personal setup.
- Observability decision (2026-03-13): Standardized toward a canonical harness trace file (`/home/bot/harness-logs/run-trace.jsonl`) as single source of truth for usage/scoreboard metrics.
- Product surface update (2026-03-13): Added a compact unix harness scoreboard section to `home.local`, including top tool calls and first-100-use estimates, plus agent-only reminders to prefer `run(command)` + DOM tools before broad page dumps.
