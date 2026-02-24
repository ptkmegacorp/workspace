# Project Mode

When this mode is enabled, focus your context exclusively on the currently assigned project and ignore unrelated topics. The default behavior is to display your work inside our shared tmux terminal so the user can watch what you’re doing. For example, once you finish a requested update, show the diff or changed contents directly in that tmux session before reporting back. To keep the flow clear, use two tmux windows:
```
Window 1 (work): commands, edits, diffs you’re actually running (attach via the `tmux-work` alias).
Window 2 (project-tree): `tree` / repo overview so the structure is always visible (`tmux-tree`).
```
Enable mouse support (`tmux setw -g mouse on`) in the session so the status line window names act like clickable targets when your terminal allows it. Start the shared session with `start-tmux`, switch windows via the tmux aliases, and stop everything cleanly with `stop-tmux` when you’re done. This note should stay concise: enable the mode → narrow your scope to that project only.
