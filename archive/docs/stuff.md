# Deferred capabilities — archive reference

**Status:** Docs-only archive (2026-07-10). Python modules and tests were removed from this folder; they remain in **git history** if you restore the full control plane.

Nothing here is read by `./install.sh`, `npx skills`, or `agentbot` at runtime.

**Implementation roadmap:** [../../docs/roadmap.md](../../docs/roadmap.md) — active phased build plan.

**Current status (2026-08-06):** Phases 0–2 and 5 are complete. Phase 4 is
the next workstream; its public-memory migration gate (Slice 4M) is merged and
complete, so Slice 4.0A is next. Phase 3 remains deferred. The live system is
the standalone Agentbot menu, profile-driven workspace rendering, local
registration/resync, global baseline rendering, curated skills management, and
the Dotfiles sibling bridge, with an optional Graphify CLI and assistant
integration. Catalog/MCP remains deferred; the active Phase 4 design is in the
workspace `temp/mem/` notes, not in this archive.

---

## What stays in `archive/` (keep)

| Path | Why keep |
|------|----------|
| **[stuff.md](./stuff.md)** | This file — deferred map and restore pointers |
| **[../../docs/roadmap.md](../../docs/roadmap.md)** | Active implementation phases (outside the archive) |
| **[legacy-memory-vault-design.md](./legacy-memory-vault-design.md)** | Sanitized history of the retired public prototype |
| **[README.md](./README.md)** | Move log (Tier 1/2) and pack → bootstrap matrix |
| **[LOCKFILE-NOTES.md](./LOCKFILE-NOTES.md)** | Global vs project lockfile history |
| **[archive/docs/](./)** | Deferred-capability and historical notes (`stuff.md`, `future.md`) |
| **[future.md](./future.md)** | AgentOS roadmap items still deferred |
| **Phase 4 design** | Workspace [`temp/mem/`](../../../temp/mem/); private memory is not stored in this repository |
| **[agentos.yaml](../agentos.yaml)** | v4 Lite export profiles reference |
| **[catalog/packages.json](../catalog/packages.json)** | Package catalog schema + entries for future MCP restore |
| **[mcp/mcp.json](../mcp/mcp.json)** | MCP server list for future workspace render |
| **[templates/](../templates/)** | Workspace render overlay templates |
| **[.env.example](../.env.example)** | MCP credential env var names |

---

## What was removed (safe — recover from git)

Removed **2026-07-10** to keep archive lean. None of this was on the runtime path.

| Removed | Original role | Recover via |
|---------|---------------|-------------|
| `archive/src/agent_bootstrap/*.py` | catalog, discovery, state, full render, interactive ui | `git log -- archive/src` or pre-2026-07-10 commit |
| `archive/tests/test_bootstrap_engine.py` | Catalog/workspace render tests | git history |
| `archive/exports/` | Empty generated-output placeholder | Not needed |

**Do not delete** the remaining JSON/YAML/markdown rows in the “keep” table
unless you are sure you will never restore catalog, MCP, or workspace render.

---

## What's still **live** (repo root)

| Capability | Where |
|------------|--------|
| Skills install/update | `skills.sources.yaml`, `bin/skills-install.sh` |
| Global skill pins | `~/.agents/.skill-lock.json` |
| Claude bridge | `bin/claude-skills-bridge.sh` |
| `agentbot` bootstrap | `bin/agentbot`, `base/` |
| Workspace render and resync | `src/workspace_*.py`, `agentos.yaml`, `scripts/menus/workspaces.sh` |
| Global baseline | `global/AGENTS.md` → `~/.codex/`, `~/.claude/` |
| Optional Graphify integration | sibling `dotfiles` `graphify_cli` component, main Agentbot Install/Update, `src/graphify.py`, and direct `agentbot graphify` repair commands |
| Slim CLI | `src/` (`python3 -m src.cli`) |
| Doctor / status | `install.sh` |

---

## Archived artifacts and deferred capabilities (docs + config in tree)

