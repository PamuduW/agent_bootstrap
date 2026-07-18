# Deferred capabilities — archive reference

**Status:** Docs-only archive (2026-07-10). Python modules and tests were removed from this folder; they remain in **git history** if you restore the full control plane.

Nothing here is read by `./install.sh`, `npx skills`, or `agentbot` at runtime.

**Implementation roadmap:** [stuff3.md](./stuff3.md) — phased build plan for restoring deferred features.

**Current status (2026-07-18):** Phase 1 is complete. The live system is the
standalone Agentbot menu, `agentbot boot`, global baseline rendering, curated
skills management, and the Dotfiles sibling bridge. The capabilities below are
deferred starting with Phase 2; this file records the design map, not a promise
to restore the old implementation unchanged.

---

## What stays in `archive/` (keep)

| Path | Why keep |
|------|----------|
| **[docs/stuff.md](./stuff.md)** | This file — deferred map and restore pointers |
| **[docs/stuff2.md](./stuff2.md)** | Day-to-day impact of deferred features |
| **[docs/stuff3.md](./stuff3.md)** | Implementation phases (Phase 0–1 complete; Phase 2 next) |
| **[README.md](../README.md)** | Move log (Tier 1/2) and pack → bootstrap matrix |
| **[LOCKFILE-NOTES.md](../LOCKFILE-NOTES.md)** | Global vs project lockfile history |
| **[docs/](./)** | Harness architecture, OpenClaw plan, stuff*.md |
| **[future/README.md](../future/README.md)** | AgentOS roadmap items still deferred |
| **[memory-vault/](../memory-vault/)** | Human Obsidian-style memory (draft → you approve) |
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

**Do not delete** the JSON/YAML/markdown rows in the “keep” table unless you are sure you will never restore catalog, MCP, workspace render, or memory vault.

---

## What's still **live** (repo root)

| Capability | Where |
|------------|--------|
| Skills install/update | `skills.sources.yaml`, `bin/skills-install.sh` |
| Global skill pins | `~/.agents/.skill-lock.json` |
| Claude bridge | `bin/claude-skills-bridge.sh` |
| `agentbot` bootstrap | `bin/agentbot`, `base/` |
| Global baseline | `global/AGENTS.md` → `~/.codex/`, `~/.claude/` |
| Slim CLI | `src/` (`python3 -m src.cli`) |
| Doctor / status | `install.sh` |

---

## Deferred — archived artifacts (docs + config in tree)

| Capability | What it means | What you still have |
|------------|---------------|---------------------|
| **Interactive control-plane TUI** | Arrow-key menus inside `agent_bootstrap` to pick packages, track workspaces, and “Apply” exports — a full installer UI, not just `install.sh` one-shots. | Design in [harness-architecture.md](./harness-architecture.md); code in **git**. Planned: [stuff3.md](./stuff3.md) Phase 2. |
| **Workspace render** | Generate per-repo agent files from the catalog: Copilot instructions, Cursor rules, repo `CLAUDE.md` merges — not just copying `base/`. | `../templates/`, `../agentos.yaml`; render code in **git**. Phase 2. |
| **Tracked workspaces** | Remember which git repos you care about, scan them, and re-render all of them when the catalog or global baseline changes. | `discovery.py` + `state.py` in **git**. Phase 2. |
| **Package catalog** | A curated JSON registry of skills, rules, MCP servers, and templates with provenance — “import from disk/cache into catalog” workflows. | `../catalog/packages.json`. Phase 3. |
| **MCP bundle render** | Filter the master MCP list per profile/workspace and write `.cursor/mcp.json` (and similar) automatically. | `../mcp/mcp.json` + catalog; render code in **git**. Phase 3. |
| **Agentbot workspace exports** | After the current `AGENTS.md` + `CLAUDE.md` bootstrap, also generate Copilot/Cursor compatibility files from one canonical source. | Phase 2 workspace render; MCP files remain Phase 3. |
| **`agentos.yaml` profiles** | Declarative map of export targets (Codex, Claude, Cursor, Copilot, per-repo) and trust/skill policy per profile. | `../agentos.yaml`. Phase 2. |
| **Obsidian memory vault** | Git-tracked markdown for durable context (decisions, lessons, preferences) — agents draft, you commit. | `../memory-vault/`. Phase 4. |
| **CLI commands** | Extra `install.sh` / CLI subcommands: `workspace`, `all`, `interactive`, `import-local`, `remove-managed`, `delete-local`. | Hard-fail today; restore with re-wired `src/cli.py`. Phase 2–3. |

Upstream skills only — no in-repo vendored pack. Live path: `skills.sources.yaml` + `npx skills -g`.

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
| 1 | Per-repo `AGENTS.md` via `agentbot boot` | **Live — Phase 1 complete** |
| 2 | Global `npx skills` | **Live** |
| 3 | Obsidian vault | **Phase 4** (`../memory-vault/`) |
| 4 | Hermes `MEMORY.md` + SQLite FTS (home server) | **Deferred** — Proxmox + Phase 7.3 |
| 5 | Graphify on-demand (large infra repos) | **Phase 4** ([stuff3.md](./stuff3.md)) |
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
agentbot bootstrap          agentos.yaml                 discovery.py           Graphify / Mem0
global render               packages.json + mcp.json     state.py, ui.py
Claude bridge               memory-vault/                render.py (full)
doctor                      templates/
```

---

## If you restore a deferred feature

1. **Pick scope** — follow [stuff3.md](./stuff3.md) phases; catalog/MCP/render/ui are coupled within Phases 2–3.
2. **Restore code from git** — e.g. `git show <commit>:archive/src/agent_bootstrap/render.py` or checkout pre-removal commit.
3. **Copy config from archive** — `catalog/`, `mcp/`, `templates/`, `agentos.yaml`, `.env.example`.
4. **Re-wire live tree** — `src/cli.py`, `install.sh`, `service.py`; restore CLI subcommands.
5. **Restore tests** from git if you need catalog/workspace coverage.
6. **Verify** — `python3 -m unittest discover -s tests` and `./install.sh doctor`.

Use a branch; keep slim `main` as default until you intentionally expand scope.
