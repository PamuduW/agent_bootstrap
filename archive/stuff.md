The `archive/` folder is a **cold storage** area from the **2026-07-09 slim-bootstrap rework**. Nothing in `./install.sh`, `npx skills`, or `agentboot` reads it at runtime. It's there if you want to restore old capabilities from git or by moving files back.

---

## What's physically in `archive/` today

| Area | Contents |
|------|----------|
| **Docs** | `README.md`, `MANIFEST.md` (pre-slim snapshot), `LOCKFILE-NOTES.md`, `docs/harness-architecture.md`, `docs/openclaw-plan.md` |
| **Python (full control plane)** | `src/agent_bootstrap/` — `catalog.py`, `discovery.py`, `state.py`, `ui.py` (interactive menus), `render.py` (workspace + MCP render) |
| **Tests** | `tests/test_bootstrap_engine.py` (catalog/workspace tests) |
| **Catalog & MCP** | `catalog/packages.json`, `mcp/mcp.json` |
| **Templates** | `templates/AGENTS.md`, `.codexignore` (per-repo workspace render overlays) |
| **Memory vault** | `memory-vault/` — Obsidian-style markdown (active-context, preferences, decisions/, lessons/, projects/) |
| **Config** | `agentos.yaml` (v4 Lite profiles + export targets), `.env.example` (MCP creds) |
| **Future planning** | `future/README.md` (AgentOS roadmap items) |
| **Legacy skills docs** | `skills-README.md` (in-repo personal skills pack — removed workflow) |
| **Exports** | `exports/.gitkeep` (was generated output dir) |

`archive/MANIFEST.md` is a snapshot of the **full pre-slim repo tree** before Tier 1/2 moves.

---

## What's still **live** (not deferred)

These stayed at repo root and are what you use today:

| Capability | Where |
|------------|--------|
| Skills install/update via `npx skills` | `skills.sources.yaml`, `bin/skills-install.sh` |
| Global skill pins | `~/.agents/.skill-lock.json` |
| Claude bridge symlinks | `bin/claude-skills-bridge.sh` |
| `agentboot` minimal scaffold | `bin/agentboot`, `base/AGENTS.md`, `base/CLAUDE.md` |
| Global baseline render | `global/AGENTS.md` → `~/.codex/`, `~/.claude/` |
| Slim Python CLI | `src/` (`python3 -m src.cli`) |
| Doctor / status / bootstrap | `install.sh` |

---

## What you **deferred** (archived or disabled)

### A. Archived in `archive/` — restore if needed

| Deferred capability | What it was | Archive dependency |
|---------------------|-------------|-------------------|
| **Interactive control-plane TUI** | Arrow-key menus: packages, workspaces, Apply | `ui.py`, `state.py`, CLI commands `interactive`, `all` |
| **Workspace render** | Per-repo AGENTS/Copilot/Cursor/MCP exports from catalog | `render.py` (full), `templates/` |
| **Tracked workspaces** | Discover repos, track state, render all | `discovery.py`, `state.py` |
| **Package catalog** | Curated package list + provenance | `catalog/packages.json`, `catalog.py` |
| **MCP bundle render** | Write filtered `mcp.json` into workspaces | `mcp/mcp.json`, archived `render.py` |
| **`agentboot --full`** | Copilot instructions + Cursor rules + MCP exports | Archived render + catalog (today `--full` only warns and runs minimal) |
| **`agentos.yaml` profiles** | v4 Lite export profiles (`safe-default`, etc.) | `archive/agentos.yaml` |
| **Obsidian memory vault** | Human-owned durable memory (decisions, lessons, context) | `archive/memory-vault/` |
| **In-repo personal skills pack** | Vendored/forked skills in repo | Removed; upstream-only via manifest now |
| **CLI commands** | `workspace`, `all`, `interactive`, `import-local`, `remove-managed`, `delete-local` | Hard-fail in `install.sh` / `src/cli.py` with pointer to archive |

### B. Disabled in manifest (not archived, just off)

| Item | Why |
|------|-----|
| **`graphify`** | In `skills.sources.yaml` with `enabled: false` — upstream layout not ready |
| **`obsidian-memory`** | `enabled: false`, empty skills list |

### C. Explicitly **deferred to later phases** (documented, not in archive code)

From `archive/docs/harness-architecture.md` and `archive/future/README.md`:

**Memory tiers (add only when pain appears):**

| Tier | Mechanism | Status |
|------|-----------|--------|
| 1 | Per-repo `AGENTS.md` via `agentboot` | **Live** |
| 2 | Global `npx skills` | **Live** |
| 3 | Obsidian vault | **Archived** (in `memory-vault/`) |
| 4 | Hermes `MEMORY.md` + SQLite FTS on home server | **Deferred** — needs Proxmox + Phase 7.3 |
| 5 | Graphify for huge infra/K8s/TF repos | **Deferred** — trigger: grep + AGENTS.md isn't enough |
| 6 | Mem0 / Graphiti / GraphRAG semantic recall | **Deferred** — trigger: markdown stops scaling |

**Future phases (do not build now):**

- **Phase 7.2** — opencode + OpenRouter, planner→worker→reviewer workflows
- **Phase 7.3** — Proxmox home server, Hermes daemon, Telegram/Discord gateway, background cron while laptop is off
- **Phase 7.4** — Graphify rebuild hooks, Mem0 MCP, Graphiti/GraphRAG
- **AgentOS extras** — full taxonomy (`00-core/`, `10-rules/`, …), `agentos tui`, ingest pipeline, OpenClaw file set (`SOUL.md`, `USER.md`), ChatGPT adapters

**Control plane (biggest deferral):**

> Hermes on Proxmox as an always-on orchestrator — explicitly **out of scope** until config + work planes are stable. Laptop stays CLI-only, no daemon, no vector DB by default.

---

## Mental model

```text
LIVE (slim bootstrap)          ARCHIVED (archive/)           DEFERRED (docs only)
─────────────────────          ───────────────────           ──────────────────
npx skills                     catalog + MCP render          Hermes / Proxmox
agentboot minimal              interactive TUI               Graphify / Mem0 / GraphRAG
global AGENTS.md render        workspace render              opencode experiments
Claude bridge                  memory-vault                  AgentOS full taxonomy
doctor / status                agentos.yaml profiles         OpenClaw bootstrap set
```

---

## If you ever want something back

`archive/README.md` has restore steps: pick scope → `git mv archive/...` back → re-wire `src/cli.py` + `install.sh` + `service.py` → restore tests. Tier 2 modules are coupled (catalog + discovery + state + full render + ui), so partial restore is awkward.

**Bottom line:** You kept a **skills + scaffold + global baseline** installer. You parked the **full config plane** (catalog, MCP, workspace render, interactive menus, memory vault, agentos profiles) in `archive/`, and you **punted** the home-server control plane and heavy memory/graph layers to future phases when you actually need them.