# Virtual Desktop GUI Screenshots

- Purpose: configure the DBN machine for repeatable virtual desktop sessions so we can grab GUI screenshots with minimal friction.
- Tooling: install and/or configure the VFC/W CLI (virtual frame capture) that can launch the VM display, keep it alive, and expose it for automation.
- Workflow: document how to start the virtual desktop, attach to it, and run the screenshot capture command (e.g., `vfc-w capture --output ...`) along with any environment variables or SSH tunnels needed.
- Outputs: decide where to land captures, how to name them, and how to refresh the session if it stalls.
- Next steps: add scripts/aliases that wrap the CLI so taking a new screen is `./projects/virtual-desktop-gui/bin/capture` and note any follow-up automation.
