# Sexy OpenClaw Subagent Dash

A real-time TUI (Terminal User Interface) that displays OpenClaw session info - main agent and subagents - in a sleek dashboard.

## Features

- Real-time monitoring of OpenClaw sessions
- Auto-refreshes every 2 seconds
- Color-coded by session type (main, subagent, cron)
- Shows key info: Kind, Key, Age, Model, Tokens, Flags

## Installation

```bash
# Ensure you have Python 3 and curses
# Install OpenClaw CLI (requires Node >=22)
openclaw --help

# Run the dash
python3 dash.py
```

## Usage

```bash
python3 dash.py
```

Controls:
- Press `q` to quit
- Auto-refreshes every 2 seconds

## Requirements

- Python 3
- curses (included with Python on most systems)
- OpenClaw CLI (`openclaw sessions list`)
- Node.js >=22 (for OpenClaw CLI)

## Demo

![Demo](https://example.com/demo.gif) (optional)
