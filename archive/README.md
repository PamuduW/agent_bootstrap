# agent_bootstrap archive

This directory holds **pre-slim `agent_bootstrap` assets** moved during the 2026-07-09 rework. It is **not part of the runtime install path** — `./install.sh`, `npx skills`, `bin/agentboot`, and slim bootstrap flows do not read from here.

Restore from this folder if you need a deferred capability. Git history also preserves pre-move paths.

## Pre-slim snapshot

See [MANIFEST.md](./MANIFEST.md) for the top-level repo layout **before** Tier 1/2 moves (captured 2026-07-09).

## Tier 1 moves (Phase 2 — 2026-07-09)

Moved from repo root with `git mv` (except `exports/`, which was gitignored and relocated with `mv`):

| Original path | Archive path | Notes |
|---------------|--------------|-------|
| `memory-vault/` | `archive/memory-vault/` | Obsidian-compatible human memory store |
| `future/` | `archive/future/` | Deferred AgentOS / harness phases |
| `agentos.yaml` | `archive/agentos.yaml` | v4 Lite profiles and export targets |
| `templates/` | `archive/templates/` | Per-repo AGENTS.md overlay template for workspace render |
| `exports/` | `archive/exports/` | Generated outputs (was gitignored) |
| `docs/openclaw-plan.md` | `archive/docs/openclaw-plan.md` | OpenClaw adapter planning |
| `docs/harness-architecture.md` | `archive/docs/harness-architecture.md` | Three-plane harness architecture |
| `skills/README.md` | `archive/skills-README.md` | In-repo personal skills pack docs (no fork workflow) |

Top-level `docs/` and `skills/` were removed after the moves (empty). Restore from this directory or from git history.

## Tier 2 moves (Phase 3 — 2026-07-09)

Moved after CLI/service/render surgery:

| Original path | Archive path | Notes |
|---------------|--------------|-------|
| `catalog/` | `archive/catalog/` | Package catalog + MCP key provenance |
| `mcp/` | `archive/mcp/` | `mcp.json` for rendered MCP bundles |
| `.env.example` | `archive/.env.example` | Optional MCP-related env vars |
| `src/agent_bootstrap/discovery.py` | `archive/src/agent_bootstrap/discovery.py` | Workspace/package discovery |
| `src/agent_bootstrap/catalog.py` | `archive/src/agent_bootstrap/catalog.py` | Catalog load/filter |
| `src/agent_bootstrap/state.py` | `archive/src/agent_bootstrap/state.py` | Tracked workspaces + audit log |
| `src/agent_bootstrap/ui.py` (full) | `archive/src/agent_bootstrap/ui.py` | Interactive Apply menus |
| `src/agent_bootstrap/render.py` (full) | `archive/src/agent_bootstrap/render.py` | Includes `render_workspace_outputs`, MCP filter |
| `tests/test_bootstrap_engine.py` (full) | `archive/tests/test_bootstrap_engine.py` | Catalog/workspace render tests |

**Slim replacements at repo root:**

- `src/agent_bootstrap/render.py` — `render_global_outputs` only (no MCP write from catalog)
- `src/agent_bootstrap/ui.py` — print helpers only (no interactive menus)
- `bin/agentboot --full` — deprecated; runs minimal scaffold only

## Deferred use cases

| Use case | Archive dependency |
|----------|-------------------|
| Full bootstrap / interactive Apply | `ui.py`, `state.py`, restore CLI commands |
| Workspace render | `render_workspace_outputs`, `templates/` |
| Render all tracked workspaces | `discovery.py`, `state.py` |
| Package catalog / import-local | `catalog/` |
| MCP filter / render into `.cursor/mcp.json` | `mcp/`, `catalog/packages.json` |
| Memory vault workflows | `memory-vault/` |
| agentboot `--full` (Copilot + Cursor rules) | catalog/render coupling in archived `render.py` |
| `agentos.yaml` profiles | `archive/agentos.yaml` |

## Slim core (stays at repo root)

`install.sh`, `skills.sources.yaml`, `skills-lock.json`, `bin/*`, `base/`, `global/AGENTS.md`, trimmed `src/`, and focused tests.

## Restore notes

1. **Pick scope** — restore only what you need; Tier 2 modules depend on each other (catalog + discovery + state + full render + ui).
2. **Move files back** — `git mv archive/<path> <original-path>` or copy and adjust.
3. **Re-wire code** — restore archived commands in `src/agent_bootstrap/cli.py` and `install.sh` (`workspace`, `all`, `interactive`, `import-local`, `remove-managed`, `delete-local`). Re-import archived modules in `service.py`.
4. **Restore tests** — merge or replace slim `tests/test_bootstrap_engine.py` with archived copy if testing catalog/workspace paths.
5. **Env** — copy `archive/.env.example` to repo root if MCP servers need credentials.
6. **Verify** — `python3 -m unittest discover -s tests` and `./install.sh skills doctor`.

Commit restore work on a branch; slim `main` / `slim-bootstrap` should stay the default install path unless you intentionally revert the rework.
