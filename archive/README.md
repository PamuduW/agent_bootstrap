# agent_bootstrap archive

This directory holds **pre-slim `agent_bootstrap` assets** moved during the 2026-07-09 rework. It is **not part of the runtime install path** — `./install.sh`, `npx skills`, `bin/agentbot`, and slim bootstrap flows do not read from here.

**Docs (archive/docs/):**

| File | Role |
|------|------|
| [stuff.md](./docs/stuff.md) | Deferred capability map + restore pointers |
| [stuff2.md](./docs/stuff2.md) | Day-to-day impact of deferred features |
| [stuff3.md](./docs/stuff3.md) | **Implementation phases** (Phase 0–2 complete; Phases 3–4 deferred) |

**Docs-only policy (2026-07-10):** Python modules and tests were removed from `archive/`; recover them from **git history** when restoring. Config (JSON/YAML) and markdown stay here.

Restore from this folder for **design and config**; restore **code** from git. See [stuff.md § If you restore](./docs/stuff.md#if-you-restore-a-deferred-feature).

## Pre-slim snapshot

Tier 1/2 move tables below record what left the repo root on 2026-07-09. See [stuff.md](./docs/stuff.md) for the deferred map and [stuff3.md](./docs/stuff3.md) for the build phases.

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
| Obsidian memory vault | **Archived** | `archive/memory-vault/` |
| Deferred AgentOS / harness phases | **Archived** | `archive/future/`, `archive/docs/` |
| `graphify` skill source | **Disabled** | `skills.sources.yaml` (`enabled: false`) |
| `obsidian-memory` skill source | **Disabled** | `skills.sources.yaml` (`enabled: false`) |

## Archived and deferred use cases

| Use case | Archive / git dependency |
|----------|--------------------------|
| Full bootstrap / catalog Apply | `ui.py`, `state.py` — **git**; restore only with a new Phase 3 design |
| Workspace render | **Live Phase 2**: `src/workspace_render.py`, `base/`, `agentos.yaml` |
| Render all registered workspaces | **Live Phase 2**: `src/workspace_state.py`, `src/workspace_service.py` |
| Package catalog / import-local | `archive/catalog/` |
| MCP filter / render into `.cursor/mcp.json` | `archive/mcp/`, `catalog/packages.json` |
| Memory vault workflows | `archive/memory-vault/` |
| Agentbot workspace exports (Copilot + Cursor rules) | `src/workspace_render.py` — live Phase 2 |
| `agentos.yaml` profiles | `agentos.yaml` |

## Slim core (stays at repo root)

`install.sh`, `skills.sources.yaml`, `skills-lock.json`, `bin/*`, `base/`, `global/AGENTS.md`, trimmed `src/`, and focused tests.

## Restore notes

See [stuff.md](./docs/stuff.md) and [stuff3.md](./docs/stuff3.md). Summary:

1. **Pick scope** — catalog, discovery, state, full render, and ui are coupled.
2. **Config/docs** — copy from `archive/` (`catalog/`, `mcp/`, `templates/`, `agentos.yaml`, `memory-vault/`).
3. **Code** — restore from git (pre-2026-07-10 archive layout or `git show <commit>:archive/src/...`).
4. **Re-wire** — `src/cli.py`, `install.sh`, `service.py`; archived CLI subcommands.
5. **Env** — copy `archive/.env.example` if MCP servers need credentials.
6. **Verify** — unittest + `./install.sh doctor`.
