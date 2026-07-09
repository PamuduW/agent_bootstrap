# agent_bootstrap archive

This directory holds **pre-slim `agent_bootstrap` assets** moved during the 2026-07-09 rework. It is **not part of the runtime install path** — `./install.sh`, `npx skills`, `bin/agentboot`, and slim bootstrap flows do not read from here.

Restore from this folder if you need a deferred capability (catalog, workspace render, memory vault, etc.). Git history also preserves pre-move paths.

## Pre-slim snapshot

See [MANIFEST.md](./MANIFEST.md) for the top-level repo layout **before** Tier 1/2 moves (captured 2026-07-09).

## Tier 1 moves (Phase 2 — 2026-07-09)

These paths were moved from the repo root with `git mv` (except `exports/`, which was gitignored and relocated with `mv`):

| Original path | Archive path |
|---------------|--------------|
| `memory-vault/` | `archive/memory-vault/` |
| `future/` | `archive/future/` |
| `agentos.yaml` | `archive/agentos.yaml` |
| `templates/` | `archive/templates/` |
| `exports/` | `archive/exports/` |
| `docs/openclaw-plan.md` | `archive/docs/openclaw-plan.md` |
| `docs/harness-architecture.md` | `archive/docs/harness-architecture.md` |
| `skills/README.md` | `archive/skills-README.md` |

Top-level `docs/` and `skills/` were removed after the moves (empty). Restore from this directory or from git history.

## Planned archive contents (rework plan)

### Tier 2 — after code surgery (Phase 3)

| Path | Reason |
|------|--------|
| `catalog/` | Package catalog + MCP provenance |
| `mcp/` | `mcp.json` for rendered MCP bundles |
| `src/agent_bootstrap/discovery.py` | Workspace/package discovery |
| `src/agent_bootstrap/catalog.py` | Catalog load/filter |
| `src/agent_bootstrap/state.py` | Tracked workspaces |
| `src/agent_bootstrap/ui.py` | Interactive Apply menus |
| Workspace render | `render_workspace_outputs` in `render.py` |

## Deferred use cases (restore from archive)

| Use case | Archive dependency |
|----------|-------------------|
| Full bootstrap / interactive Apply | `ui.py`, `state.py` |
| Workspace render | `render_workspace_outputs`, `templates/` |
| Render all tracked workspaces | `discovery.py`, `state.py` |
| Package catalog / import-local | `catalog/` |
| MCP filter / render | `mcp/`, `catalog/packages.json` |
| Memory vault | `memory-vault/` |
| agentboot `--full` | catalog/render coupling |

## Slim core (stays at repo root)

`install.sh`, `skills.sources.yaml`, `skills-lock.json`, `bin/*`, `base/`, `global/AGENTS.md`, trimmed `src/`, and focused tests.

## Restore notes

1. Copy or `git mv` the needed path from `archive/` back to its original location.
2. Re-wire imports in `src/agent_bootstrap/cli.py`, `service.py`, or `install.sh` if Tier 2 modules were archived.
3. Run `pytest tests/` and `./install.sh skills doctor` after restoring.
