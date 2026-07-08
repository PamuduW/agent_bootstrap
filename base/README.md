# Base templates

Canonical `AGENTS.md` and `CLAUDE.md` templates for **agentboot**.

These files are live templates (not stubs). `agentboot` copies them into the current repo:

- `AGENTS.md` — environment header, phase-based skill tables, interaction rules, orchestration convention, and a `## Project` overlay section for repo-specific notes.
- `CLAUDE.md` — minimal pointer that imports `@AGENTS.md` (Claude Code) and instructs agents to read AGENTS.md first.

Machine-level baseline remains at `global/AGENTS.md`. Per-repo overlays are rendered via `templates/AGENTS.md` and the control plane in `src/`.
