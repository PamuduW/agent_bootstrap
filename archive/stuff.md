# Deferred capabilities — archive reference

**Status:** Docs-only archive (2026-07-10). Python modules and tests were removed from this folder; they remain in **git history** if you restore the full control plane.

Nothing here is read by `./install.sh`, `npx skills`, or `agentboot` at runtime.

---

## What stays in `archive/` (keep)

| Path | Why keep |
|------|----------|
| **[stuff.md](./stuff.md)** | This file — deferred map and restore pointers |
| **[README.md](./README.md)** | Move log (Tier 1/2) and pack → bootstrap matrix |
| **[LOCKFILE-NOTES.md](./LOCKFILE-NOTES.md)** | Global vs project lockfile history |
| **[docs/](./docs/)** | Harness architecture, OpenClaw plan |
| **[future/README.md](./future/README.md)** | AgentOS roadmap items still deferred |
| **[memory-vault/](./memory-vault/)** | Human Obsidian-style memory (draft → you approve) |
| **[agentos.yaml](./agentos.yaml)** | v4 Lite export profiles reference |
| **[catalog/packages.json](./catalog/packages.json)** | Package catalog schema + entries for future MCP restore |
| **[mcp/mcp.json](./mcp/mcp.json)** | MCP server list for future workspace render |
| **[templates/](./templates/)** | Workspace render overlay templates |
| **[.env.example](./.env.example)** | MCP credential env var names |

---

## What was removed (safe — recover from git)

Removed **2026-07-10** to keep archive lean. None of this was on the runtime path.

| Removed | Original role | Recover via |
|---------|---------------|-------------|
| `archive/src/agent_bootstrap/*.py` | catalog, discovery, state, full render, interactive ui | `git log -- archive/src` or pre-2026-07-10 commit |
| `archive/tests/test_bootstrap_engine.py` | Catalog/workspace render tests | git history |
| `archive/exports/` | Empty generated-output placeholder | Not needed |

**Do not delete** the JSON/YAML/markdown rows in the “keep” table unless you are sure you will never restore catalog, MCP, workspace render, or memory vault.

---

## What's still **live** (repo root)

| Capability | Where |
|------------|--------|
| Skills install/update | `skills.sources.yaml`, `bin/skills-install.sh` |
| Global skill pins | `~/.agents/.skill-lock.json` |
| Claude bridge | `bin/claude-skills-bridge.sh` |
| `agentboot` minimal | `bin/agentboot`, `base/` |
| Global baseline | `global/AGENTS.md` → `~/.codex/`, `~/.claude/` |
| Slim CLI | `src/` (`python3 -m src.cli`) |
| Doctor / status | `install.sh` |

---

## Deferred — archived artifacts (docs + config in tree)

| Capability | What it was | What you still have locally |
|------------|-------------|----------------------------|
| Interactive control-plane TUI | Package/workspace menus, Apply | Code in **git**; design in `docs/harness-architecture.md` |
| Workspace render | Per-repo Copilot/Cursor/MCP exports | `templates/`, `agentos.yaml`; code in **git** |
| Tracked workspaces | Discovery + state + render-all | Code in **git** |
| Package catalog | `import-local`, provenance | `catalog/packages.json` |
| MCP bundle render | Filtered `.cursor/mcp.json` | `mcp/mcp.json`, `catalog/` |
| `agentboot --full` | Copilot + Cursor rules + MCP | Warn-only today; full logic in **git** |
| `agentos.yaml` profiles | Export target map | `archive/agentos.yaml` |
| Obsidian memory vault | Tier 3 memory | `memory-vault/` |
| In-repo skills pack | Vendored skills in repo | Removed — use `skills.sources.yaml` |
| CLI commands | `workspace`, `all`, `interactive`, `import-local`, … | Hard-fail → pointer to this archive |

### Disabled in manifest (not in archive)

| Skill source | Reason |
|--------------|--------|
| `graphify` | `enabled: false` — upstream layout not ready |
| `obsidian-memory` | `enabled: false` |

---

## Deferred — future phases (docs only, not built)

From `docs/harness-architecture.md` and `future/README.md`.

**Memory tiers** — add only when the previous tier hurts:

| Tier | Mechanism | Status |
|------|-----------|--------|
| 1 | Per-repo `AGENTS.md` via `agentboot` | **Live** |
| 2 | Global `npx skills` | **Live** |
| 3 | Obsidian vault | **Archived** (`memory-vault/`) |
| 4 | Hermes `MEMORY.md` + SQLite FTS (home server) | **Deferred** — Proxmox + Phase 7.3 |
| 5 | Graphify on-demand (large infra repos) | **Deferred** |
| 6 | Mem0 / Graphiti / GraphRAG | **Deferred** |

**Later phases (do not build on laptop now):**

- **7.2** — opencode, OpenRouter, planner → worker → reviewer
- **7.3** — Proxmox, Hermes daemon, Telegram/Discord gateway
- **7.4** — Graphify hooks, Mem0 MCP, Graphiti/GraphRAG
- **AgentOS extras** — full taxonomy, `agentos tui`, ingest pipeline, OpenClaw file set (`SOUL.md`, …)

**Control plane:** Hermes on Proxmox — out of scope until config + work planes are stable.

---

## Mental model

```text
LIVE (slim)                 ARCHIVE (docs/config)        GIT HISTORY (code)     FUTURE (not built)
───────────                 ─────────────────────        ──────────────────     ────────────────
npx skills                  harness-architecture.md      catalog.py             Hermes / Proxmox
agentboot minimal           agentos.yaml                 discovery.py           Graphify / Mem0
global render               packages.json + mcp.json     state.py, ui.py
Claude bridge               memory-vault/                render.py (full)
doctor                      templates/
```

---

## If you restore a deferred feature

1. **Pick scope** — catalog/MCP/render/ui are coupled; partial restore is awkward.
2. **Restore code from git** — e.g. `git show <commit>:archive/src/agent_bootstrap/render.py` or checkout pre-removal commit.
3. **Copy config from archive** — `catalog/`, `mcp/`, `templates/`, `agentos.yaml`, `.env.example`.
4. **Re-wire live tree** — `src/cli.py`, `install.sh`, `service.py`; restore CLI subcommands.
5. **Restore tests** from git if you need catalog/workspace coverage.
6. **Verify** — `python3 -m unittest discover -s tests` and `./install.sh doctor`.

Use a branch; keep slim `main` as default until you intentionally expand scope.
