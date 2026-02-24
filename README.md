# Workspace Projects

This workspace keeps each major project entirely inside its own directory so the context, scripts, documentation, and helpers stay grouped together. When a project touches code, docs, skills, or scripts, place all of that work under `projects/<project-name>` (or a dedicated subfolder there) instead of scattering files across `scripts/` or other top-level directories.

Example: the `always-on-mic` project now lives under `projects/always-on-mic`, with its pipeline docs, implementation notes, task list, and executable helpers all co-located. The only remaining exception is shared tooling (e.g., CLI utilities) that truly belong to the general workspace rather than a single project.

Keep this pattern in mind whenever you start a new feature so your work stays self-contained and easy to reference later.