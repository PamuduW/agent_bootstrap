# Base templates

Canonical `AGENTS.md` and `CLAUDE.md` templates for **Agentbot**.

These files are live templates (not stubs). `agentbot boot` copies them into the current repo:

- `AGENTS.md` — environment header, runtime skill-discovery policy, interaction rules, orchestration convention, and a `## Project` overlay section for repo-specific notes.
- `CLAUDE.md` — minimal pointer that imports `@AGENTS.md` (Claude Code) and instructs agents to read AGENTS.md first.

Machine-level baseline remains at `global/AGENTS.md`. Per-repo overlays are scaffolded from `base/` via `agentbot boot`; re-render the global baseline with `./install.sh global`.
