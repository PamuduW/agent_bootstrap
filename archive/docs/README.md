# agent_bootstrap archive

This directory holds **pre-slim `agent_bootstrap` assets** moved during the 2026-07-09 rework. It is **not part of the runtime install path** — `./install.sh`, `npx skills`, `bin/agentbot`, and slim bootstrap flows do not read from here.

All archive Markdown indexes, roadmaps, and historical notes live in this
`archive/docs/` directory. The archive root keeps the remaining
JSON/YAML/environment configuration and template payloads they describe.

**Archive documentation:**

| File | Role |
|------|------|
| [stuff.md](./stuff.md) | Deferred capability map + restore pointers |
| [stuff3.md](./stuff3.md) | **Implementation phases** (Phases 0–2 and 5 complete; Phase 4 next; Phase 3 deferred) |
| [legacy-memory-vault-design.md](./legacy-memory-vault-design.md) | Sanitized historical note; not an active memory store |
| [future.md](./future.md) | Deferred AgentOS feature notes |
| [LOCKFILE-NOTES.md](./LOCKFILE-NOTES.md) | Historical lockfile strategy |

**Docs-only policy (2026-07-10):** Python modules and tests were removed from
`archive/`; recover them from **git history** when restoring. Configuration
(JSON/YAML) remains under `archive/`; Markdown documentation stays in this
directory.

