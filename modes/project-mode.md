# Project Mode

**Toggle: enabled**
**Display mode: enabled**

## Project Mode Toggle enabled
- use scripts/shared-tmux/shared-tmux-project-mode.sh --sync-tree
- execute cmds within the shared-tmux-work session
- display relative project tree in shared-tmux-tree session
- shared-tmux-tree should mirror the relevent directories that shared-tmux-work is currently in. they are paired
- 'zoom in' means shared-tmux-tree narrows to the active dir, 'zoom out' means expand to workspace root dir
- these 2 tmux sessions is default, one for active cli work, the other for relevant tree info
- if there are existing tmux sessions active that reflect this, use them. 

## Display mode: enabled
- when display mode is enabled use uxterm on your dipslay in real time. 
- all Project Mode toggle enabled rules listed above are relevent here. 

