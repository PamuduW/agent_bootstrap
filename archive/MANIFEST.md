# Pre-slim top-level manifest

**Captured:** 2026-07-09  
**Branch:** `main` (working tree clean at capture time)  
**Purpose:** Snapshot of repo layout before Tier 1/2 archive moves.

## Top-level entries

| Name | Type | Notes |
|------|------|-------|
| `.env.example` | file | Environment template |
| `.gitignore` | file | |
| `AGENTS.md` | file | Repo agent instructions |
| `QUICKSTART.md` | file | Quick start guide |
| `README.md` | file | Main documentation |
| `agentos.yaml` | file | v4 Lite profiles (Tier 1 → archive) |
| `base/` | dir | agentboot templates (`AGENTS.md`, `CLAUDE.md`) |
| `bin/` | dir | `agentboot`, `skills-install.sh`, `claude-skills-bridge.sh` |
| `catalog/` | dir | `packages.json` (Tier 2 → archive) |
| `docs/` | dir | `harness-architecture.md`, `openclaw-plan.md` (Tier 1 → archive) |
| `exports/` | dir | Generated outputs, `.gitkeep` (Tier 1 → archive) |
| `future/` | dir | Deferred AgentOS features (Tier 1 → archive) |
| `global/` | dir | Machine baseline `AGENTS.md` |
| `install.sh` | file | Primary entrypoint |
| `mcp/` | dir | `mcp.json` (Tier 2 → archive) |
| `memory-vault/` | dir | Obsidian-style store (Tier 1 → archive) |
| `skills/` | dir | In-repo skills pointer (`README.md` only) |
| `skills-lock.json` | file | Project skill lock (stub at capture) |
| `skills.sources.yaml` | file | Upstream skill manifest |
| `src/` | dir | Python package `agent_bootstrap/` |
| `templates/` | dir | Workspace render overlays (Tier 1 → archive) |
| `tests/` | dir | pytest + shell tests |

## Second-level layout (abbreviated)

```
base/
  AGENTS.md, CLAUDE.md, README.md
bin/
  agentboot, claude-skills-bridge.sh, skills-install.sh
catalog/
  packages.json
docs/
  harness-architecture.md, openclaw-plan.md
exports/
  .gitkeep
future/
  README.md
global/
  AGENTS.md
mcp/
  mcp.json
memory-vault/
  README.md, active-context.md, preferences.md
  agent-relationships/, decisions/, lessons/, projects/
skills/
  README.md
src/agent_bootstrap/
  (cli, service, skills_installer, render, catalog, discovery, state, ui, …)
templates/
  .codexignore, AGENTS.md
tests/
  test_agentboot.sh, test_bootstrap_engine.py, test_claude_bridge.py
  test_skills_installer.py, test_skills_sources.py
```
