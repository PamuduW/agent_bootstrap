# Implementation phases — agent_bootstrap expansion

**Status:** Planning doc (2026-07-11). Not started.

**Related:**

| Doc | Role |
|-----|------|
| [stuff.md](./stuff.md) | Deferred capability map + archive inventory |
| [stuff2.md](./stuff2.md) | Day-to-day impact of deferred features (deep dive) |
| [harness-architecture.md](./harness-architecture.md) | Three-plane design + memory tiers 1–6 |
| [../README.md](../README.md) | Archive move log + pack → slim matrix |

**Next session:** Phase 1 implementation plan (menu relocation + unified `agentboot`).

---

## Verdict on this phase split

**Yes — this is a good setup.** Dependencies flow in the right direction:

```text
Phase 1 (UX + standalone)     →  no render/catalog dependency
Phase 2 (render + state)      →  needs stable entrypoints from Phase 1
Phase 3 (catalog + MCP)       →  needs render pipeline from Phase 2
Phase 4 (memory + graphs)     →  optional; does not block Phases 1–3
```

### Suggested tweaks (minor)

1. **Rename Phase 1 “TUI” mentally** — you are moving the **dotfiles Agents submenu** into `agent_bootstrap`, not restoring the archived package/workspace **Apply** TUI yet. That fuller control plane lands in **Phase 2** with tracked workspaces + CLI `interactive` / `all`.

2. **Order inside Phase 2** (when building):

   ```text
   agentos.yaml (live at repo root) → workspace render → tracked workspaces → CLI commands
   ```

   Profiles define export targets; render reads them; state remembers repos; CLI exposes the flows.

3. **`agentboot` grows by phase** — Phase 1 removes `--full` and keeps today’s `AGENTS.md` + `CLAUDE.md` copy. Copilot/Cursor/MCP outputs attach in Phase 2–3 as render matures. One command, behavior expands — your instinct is right.

4. **Phase 4: vault before Graphify** — populate Obsidian-style memory habits first; add Graphify when a specific large repo hurts. Enable `obsidian-memory` in `skills.sources.yaml` when the vault has real content.

5. **Explicitly out of these four phases** (harness tiers 4 & 6): Hermes/Proxmox, Mem0, Graphiti, GraphRAG — revisit only if markdown + vault + Graphify stop scaling.

---

## Phase 0 — current (slim bootstrap)

**Goal:** Single config repo for skills + global baseline + minimal repo scaffold. **Live today.**

| Piece | Location |
|-------|----------|
| Skills manifest + install | `skills.sources.yaml`, `./install.sh skills *` |
| Global baseline render | `global/AGENTS.md`, `./install.sh global` |
| Repo scaffold | `bin/agentboot` → `base/AGENTS.md`, `base/CLAUDE.md` |
| Agents UX | `dotfiles/scripts/menus/agents.sh` (to move in Phase 1) |
| Deferred reference | `archive/docs/stuff.md`, `archive/docs/stuff2.md` |

### Phase 0 follow-up — personal custom skills source (planned, not implemented)

Create a dedicated NPM/Skills-CLI-compatible repository for personal skills (including `co-council`). Once it exists and has a reviewed revision, add it as a normal source in `skills.sources.yaml` and install it with `npx skills -g` so its selected skills are represented in `~/.agents/.skill-lock.json` and validated as managed Codex links. Do not treat ad-hoc copies into `~/.agents/skills/` as equivalent; they remain user-managed until explicitly linked or moved into that source.

**Exit criteria:** `./install.sh doctor` clean; tests pass; dotfiles Agents menu works.

---

## Phase 1 — standalone UX + unified agentboot

**Goal:** `agent_bootstrap` works without dotfiles; dotfiles becomes a thin launcher.

### Scope

| Item | Intent |
|------|--------|
| **Bootstrap menu (from dotfiles)** | Move Agents submenu (`status`, `clone/update`, `bootstrap`, `skills`, `link`, `agentboot`, `doctor`) into this repo. Reuse or share menu primitives (`menu_simple`, descriptions, colors) — discuss at build time. |
| **Dotfiles integration** | Keep `agent_bootstrap_paths.sh` in dotfiles for sibling-path resolution. Main menu `--agents` delegates to `$AGENT_BOOTSTRAP_HOME/.../menu` (or `./install.sh menu`). |
| **Unified `agentboot`** | Drop `--minimal` / `--full` split. Default `agentboot` does the full scaffold *for this phase* (`AGENTS.md` + `CLAUDE.md`). Remove `--full` prompts from dotfiles menu. As later phases land, the same command gains Copilot/Cursor/MCP without new flags. |

### Not in Phase 1

- Package/workspace **Apply** TUI from archived `ui.py`
- Workspace render, catalog, MCP filter
- Restoring archived CLI subcommands

### Architecture sketch

```text
dotfiles/install.sh --agents
        │
        ▼
AGENT_BOOTSTRAP_HOME/install.sh menu   (new)
        │
        ├── status / doctor / bootstrap / skills / link
        └── agentboot (target dir prompt)
```

### Exit criteria

- Fresh clone: `./install.sh` + `./install.sh menu` usable with no dotfiles
- Dotfiles `--agents` calls into agent_bootstrap menu
- `agentboot` has no `--full`; docs and menus updated
- `AGENT_BOOTSTRAP_TUI=1` still works when piped via dotfiles `tee`

---

## Phase 2 — render engine + tracked workspaces

**Goal:** One canonical `AGENTS.md` per repo; generated compatibility files; batch re-apply.

### Scope

