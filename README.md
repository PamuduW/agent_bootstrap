# agent_bootstrap

Private source-of-truth for my agent instructions.

## How I use this

### Global (Codex)
- Copy `global/AGENTS.md` to `~/.codex/AGENTS.md`
- Codex loads global instructions from its Codex home (default `~/.codex`, or `CODEX_HOME` if set), then layers project instructions from the repo root down to the current working directory. Closest file wins. 

### Project-specific
- Copy `specific/<project>/AGENTS.md` to the project root as `AGENTS.md`

### New project
- Copy `templates/AGENTS.md` to the project root as `AGENTS.md`
- Optionally copy `templates/.codexignore` to the project root as `.codexignore`

## Quick verification (Codex)
- In Codex, use `/status` and `/debug-config` to confirm model, approvals, workspace root, and config layers.
- Use `/permissions` to switch between Auto and Read Only.
- Use `/compact` after long sessions to keep context lean.