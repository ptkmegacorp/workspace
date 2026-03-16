# OpenClaw Harness – Run‑First Promotion

## Goal
Make `run(<command>)` the default and recommended way to execute any CLI‑style task.

## Quick‑Start

```bash
# Basic CLI work
run("ls -la /home/bot/mothership")

# Search with mgrep
run("mgrep -r \"query\" /path/to/code")

# DOM inspection
run("dom query --url http://home.local --selector '.scoreboard-block'")

# Run any pipeline safely
run("grep foo file.txt | sort | uniq")
```

### Why use `run(...)`?
- **Automatic policy enforcement** – respects Class A/B/C rules
- **Audit‑ready** – logs run‑vs‑exec escapes on the scoreboard
- **Safety net** – prevents accidental destructive or external commands
- **Consistent output** – always returns structured `{ok, exitCode, output, ...}` 

### When you *must* use raw `exec` / `process`
Only for genuine edge cases (service management, long‑running daemons, etc.).  
You **must**:
1. Add the required flag (`confirmSure=true`, `confirmDelete=true`, etc.)
2. Immediately log a short reason in `memory/exec-escapes.log`
3. Return to `run(...)` for subsequent work

### Promotion Highlights
- Documentation now leads with `run(...)` examples
- Scoreboard shows `runVsExec24h` ratio (currently `37:0`)
- All new code snippets in TOOLS.md start with `run(...)`
- Built‑in aliases in the shell hint (`r(...)`) – see `alias.txt`

### Alias shortcut (optional)

Add this to your shell profile for a quick alias:

```bash
alias r='run'
```

Now `r("cmd")` works exactly like `run("cmd")`.

---

**All new tutorials, code samples, and help messages now start with `run(...)` to reinforce the habit.** 