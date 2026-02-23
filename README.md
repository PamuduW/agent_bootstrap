# agent_bootstrap

Single private source of truth for my coding-agent instructions.

## How I use this

### Codex (global)
Copy:
- `global/AGENTS.md` -> `~/.codex/AGENTS.md`

Codex reads global instructions from its home and then loads project instructions from `AGENTS.md` files from repo root down to the current working directory.

### Any project (project-specific)
Copy:
- `specific/<project>/AGENTS.md` -> `<project-root>/AGENTS.md`

### New project (template)
Copy:
- `templates/AGENTS.md` -> `<project-root>/AGENTS.md`
- `templates/.codexignore` -> `<project-root>/.codexignore` (optional)

## Update flow
- Edit files here first.
- Re-copy into `~/.codex/` and/or the target repo when they change.