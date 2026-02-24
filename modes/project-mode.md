# Project Mode

When this mode is enabled, focus your context exclusively on the currently assigned project and ignore unrelated topics. The default behavior is to display your work inside our shared tmux terminal so the user can watch what you’re doing. For example, once you finish a requested update, show the diff or changed contents directly in that tmux session before reporting back. To keep the flow clear, use two tmux windows:
```
Window 1 (work): commands, edits, diffs you’re actually running.
Window 2 (project-tree): `tree` / repo overview so the structure is always visible.
```
Attach to the default work window with `tmux -S /tmp/shared-tmux.sock attach -t shared-tmux` and switch to the project-tree window via `tmux -S /tmp/shared-tmux.sock select-window -t shared-tmux:project-tree` whenever you’d like to keep the tree in view.
This note should stay concise: enable the mode → narrow your scope to that project only.