| Capability | What it means | What you still have |
|------------|---------------|---------------------|
| **Interactive control-plane TUI** | Arrow-key menus inside `agent_bootstrap` to pick packages, track workspaces, and “Apply” exports — a full installer UI, not just `install.sh` one-shots. | Historical design/code remain in **git history**. Restore only with a new Phase 3 design. |
| **Workspace render** | Generate per-repo agent files from canonical `AGENTS.md` with managed-boundary and conflict rules. | **Live Phase 2**: `../src/workspace_render.py`, `../agentos.yaml` |
| **Tracked workspaces** | Remember opted-in Git roots or plain folders and preview/resync them from local private state. | **Live Phase 2**: `../src/workspace_state.py` + `../src/workspace_service.py` |
| **Package catalog** | A curated JSON registry of skills, rules, MCP servers, and templates with provenance — “import from disk/cache into catalog” workflows. | `../catalog/packages.json`. Phase 3. |
| **MCP bundle render** | Filter the master MCP list per profile/workspace and write `.cursor/mcp.json` (and similar) automatically. | `../mcp/mcp.json` + catalog; render code in **git**. Phase 3. |
| **Agentbot workspace exports** | Generate Claude, Copilot, and Cursor compatibility files from one canonical source. | **Live Phase 2**; MCP files remain Phase 3. |
| **`agentos.yaml` profiles** | Declarative map of allowed workspace output targets and safe policy. | **Live Phase 2**: `../agentos.yaml` |
| **Durable memory** | Private, approval-gated Markdown vault designed outside this repository. | Workspace [`temp/mem/`](../../../temp/mem/); Phase 4 next. |
| **CLI commands** | Workspace preview/apply/list/resync are live; catalog-era `all`, `interactive`, `import-local`, `remove-managed`, and `delete-local` remain deferred. | `../src/cli.py`, `../install.sh`; catalog commands stay archived. |

Upstream skills only — no in-repo vendored pack. Live path: `skills.sources.yaml` + `npx skills -g`.

### External or disabled integrations (not managed by the curated manifest)

| Skill source | Reason |
|--------------|--------|
| Graphify | Live through the official CLI and main Agentbot Install/Update; direct `agentbot graphify setup` remains available for repair; intentionally not a Git skill source |
| `obsidian-memory` | Disabled; source layout and provenance remain unresolved |

---

## Deferred — future phases (docs only, not built)

Based on the former harness-architecture and future-phase notes. The retained
roadmap is [`future.md`](./future.md); the removed implementation/design
material remains recoverable from Git history.

**Memory tiers** — add only when the previous tier hurts:

| Tier | Mechanism | Status |
|------|-----------|--------|
| 1 | Per-repo `AGENTS.md` plus selected compatibility surfaces via `agentbot boot` | **Live — Phases 1–2 complete** |
| 2 | Global `npx skills` | **Live** |
| 3 | Private WSLg Obsidian vault | **Next — Phase 4** (workspace [`temp/mem/`](../../../temp/mem/)) |
| 4 | Hermes `MEMORY.md` + SQLite FTS (home server) | **Deferred** — Proxmox + Phase 7.3 |
| 5 | Graphify on-demand (large infra repos) | **Live — Phase 5** ([roadmap](../../docs/roadmap.md)) |
| 6 | Mem0 / Graphiti / GraphRAG | **Deferred** |

**Later phases (do not build on laptop now):**

- **7.2** — opencode, OpenRouter, planner → worker → reviewer
- **7.3** — Proxmox, Hermes daemon, Telegram/Discord gateway
- **7.4** — Graphify hooks, Mem0 MCP, Graphiti/GraphRAG (the standalone Graphify CLI integration is already live in Phase 5)
- **AgentOS extras** — full taxonomy, `agentos tui`, ingest pipeline, OpenClaw file set (`SOUL.md`, …)

**Control plane:** Hermes on Proxmox — out of scope until config + work planes are stable.

---

## Mental model

```text
LIVE (slim)                 ARCHIVE (docs/config)        GIT HISTORY (code)     FUTURE (not built)
───────────                 ─────────────────────        ──────────────────     ────────────────
npx skills                  future.md + roadmap.md       catalog.py             Hermes / Proxmox
agentbot bootstrap          agentos.yaml                 discovery.py           Mem0 / Graphiti
Graphify CLI + skill        packages.json + mcp.json     state.py, ui.py         Graphify hooks
global render               templates/                   render.py (full)
Claude bridge
doctor
```

---

## If you restore a deferred feature

1. **Pick scope** — follow [the active roadmap](../../docs/roadmap.md); catalog/MCP remain coupled within Phase 3 while the workspace renderer is live.
2. **Restore code from git** — e.g. `git show <commit>:archive/src/agent_bootstrap/render.py` or checkout pre-removal commit.
3. **Copy config from archive** — `catalog/`, `mcp/`, and `.env.example`; use the live root `agentos.yaml` and workspace renderer.
4. **Re-wire live tree** — `src/cli.py`, `install.sh`, `service.py`; restore only catalog/MCP subcommands after a new design.
5. **Restore tests** from git if you need catalog/workspace coverage.
6. **Verify** — `python3 -m unittest discover -s tests` and `./install.sh doctor`.

Use a branch; keep slim `main` as default until you intentionally expand scope.
