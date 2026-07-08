# agent_bootstrap

Bootstrap-first **config plane** for multi-agent development environments.

This repo is the source of truth for machine-level agent policy, curated upstream
skills, MCP server config, and generated compatibility outputs for Codex, Claude
Code, Cursor, and GitHub Copilot. It replaces the old v1 model (vendored plugin
mirrors + sync menu) with a layered control plane and Vercel [`npx skills`](https://www.npmjs.com/package/skills)
for skill installation.

## What this repo does

On a fresh machine (or after `git pull`):

1. **Bootstrap** — `./install.sh` checks dependencies, exports `AGENT_BOOTSTRAP_HOME` from the clone location, installs curated skills globally, and renders AGENTS.md / MCP exports.
2. **Curate** — you edit canonical instruction files and `skills.sources.yaml`; the installer materializes skills and compatibility surfaces.
3. **Validate** — `./install.sh doctor` checks catalog, workspaces, and instruction-file hygiene.

v0.1 scope: skills install/update, AGENTS.md exports, and doctor. Hermes, opencode, and full AgentOS features are deferred — see [`future/README.md`](future/README.md).

## Config-plane model

The architecture separates concerns into layers:

| Layer | Role | Source |
|-------|------|--------|
| **Catalog** | Curated package metadata and MCP ownership | [`catalog/packages.json`](catalog/packages.json) |
| **Discovery** | Read-only detection of repo and Cursor cache packages | Python `discovery.py` |
| **Selection** | Operator enablement state | `state/` (gitignored) |
| **Render** | Generated compatibility outputs per agent surface | Python `render.py` |
| **Skills sources** | Curated upstream repos + personal pack | [`skills.sources.yaml`](skills.sources.yaml), [`skills/`](skills/) |

Keep these concepts distinct:

- **Managed** — listed in `catalog/packages.json`
- **Detected** — found in repo artifacts or local Cursor cache
- **Enabled** — selected for rendering
- **Applied** — enabled and rendered to agent paths

### Canonical instruction files

There is exactly one **authored** instruction file per scope:

- **Global baseline:** [`global/AGENTS.md`](global/AGENTS.md)
- **Project overlay:** `<repo>/AGENTS.md`

Everything else is **generated** compatibility output (do not hand-edit):

| Output | Purpose |
|--------|---------|
| `~/.codex/AGENTS.md` | Codex CLI global instructions |
| `~/.claude/AGENTS.md`, `~/.claude/CLAUDE.md` | Claude Code global instructions |
| `<repo>/CLAUDE.md` | Claude Code repo overlay |
| `<repo>/.github/copilot-instructions.md` | GitHub Copilot repo overlay |
| `<repo>/.cursor/rules/bootstrap-skills.mdc` | Cursor skill catalog rule |
| `<repo>/.cursor/mcp.json` | MCP servers (filtered by enabled packages) |

Canonical `AGENTS.md` changes are hash-tracked in `state/audit.log` when the control plane renders outputs.

## Skills: sources, install, and lockfile

### Personal pack

[`skills/`](skills/) holds **your authored skills** only — one folder per skill, each with a `SKILL.md`. Do not re-vendor upstream repos here.

The old 52+ vendored skill directories live in [`temp/archive/skills/`](../temp/archive/skills/) (outside this repo) for history only.

### Curated upstreams

[`skills.sources.yaml`](skills.sources.yaml) lists upstream GitHub repos and which skills to install. Each entry is installed globally to all four agents:

```bash
npx skills add <repo> --skill <name> \
  -a cursor -a codex -a claude-code -a github-copilot -g -y
```

`-a claude-code` is mandatory so skills reach Claude Code's skill paths. The installer may also bridge `~/.agents/skills/` → `~/.claude/skills/` when needed.

### Lockfile

[`skills-lock.json`](skills-lock.json) is the Vercel skills lockfile — **commit it**. It records pinned upstream versions for reproducible installs. Materialized skill trees under agent home directories are gitignored.

Refresh all sources:

```bash
./install.sh skills update
# or: python3 -m src.agent_bootstrap.cli skills update
```

## Bootstrap entrypoint

[`install.sh`](install.sh) is the machine-facing entrypoint. It:

1. Resolves the repo root and exports **`AGENT_BOOTSTRAP_HOME`** (see below)
2. Checks for `python3` and `node`/`npx`
3. Dispatches to the Python control plane and skills installer

```bash
./install.sh                  # interactive menu
./install.sh status           # show managed/detected/enabled counts
./install.sh global           # render global Codex/Claude outputs
./install.sh workspace <path> # track a git repo and render workspace outputs
./install.sh all <parent>     # render every git repo under a parent dir
./install.sh skills install   # install from skills.sources.yaml + personal pack
./install.sh skills update    # refresh all upstream skills
./install.sh doctor           # validate catalog and tracked workspaces
```

Legacy flags `--status`, `--global`, `--workspace`, and `--all` still map to the subcommands above.

Package management commands (`import-local`, `remove-managed`, `delete-local`) remain available for Cursor-cache imports during the transition.

## agentboot — per-repo scaffold

[`bin/agentboot`](bin/agentboot) scaffolds base agent files in any git repo from templates in [`base/`](base/):

```bash
agentboot              # AGENTS.md + CLAUDE.md in CWD (idempotent; no overwrite without --force)
agentboot --minimal    # same as default — AGENTS.md + CLAUDE.md only
agentboot --full       # + .github/copilot-instructions.md + .cursor/rules pointers
agentboot --force      # overwrite existing files
```

**PATH setup:** `./install.sh` (bootstrap) and `./install.sh link-agentboot` symlink `bin/agentboot` → `~/bin/agentboot`. Ensure `~/bin` is on your PATH (dotfiles stow usually handles this).

From the dotfiles boot menu, option **Agents → Run agentboot in a repo** prompts for a target directory and optionally `--full`.

Templates live in `base/AGENTS.md` and `base/CLAUDE.md`. Machine-level baseline remains at `global/AGENTS.md`; per-repo overlays use the control plane in `src/`.

## AGENT_BOOTSTRAP_HOME

`AGENT_BOOTSTRAP_HOME` is **not** a secret and **not** set via `.env`. It is derived from wherever you clone this repo:

```bash
export AGENT_BOOTSTRAP_HOME="/path/to/agent_bootstrap"  # set by install.sh from repo root
```

`install.sh` exports it for the current session. For persistent shells, add the export to your dotfiles (e.g. `~/.bashrc`) pointing at your clone path — typically `~/Dev/agent_bootstrap`. See [`agentos.yaml`](agentos.yaml) for the config-plane contract.

Dotfiles boot-menu option 4 clones/pulls this repo and runs `./install.sh`.

## Doctor

`./install.sh doctor` validates:

- **Catalog** — no duplicate MCP key ownership across packages
- **Tracked workspaces** — paths exist, are git repos, and have authored (not generated) `AGENTS.md`
- **Permissions** — workspace directories are writable

Exit code `1` when issues are found; `0` when clean.

## Repo layout

```text
agent_bootstrap/
├── install.sh              # bootstrap entrypoint
├── agentos.yaml            # v4 Lite profiles and export targets
├── skills.sources.yaml     # curated upstream skill sources
├── skills-lock.json        # Vercel lockfile (committed)
├── skills/                 # personal authored skills pack
├── global/AGENTS.md        # machine-level baseline (authored)
├── templates/              # per-repo AGENTS.md overlay template
├── base/                   # agentboot templates (AGENTS.md, CLAUDE.md)
├── memory-vault/           # Obsidian memory store (Phase 7.1)
├── future/                 # deferred AgentOS features
├── catalog/packages.json   # managed package catalog + MCP provenance
├── mcp/mcp.json            # MCP server definitions
├── src/agent_bootstrap/    # Python control-plane engine
├── exports/                # generated outputs (gitignored)
├── state/                  # local operator state (gitignored)
├── docs/openclaw-plan.md   # future OpenClaw adapter plan
└── tests/
```

## Legacy archive (external)

Superseded v1 artifacts from the Stage 5 rebuild — vendored skills, imported rules/agents/commands/hooks, deprecated `sync.sh`, and stale docs — live at [`../temp/archive/`](../temp/archive/) **outside this repo**. Nothing there is live code. See [`temp/archive/README.md`](../temp/archive/README.md) for the full inventory.

Do not add new skills or sync scripts under the legacy archive.

## Memory vault (Stage 7 — Phase 7.1)

Human-owned Obsidian-compatible memory in [`memory-vault/`](memory-vault/):

| Path | Purpose |
|------|---------|
| `active-context.md` | Current focus and open threads |
| `preferences.md` | Stable working preferences |
| `decisions/` | ADR-style decision log |
| `lessons/` | Durable lessons learned |

Agents may draft entries; you approve before they become canonical. See [`docs/harness-architecture.md`](../docs/harness-architecture.md) for the three-plane model (config / work / control) and how the vault fits the config plane.

Phases 7.2–7.4 (opencode, Hermes/Proxmox, graph upgrades) are deferred — see [`future/README.md`](future/README.md).

## Configuration

- **[`agentos.yaml`](agentos.yaml)** — active profile, export targets, bootstrap home derivation
- **[`.env.example`](.env.example)** — optional MCP-related environment variables (copy to `.env` for local overrides)
- **[`QUICKSTART.md`](QUICKSTART.md)** — step-by-step first-run guide

## Tests

```bash
python3 -m unittest tests.test_bootstrap_engine
```

## OpenClaw

OpenClaw is planned as a future adapter, not the current foundation. See [`docs/openclaw-plan.md`](docs/openclaw-plan.md).
