# Harness Architecture — Three Planes

**Status:** Phase 7.1 (config plane) — canonical design doc  
**Scope:** Laptop CLI agents + `agent_bootstrap` config repo. Hermes/Proxmox **DEFERRED**.  
**Plan:** `docs/plan/plan7-agentic-harness.md` · **Verdicts:** `docs/plan/index.md` §2

---

## 1. Executive summary

Daily coding runs on **first-party CLI agents** in WSL (Codex, Claude Code, Copilot, Cursor) fed by a single **config plane** — the rebuilt `agent_bootstrap` repo — which owns skills, templates, MCP exports, and human-curated memory. There is **no always-on harness on the laptop** (16 GB RAM, WSL2). A future **control plane** (Hermes on a Proxmox home server) handles persistent memory, cron, and messaging when the laptop is off; that rollout is **explicitly out of scope** for this project and deferred until config + work planes are stable. Markdown, skills, and per-repo `AGENTS.md` already deliver ~80% of the value; every heavier layer must earn its place.

---

## 2. Three planes

```
┌─────────────────────────────────────────────────────────────────────────┐
│  CONTROL PLANE — DEFERRED                                               │
│  Proxmox VM/LXC on old desktop → Hermes Agent                           │
│  Persistent memory, cron, Telegram/Discord gateway, scoped sandboxes    │
│  OpenRouter + optional Ollama. Not daily coding. Not on the laptop.     │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ git sync (AGENTS.md, skills, vault)
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  CONFIG PLANE — LIVE (agent_bootstrap)                                  │
│  Skills catalog · base/ templates · install.sh · MCP/agents exports     │
│  memory-vault/ (human-owned Obsidian) · global/AGENTS.md baseline       │
│  Single source of truth for every agent on every machine                │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ agentboot · npx skills · install.sh
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  WORK PLANE — LIVE (laptop WSL)                                         │
│  Codex CLI · Claude Code · GitHub Copilot · Cursor CLI                  │
│  Per-repo AGENTS.md + CLAUDE.md. No daemon. No vector DB. No Hermes.    │
└─────────────────────────────────────────────────────────────────────────┘
```

**Rule:** Config plane is the keystone. Control and work planes are consumers, not competing sources of truth.

---

## 3. Laptop constraint

| Constraint | Rationale |
|---|---|
| **CLI agents only** | Native first-party tools; best ToS compliance and lowest surprise |
| **No always-on harness** | Hermes, OpenClaw gateway, or similar daemons are wrong fit for 16 GB WSL |
| **No heavy local runtime** | No Ollama-as-default, no embedding pipelines, no Graphify rebuild hooks on laptop |
| **Design before infra** | Phase 7.1 is documentation + config hardening; server is a separate project |

The laptop is a **work terminal**, not a home lab. Background automation waits for the deferred control plane.

---

## 4. Memory tiers (1–6)

From `docs/plan/index.md` §2.4. Add layers only when the previous one hurts.

| Tier | Mechanism | Status |
|------|-----------|--------|
| **1** | Per-repo `AGENTS.md` + `CLAUDE.md` via `agentboot` | **LIVE** — Stage 6 complete |
| **2** | Global skills via `npx skills` (`skills.sources.yaml`) | **LIVE** — Stage 5 complete |
| **3** | Obsidian vault in repo (`memory-vault/`: active-context, preferences, decisions/, lessons/) | **STRUCTURE LIVE** — human-owned; agents draft, you approve |
| **4** | Hermes `MEMORY.md` + SQLite FTS on server (`write_approval: true`) | **DEFERRED** — needs Phase 7.3 + Proxmox |
| **5** | Graphify on-demand for large infra/K8s/TF repos | **DEFERRED** — trigger: codebase too large for grep + AGENTS.md |
| **6** | Mem0 / Graphiti / GraphRAG cross-machine semantic recall | **DEFERRED** — trigger: markdown stops scaling (~50+ file graphs, cross-machine recall) |

**Do not start with a vector DB.** Ops burden before curated facts exist.

---

## 5. Skills strategy

