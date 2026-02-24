# Project Mode

When this mode is enabled, focus your context exclusively on the currently assigned project and ignore unrelated topics. The default behavior is to keep two shared tmux sessions so the user can watch your work drive while the repo tree stays visible. For example, once you finish a requested update, show the diff or changed contents directly in the `tmux-work` session before reporting back. To keep the flow clear, keep both sessions open:
```
Session 1 (work): commands, edits, diffs you’re actually running (attach via the `tmux-work` alias or the `show work` instruction).
Session 2 (tree): `tree` / repo overview so the structure is always visible (`tmux-tree` or `show tree`).
```
`show work <file>` means attach to the work session and open the specified file with `vim` so you can scroll/look while you keep it active. `show tree` means attach to the tree session. Start the shared sessions with `start-tmux`, switch or click via the tmux aliases, and stop everything cleanly with `stop-tmux` when you’re done. This note should stay concise: enable the mode → narrow your scope to that project only.
Work live test editWork live test edit
