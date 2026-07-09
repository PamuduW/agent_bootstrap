# Global Agent Baseline

Machine-level baseline for all agent surfaces managed by `agent_bootstrap`.
Rendered to `~/.codex/AGENTS.md` and `~/.claude/*` — keep this file slim and
durable.

## Working Agreement

- Follow repo-local `AGENTS.md` when present; it refines this baseline.
- Prefer CLI-friendly, idempotent commands (`./install.sh`, `agentboot`).
- Treat rendered agent-home files as read-only outputs derived from canonical
  `AGENTS.md` sources.
- Never auto-commit or auto-push changes.

## Skills Discipline

- Curated upstreams live in `skills.sources.yaml`; install with
  `./install.sh skills install` or `update`.
- Global pins are authoritative in `~/.agents/.skill-lock.json`.
- Pick 2–4 skills per session by phase — do not load every skill at once.
- Repo skill tables in `base/AGENTS.md` should match enabled manifest entries.

## Surface Goals

- **Codex CLI** — consume this baseline plus repo overlays.
- **Claude Code** — read generated `~/.claude/AGENTS.md` / `CLAUDE.md` and
  repo `CLAUDE.md` pointers.
- **Cursor / Copilot** — use globally installed skills and repo `AGENTS.md`
  overlays scaffolded by `agentboot`.

## Project / Repo Conventions

- `AGENT_BOOTSTRAP_HOME` points at the `agent_bootstrap` clone (set by
  `install.sh`).
- Per-repo policy: scaffold with `agentboot`, then edit the `## Project`
  section in repo `AGENTS.md`.
- Archived workspace render, catalog, and MCP control-plane features live under
  `archive/` — do not assume they are active in the slim bootstrap path.

## Guardrails

- `install.sh` is the primary interface for bootstrap operations.
- Do not restore archived modules without re-wiring imports.
- Never run uninstall flows without explicit user request.