**Primary installer:** [Vercel `npx skills`](https://github.com/vercel-labs/skills) — installs to each agent's canonical path in one command.

**Claude bridge:** Claude Code reads `~/.claude/skills/` only — not `~/.agents/skills/`. Always pass `-a claude-code` (or use the wrapper in `install.sh`) so Cursor/Codex/Copilot and Claude stay in sync. No hand-copying.

**Content sources:**
- Curated manifest: `skills.sources.yaml` (superpowers, devops, research, etc.)
- Personal pack: fork of Akindu's `my-agent-skills` for your own skills
- Ad hoc: `npx skills add <repo> --skill <name>` from any compliant repo

**Config repo role:** `agent_bootstrap` declares what to install and wraps `npx skills`; it does not reinvent a package manager.

---

## 6. Per-repo bootstrap (`agentboot`)

```
new/cloned repo
      │
      ▼
  agentboot              # default: --minimal
      │
      ├─► ./AGENTS.md     ← base/AGENTS.md (env header, skill tables, ## Project overlay)
      ├─► ./CLAUDE.md     ← base/CLAUDE.md (@AGENTS.md pointer for Claude Code)
      │
      ▼ (optional)
  agentboot --full
      │
      ├─► .github/copilot-instructions.md
      ├─► .cursor/rules/ …
      └─► MCP workspace exports (render.py)

Idempotent: skips existing files unless --force.
PATH: ~/bin/agentboot (symlinked by install.sh).
```

**Convention:** `AGENTS.md` is the single authored instruction file. `CLAUDE.md`, Copilot, and Cursor outputs **point at it** — never duplicate conflicting rules.

**After bootstrap:** edit `## Project`, `git add`, optionally `./install.sh skills install` from the config repo.

---

## 7. Future phases (DEFERRED)

Recorded for when pain appears. **Do not execute in this project.**

### Phase 7.2 — Laptop work plane extras

| Item | Trigger to start |
|------|------------------|
| **opencode** + OpenRouter (`sk-or-`) | Deliberate multi-provider experiments or cheap worker models needed |
| **Planner → worker → reviewer** habit | Recurring tasks where strong model plans, cheap model executes, strong reviews |
| **Claude Code subscription** | When purchased; use first-party CLI only |

### Phase 7.3 — Home server / Hermes

| Item | Trigger to start |
|------|------------------|
| Proxmox VM/LXC (~1 GB+ for Hermes) | Phases 7.1–7.2 stable; user initiates separate server project |
| Hermes Docker + systemd gateway | Need background cron, messaging, or memory while laptop is off |
| Telegram/Discord gateway | Need phone reachability to control plane |
| Scoped sandboxes + `write_approval: true` | Before any production/client repo access |

### Phase 7.4 — Memory/graph upgrades

| Item | Trigger to start |
|------|------------------|
| **Graphify** rebuild on commit | Large infra/K8s/TF repo where structure queries burn too many tokens |
| **Mem0 MCP** | Cross-machine semantic recall beyond markdown + Hermes FTS |
| **Graphiti / GraphRAG** | FYP becomes memory/retrieval research; otherwise skip |

---

## 8. What NOT to do

| Anti-pattern | Why |
|---|---|
| **Pi (or any) subscription proxy** | Anthropic prohibits third-party OAuth; opencode removed Claude Pro OAuth Mar 2026; economics and ToS are fragile |
| **Vector DB on day one** | Ops before curated facts; tiers 1–3 cover most needs |
| **Hermes + OpenClaw both as control plane** | Pick one orchestrator; OpenClaw persona model (SOUL.md) is borrowable structure, not a second daemon |
| **Always-on harness on laptop** | Wrong resource profile; defeats WSL-as-terminal model |
| **Hermes as daily coding IDE** | Wrong tool; use work-plane CLIs for in-repo work |
| **Unsupervised memory writes** | Memory poisoning risk; approval-gated writes + weekly audit when tier 4 lands |
| **Full auto-routing / agent swarms** | Semi-manual planner→worker→reviewer is enough; chase automation only when manual flow hurts |

---

## 9. Cost and auth strategy

| Spend | Tool | Notes |
|-------|------|-------|
| Claude subscription | **Claude Code** CLI | First-party only; no proxy plugins |
| ChatGPT subscription | **Codex** CLI | First-party |
| GitHub Copilot | Copilot in VS Code / CLI | Where subscribed |
| Cursor | Cursor CLI / IDE | Where subscribed |
| Pay-per-token workers | **OpenRouter** (`sk-or-`) | Hermes (deferred), opencode experiments, cheap execution models |
| Free low-stakes | **Ollama on server** (deferred) | Not on laptop by default |

**Principle:** No single third-party auth hack is load-bearing. Subscriptions stay in first-party CLIs; OpenRouter is the shared fallback for experimentation and background workers.

---

## References

- Master verdicts: `docs/plan/index.md` §2
- Stage plan: `docs/plan/plan7-agentic-harness.md`
- Research: `docs/research/04-gpt-synthesis.md`, `docs/research/06-web-agentic-landscape.md`
- `agentboot`: `bin/agentboot`, `base/AGENTS.md`, `base/CLAUDE.md`
- Skills manifest: `skills.sources.yaml`, `install.sh`
