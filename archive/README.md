# agent_bootstrap archive

This directory holds **pre-slim `agent_bootstrap` assets** moved during the 2026-07-09 rework. It is **not part of the runtime install path** — `./install.sh`, `npx skills`, `bin/agentboot`, and slim bootstrap flows do not read from here.

**Canonical deferred map:** [stuff.md](./stuff.md)  
**Docs-only policy (2026-07-10):** Python modules and tests were removed from `archive/`; recover them from **git history** when restoring. Config (JSON/YAML) and markdown stay here.

Restore from this folder for **design and config**; restore **code** from git. See [stuff.md § If you restore](./stuff.md#if-you-restore-a-deferred-feature).

## Pre-slim snapshot

Tier 1/2 move tables below record what left the repo root on 2026-07-09. See [stuff.md](./stuff.md) for the current deferred map.

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
- `bin/agentboot --full` — deprecated; runs minimal scaffold only

## Pack → bootstrap matrix

Maps v4 Lite / pre-slim config-plane concepts to the slim bootstrap (2026-07-09 rework):

| v4 pack concept | Slim status | Location |
|-----------------|-------------|----------|
| Upstream skills manifest (`npx skills`) | **Live** | `skills.sources.yaml` |
| Global skill lockfile | **Live** (repo stub; global pins in `~/.agents/.skill-lock.json`) | `skills-lock.json` |
| `install.sh` / Python CLI | **Live (trimmed)** | `install.sh`, `src/` (`cli.py`, `service.py`, …) |
| `agentboot` scaffold | **Live** | `bin/agentboot`, `base/` |
| Global `AGENTS.md` render | **Live** | `global/AGENTS.md`, `src/render.py` |
| Claude skills bridge | **Live** | `bin/claude-skills-bridge.sh` |
| Package catalog + MCP provenance | **Archived** | `archive/catalog/`, `archive/mcp/` |
| Workspace render + templates | **Archived** | `archive/templates/`; render code in **git** |
| Interactive Apply / tracked workspaces | **Archived** | ui/state/discovery in **git** |
| `agentos.yaml` profiles | **Archived** | `archive/agentos.yaml` |
| Obsidian memory vault | **Archived** | `archive/memory-vault/` |
| Deferred AgentOS / harness phases | **Archived** | `archive/future/`, `archive/docs/` |
| `graphify` skill source | **Disabled** | `skills.sources.yaml` (`enabled: false`) |
| `obsidian-memory` skill source | **Disabled** | `skills.sources.yaml` (`enabled: false`) |

## Deferred use cases

| Use case | Archive / git dependency |
|----------|--------------------------|
| Full bootstrap / interactive Apply | `ui.py`, `state.py` — **git**; restore CLI commands |
| Workspace render | `templates/` + full `render.py` — **git** |
| Render all tracked workspaces | `discovery.py`, `state.py` — **git** |
| Package catalog / import-local | `archive/catalog/` |
| MCP filter / render into `.cursor/mcp.json` | `archive/mcp/`, `catalog/packages.json` |
| Memory vault workflows | `archive/memory-vault/` |
| agentboot `--full` (Copilot + Cursor rules) | catalog + full render — **git** |
| `agentos.yaml` profiles | `archive/agentos.yaml` |

## Slim core (stays at repo root)

`install.sh`, `skills.sources.yaml`, `skills-lock.json`, `bin/*`, `base/`, `global/AGENTS.md`, trimmed `src/`, and focused tests.

## Restore notes

See [stuff.md](./stuff.md) for the full deferred map. Summary:

1. **Pick scope** — catalog, discovery, state, full render, and ui are coupled.
2. **Config/docs** — copy from `archive/` (`catalog/`, `mcp/`, `templates/`, `agentos.yaml`, `memory-vault/`).
3. **Code** — restore from git (pre-2026-07-10 archive layout or `git show <commit>:archive/src/...`).
4. **Re-wire** — `src/cli.py`, `install.sh`, `service.py`; archived CLI subcommands.
5. **Env** — copy `archive/.env.example` if MCP servers need credentials.
6. **Verify** — unittest + `./install.sh doctor`.
