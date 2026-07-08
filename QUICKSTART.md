# Quickstart

Get the agent config plane running on a new machine in a few steps.

## Prerequisites

- **Git** — to clone this repo
- **Python 3** — control-plane engine (`install.sh` requires it)
- **Node.js + npx** — Vercel `skills` CLI for multi-agent skill installs

## 1. Clone and enter the repo

```bash
git clone <your-remote>/agent_bootstrap ~/Dev/agent_bootstrap
cd ~/Dev/agent_bootstrap
```

`AGENT_BOOTSTRAP_HOME` is derived from this clone path — not from `.env`. After install, add to your shell profile if you want it in every session:

```bash
export AGENT_BOOTSTRAP_HOME="$HOME/Dev/agent_bootstrap"
```

## 2. Optional: MCP environment variables

If you use MCP integrations that need credentials, copy the template and fill in values:

```bash
cp .env.example .env
# edit .env — see comments for each variable
```

Most servers in `mcp/mcp.json` (GitLab, Notion, Context7) authenticate via OAuth in the IDE. Env vars are only needed for servers or skills that require them — see `.env.example`.

## 3. Review the global baseline

Edit the canonical machine-level policy:

- [`global/AGENTS.md`](global/AGENTS.md)

Per-repo behavior belongs in each project's `AGENTS.md`, not in generated compatibility files.

## 4. Run the bootstrap installer

```bash
./install.sh
```

The interactive menu covers package enablement, workspace tracking, apply/render, status, and doctor.

For a scripted first run:

```bash
./install.sh skills install   # install curated upstream + personal skills
./install.sh global           # render ~/.codex and ~/.claude outputs
./install.sh workspace ~/Dev/my-repo   # track and render one repo
./install.sh doctor           # validate state
```

## 5. Understand skills flow

| File | Role |
|------|------|
| [`skills.sources.yaml`](skills.sources.yaml) | Upstream repos and skill names to install |
| [`skills/`](skills/) | Your personal authored skills (optional) |
| [`skills-lock.json`](skills-lock.json) | Pinned versions — commit after install |

Each upstream entry installs globally to Cursor, Codex, Claude Code, and GitHub Copilot:

```bash
npx skills add <repo> --skill <name> \
  -a cursor -a codex -a claude-code -a github-copilot -g -y
```

Update all sources later:

```bash
./install.sh skills update
```

## 6. Non-interactive commands

```bash
./install.sh status
./install.sh global
./install.sh workspace ~/Dev/my-repo
./install.sh all ~/Dev
./install.sh skills install
./install.sh skills update
./install.sh doctor
```

`workspace` expects the root of a git repository.

## 7. Generated outputs (do not edit)

The control plane renders these from canonical `AGENTS.md` sources:

- Global: `~/.codex/AGENTS.md`, `~/.claude/AGENTS.md`, `~/.claude/CLAUDE.md`
- Per repo: `CLAUDE.md`, `.github/copilot-instructions.md`, `.cursor/rules/bootstrap-skills.mdc`, `.cursor/mcp.json`

Re-run `./install.sh global` or `./install.sh workspace <path>` after changing authored files.

## 8. Verify with doctor

```bash
./install.sh doctor
```

Fixes common problems: missing workspaces, generated `AGENTS.md` in repos, duplicate MCP catalog keys.

## 9. Run tests

```bash
python3 -m unittest tests.test_bootstrap_engine
```

## 10. Memory vault (Stage 7)

Human-owned context lives in [`memory-vault/`](memory-vault/):

- `active-context.md` — what you're working on now
- `preferences.md` — stable preferences
- `decisions/` — decision log
- `lessons/` — lessons learned

Agents may draft; you approve before entries are canonical. See [`docs/harness-architecture.md`](../docs/harness-architecture.md) for how the vault fits the three-plane harness model.

## What's next

- **Deferred harness work** — opencode, Hermes/Proxmox, graph memory upgrades (Phases 7.2–7.4) — see [`future/README.md`](future/README.md)
- **Dotfiles** — boot-menu option 4 clones this repo and runs `./install.sh` automatically

See [`README.md`](README.md) for the full config-plane model and [`temp/archive/README.md`](../temp/archive/README.md) for legacy artifacts (outside this repo).