Restore **design** from this folder and **configuration** from the archive root
and its payload directories; restore **code** from git. See [stuff.md § If you
restore](./stuff.md#if-you-restore-a-deferred-feature).

## Pre-slim snapshot

Tier 1/2 move tables below record what left the repo root on 2026-07-09. See [stuff.md](./stuff.md) for the deferred map and [stuff3.md](./stuff3.md) for the build phases.

## Tier 1 moves (Phase 2 — 2026-07-09)

Moved from repo root with `git mv` (except `exports/`, which was gitignored and relocated with `mv`):

| Original path | Archive path | Notes |
|---------------|--------------|-------|
| `memory-vault/` | *(removed in Phase 4 Slice 4M)* | Public memory prototype; see [legacy-memory-vault-design.md](./legacy-memory-vault-design.md) |
| `future/` | `archive/docs/future.md` | Deferred AgentOS / harness phases |
| `agentos.yaml` | `archive/agentos.yaml` | v4 Lite profiles and export targets |
| `templates/` | `archive/templates/` | Per-repo AGENTS.md overlay template for workspace render |
| `exports/` | `archive/exports/` | Generated outputs (was gitignored) |

Top-level `docs/` and `skills/` were removed after the moves (empty). Restore from this directory or from git history.

## Tier 2 moves (Phase 3 — 2026-07-09)

Moved after CLI/service/render surgery:

| Original path | Archive path | Notes |
|---------------|--------------|-------|
| `catalog/` | `archive/catalog/` | Package catalog + MCP key provenance |
| `mcp/` | `archive/mcp/` | `mcp.json` for rendered MCP bundles |
| `.env.example` | `archive/.env.example` | Optional MCP-related env vars |
| `src/agent_bootstrap/discovery.py` | *(removed 2026-07-10)* | Workspace/package discovery — **git history** |
| `src/agent_bootstrap/catalog.py` | *(removed 2026-07-10)* | Catalog load/filter — **git history** |
| `src/agent_bootstrap/state.py` | *(removed 2026-07-10)* | Tracked workspaces + audit log — **git history** |
| `src/agent_bootstrap/ui.py` (full) | *(removed 2026-07-10)* | Interactive Apply menus — **git history** |
| `src/agent_bootstrap/render.py` (full) | *(removed 2026-07-10)* | Workspace render + MCP filter — **git history** |
| `tests/test_bootstrap_engine.py` (full) | *(removed 2026-07-10)* | Catalog/workspace tests — **git history** |
| `exports/` | *(removed 2026-07-10)* | Was empty generated-output placeholder |

**Slim replacements at repo root:**

- `src/render.py` — `render_global_outputs` only (no MCP write from catalog)
- `src/ui.py` — print helpers only (no interactive menus)
- `bin/agentbot` — live unified scaffold and Phase 2 workspace entrypoint

## Pack → bootstrap matrix

Maps v4 Lite / pre-slim config-plane concepts to the slim bootstrap (2026-07-09 rework):

| v4 pack concept | Slim status | Location |
|-----------------|-------------|----------|
| Upstream skills manifest (`npx skills`) | **Live** | `skills.sources.yaml` |
| Global skill lockfile | **Live** (repo stub; global pins in `~/.agents/.skill-lock.json`) | `skills-lock.json` |
| `install.sh` / Python CLI | **Live (trimmed)** | `install.sh`, `src/` (`cli.py`, `service.py`, …) |
| `agentbot` scaffold | **Live** | `bin/agentbot`, `base/` |
| Global `AGENTS.md` render | **Live** | `global/AGENTS.md`, `src/render.py` |
| Claude skills bridge | **Live** | `bin/claude-skills-bridge.sh` |
| Package catalog + MCP provenance | **Archived** | `archive/catalog/`, `archive/mcp/` |
| Workspace render + templates | **Live (Phase 2)** | `agentos.yaml`, `src/workspace_render.py`, `base/` |
| Local registration / tracked workspaces | **Live (Phase 2)** | `src/workspace_state.py`, `src/workspace_service.py` |
| `agentos.yaml` profiles | **Live (Phase 2)** | `agentos.yaml`, `src/workspace_profiles.py` |
| Durable memory design | **Next (Phase 4)** | Workspace `temp/mem/`; public prototype removed |
| Deferred AgentOS / harness phases | **Archived** | `archive/docs/future.md`, `archive/docs/` |
| Graphify skill integration | **On-demand / live** | Main Agentbot Install/Update plus direct `agentbot graphify setup` repair; not a manifest source |
| `obsidian-memory` skill source | **Disabled** | `skills.sources.yaml` (`enabled: false`) |

## Archived and deferred use cases

| Use case | Archive / git dependency |
|----------|--------------------------|
| Full bootstrap / catalog Apply | `ui.py`, `state.py` — **git**; restore only with a new Phase 3 design |
| Workspace render | **Live Phase 2**: `src/workspace_render.py`, `base/`, `agentos.yaml` |
| Render all registered workspaces | **Live Phase 2**: `src/workspace_state.py`, `src/workspace_service.py` |
| Package catalog / import-local | `archive/catalog/` |
| MCP filter / render into `.cursor/mcp.json` | `archive/mcp/`, `catalog/packages.json` |
| Memory vault workflows | Workspace `temp/mem/`; implementation begins after the Phase 4 migration gate |
| Agentbot workspace exports (Copilot + Cursor rules) | `src/workspace_render.py` — live Phase 2 |
| `agentos.yaml` profiles | `agentos.yaml` |

## Slim core (stays at repo root)

`install.sh`, `skills.sources.yaml`, `skills-lock.json`, `bin/*`, `base/`, `global/AGENTS.md`, trimmed `src/`, and focused tests.

## Restore notes

See [stuff.md](./stuff.md) and [stuff3.md](./stuff3.md). Summary:

1. **Pick scope** — catalog, discovery, state, full render, and ui are coupled.
2. **Config/docs** — copy from `archive/` (`catalog/`, `mcp/`, `templates/`, `agentos.yaml`); use the Phase 4 design in workspace `temp/mem/` for the private memory workflow.
3. **Code** — restore from git (pre-2026-07-10 archive layout or `git show <commit>:archive/src/...`).
4. **Re-wire** — `src/cli.py`, `install.sh`, `service.py`; archived CLI subcommands.
5. **Env** — copy `archive/.env.example` if MCP servers need credentials.
6. **Verify** — unittest + `./install.sh doctor`.
