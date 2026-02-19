#!/usr/bin/env python3
"""
Sexy OpenClaw Subagent Dash - Real-time session monitor TUI
"""

import argparse
import subprocess
import curses
import time
import re
from datetime import datetime

__version__ = "1.0"

def get_sessions():
    """Run openclaw sessions list and parse output."""
    try:
        result = subprocess.run(
            ["openclaw", "sessions", "list"],
            capture_output=True,
            text=True,
            timeout=5
        )
        output = result.stdout
        lines = output.strip().split("\n")
        sessions = []
        # Skip header lines (first few lines until "Kind")
        start = 0
        for i, line in enumerate(lines):
            if line.startswith("Kind"):
                start = i + 1
                break
        for line in lines[start:]:
            if not line.strip():
                continue
            # Parse line: Kind   Key                        Age       Model          Tokens (ctx %)       Flags
            # Example: direct agent:main:main            5m ago    MiniMax-M2.5   26k/200k (13%)       system id:b14b1914-2432-4f59-bf23-542fcbd72b0f
            parts = line.split()
            if len(parts) >= 5:
                kind = parts[0]
                key = parts[1]
                age = parts[2] if len(parts) > 2 else ""
                model = parts[3] if len(parts) > 3 else ""
                tokens = parts[4] if len(parts) > 4 else ""
                # The rest is flags (maybe combined)
                flags = " ".join(parts[5:]) if len(parts) > 5 else ""
                sessions.append({
                    "kind": kind,
                    "key": key,
                    "age": age,
                    "model": model,
                    "tokens": tokens,
                    "flags": flags
                })
        return sessions
    except Exception as e:
        return [{"kind": "error", "key": str(e), "age": "", "model": "", "tokens": "", "flags": ""}]

def draw_dash(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(1)
    stdscr.timeout(1000)
    
    # Colors
    curses.start_color()
    curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(5, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
    
    while True:
        stdscr.clear()
        h, w = stdscr.getmaxyx()
        
        # Title
        title = " Sexy OpenClaw Subagent Dash "
        stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
        stdscr.addstr(0, (w - len(title)) // 2, title)
        stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)
        
        # Timestamp
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        stdscr.addstr(0, w - len(ts) - 1, ts)
        
        # Get sessions
        sessions = get_sessions()
        
        # Header
        stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
        header = f"{'Kind':<8} {'Key':<30} {'Age':<10} {'Model':<18} {'Tokens':<15} Flags"
        stdscr.addstr(2, 2, header)
        stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
        
        # Draw sessions
        y = 3
        for sess in sessions:
            if y >= h - 2:
                break
            if sess["kind"] == "error":
                stdscr.attron(curses.color_pair(4))
                stdscr.addstr(y, 2, f"Error: {sess['key']}")
                stdscr.attroff(curses.color_pair(4))
            else:
                # Color by kind
                if sess["kind"] == "direct":
                    color = curses.color_pair(3)
                elif "subagent" in sess["key"]:
                    color = curses.color_pair(5)
                elif "cron" in sess["key"]:
                    color = curses.color_pair(2)
                else:
                    color = curses.color_pair(1)
                
                stdscr.attron(color)
                line = f"{sess['kind']:<8} {sess['key']:<30} {sess['age']:<10} {sess['model']:<18} {sess['tokens']:<15} {sess['flags']}"
                stdscr.addstr(y, 2, line[:w-3])
                stdscr.attroff(color)
            y += 1
        
        # Footer
        stdscr.attron(curses.color_pair(1))
        footer = "Press 'q' to quit | Auto-refreshes every 2s"
        stdscr.addstr(h-1, (w - len(footer)) // 2, footer)
        stdscr.attroff(curses.color_pair(1))
        
        stdscr.refresh()
        
        # Input handling
        key = stdscr.getch()
        if key == ord('q'):
            break
        
        # Sleep for 2 seconds total (we have 1s timeout, so do 2 loops)
        time.sleep(1)

def main():
    parser = argparse.ArgumentParser(description="Sexy OpenClaw Subagent Dash - Real-time session monitor TUI")
    parser.add_argument("--version", action="version", version=f"Sexy OpenClaw Dash v{__version__}")
    parser.parse_args()
    curses.wrapper(draw_dash)

if __name__ == "__main__":
    main()