| Item | Intent |
|------|--------|
| **`agentos.yaml` profiles** | Promote `archive/agentos.yaml` → repo root (or `config/`). `safe-default` profile drives export policy. |
| **Workspace render** | Restore/adapt `render.py`: merge `global/AGENTS.md` + repo `## Project` → `CLAUDE.md`, Copilot instructions, Cursor rules. Generated files gitignored. |
| **Tracked workspaces** | Restore/adapt `state.py` + `discovery.py`: remember git roots; `workspace` / `all` re-render on demand. |
| **CLI commands** | Re-enable: `workspace`, `all`, `interactive` (package/workspace Apply TUI), wire through `install.sh` + `src/cli.py`. |

### Build order (recommended)

1. `agentos.yaml` at live path + loader in Python  
2. Workspace render (single repo)  
3. Operator state + discovery  
4. CLI + optional interactive Apply menu  
5. Extend `agentboot` to invoke workspace render (still one command)

### Exit criteria

- `./install.sh workspace ~/Dev/my-app` merges and writes generated surfaces  
- `./install.sh all ~/Dev` updates every tracked repo  
- `agentboot` in a git repo runs render path (not just static copy)  
- Tests cover merge + gitignore idempotency  

**Reference:** git history for `archive/src/agent_bootstrap/{render,state,discovery,ui}.py`; config in `archive/templates/`, `archive/agentos.yaml`.

---

## Phase 3 — catalog + MCP bundles

**Goal:** Curated packages drive which MCP servers and artifacts appear per profile/workspace.

### Scope

| Item | Intent |
|------|--------|
| **Package catalog** | Promote `archive/catalog/packages.json`; restore catalog load/filter + `import-local` / `remove-managed`. |
| **MCP bundle render** | Filter `archive/mcp/mcp.json` by enabled packages’ `mcp_keys`; write global and per-workspace `.cursor/mcp.json`. |

### Depends on Phase 2

MCP render hooks into the same `render.py` / `agentos.yaml` export targets (`cursor` → `mcp.json`).

### Exit criteria

- Enable/disable package → MCP subset updates on next render  
- `import-local` copies Cursor plugin cache artifact into catalog  
- Doctor validates MCP ownership vs catalog  

---

## Phase 4 — long-term memory

**Goal:** Durable human-owned context beyond per-repo `AGENTS.md`.

### Scope

| Item | Intent |
|------|--------|
| **Obsidian memory vault** | Populate `archive/memory-vault/` structure (`active-context.md`, `decisions/`, `lessons/`, …). Agents draft; you commit. Optional: enable `obsidian-memory` in `skills.sources.yaml`. |
| **Graphify** | On-demand per large repo (infra/K8s/TF). Enable `graphify` skill when upstream ships Agent Skills layout; manual `graphify build` until then. Not always-on on laptop. |

### Not in Phase 4 (unless triggers hit)

| Item | Trigger |
|------|---------|
| Hermes + SQLite FTS | Need background memory while laptop off (tier 4) |
| Mem0 / Graphiti / GraphRAG | Markdown + vault + Graphify stop scaling (tier 6) |

### Exit criteria

- Vault has real content you use weekly  
- Graphify run documented for at least one painful repo  
- Agents read small vault slices / exports — not whole vault every session  

---

## Cross-phase dependency diagram

```text
                    ┌─────────────────────────────────────┐
                    │  Phase 0 (live): skills + agentboot │
                    └──────────────────┬──────────────────┘
                                       │
                    ┌──────────────────▼──────────────────┐
                    │  Phase 1: menu here + agentboot UX  │
                    └──────────────────┬──────────────────┘
                                       │
         ┌─────────────────────────────▼─────────────────────────────┐
         │  Phase 2: agentos.yaml → render → tracked workspaces → CLI │
         └─────────────────────────────┬─────────────────────────────┘
                                       │
                    ┌──────────────────▼──────────────────┐
                    │  Phase 3: catalog → MCP bundle render │
                    └──────────────────┬──────────────────┘
                                       │
                    ┌──────────────────▼──────────────────┐
                    │  Phase 4: memory vault + Graphify   │
                    └─────────────────────────────────────┘

     OUT OF SCOPE (separate projects): Hermes / Proxmox / Mem0 / Graphiti
```

---

## Mapping: deferred table → phases

| Deferred capability ([stuff.md](./stuff.md)) | Phase |
|-----------------------------------------------|-------|
| Interactive control-plane TUI (full Apply) | 2 |
| Workspace render | 2 |
| Tracked workspaces | 2 |
| `agentos.yaml` profiles | 2 |
| CLI commands (`workspace`, `all`, `interactive`, …) | 2 |
| Package catalog | 3 |
| MCP bundle render | 3 |
| Obsidian memory vault | 4 |
| Graphify | 4 |
| `agentboot --full` (concept) | 1–3 → unified `agentboot` |

---

## Phase 1 planning checklist (next session)

- [ ] Menu library: copy vs shared package vs git submodule from dotfiles  
- [ ] Entrypoint name: `./install.sh menu` vs `bin/agent-menu`  
- [ ] What stays in dotfiles: `agent_bootstrap_paths.sh`, clone URL allowlist, one-line `--agents` delegate  
- [ ] `agentboot` flag removal + test updates  
- [ ] README / QUICKSTART / dotfiles `AGENTS.md` path updates  

---

## Changelog

| Date | Change |
|------|--------|
| 2026-07-11 | Initial phase map; `stuff.md` / `stuff2.md` moved to `archive/docs/` |
