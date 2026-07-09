# Agent Bootstrap

This repo is the **slim agent bootstrap** — skills install via `npx`, `agentboot` scaffolding, and a global `AGENTS.md` baseline. Agents editing *this* repo should treat it as a small CLI + shell entrypoint, not a full config plane.

## Repo structure

```
install.sh             Bootstrap entrypoint
skills.sources.yaml    Curated upstream skill sources (no in-repo skill pack)
skills-lock.json       Stub; global pins live in ~/.agents/.skill-lock.json
bin/                   agentboot, skills-install.sh, claude-skills-bridge.sh
base/                  agentboot templates (AGENTS.md, CLAUDE.md)
global/AGENTS.md       Machine-level baseline (authored)
src/agent_bootstrap/   Slim Python CLI (skills, global render, doctor)
tests/                 Foundation tests
archive/               Deferred Tier 1+2 assets — see archive/README.md
```

There is **no** `catalog/`, `mcp/`, `skills/` personal pack, `memory-vault/`, or workspace render in the slim path. Those live under [`archive/`](archive/README.md).

## Quick start

```bash
./install.sh
```

Scripted:

```bash
./install.sh skills install
./install.sh global
./install.sh doctor
```

## When asked to update skills

```bash
./install.sh skills update
```

Optionally re-run the Claude bridge explicitly: `bin/claude-skills-bridge.sh`.

## When asked to install or set up

```bash
./install.sh                    # full bootstrap (default)
./install.sh skills install
./install.sh link-agentboot     # symlink ~/bin/agentboot
```

Archived commands (`workspace`, `all`, `interactive`, `import-local`, catalog management) error with a pointer to `archive/README.md`.

## Skills model

- **Upstream only** — `skills.sources.yaml` → `npx skills add … -a cursor -a codex -a claude-code -a github-copilot -g`
- **Project lock (`skills-lock.json`)** — committed stub only (`sources: []`, v1); `-g` installs do not populate it
- **Global lock** — `~/.agents/.skill-lock.json` (v3) is authoritative for `-g` installs; do not hand-copy into the repo
- **Future** — populate project `skills-lock.json` for CI/reproducible project-scoped installs
- **Bridge** — `~/.agents/skills/` → `~/.claude/skills/` symlinks after install/update
- **Templates** — `base/AGENTS.md` skill table should match enabled manifest entries only; keep `graphify` and `obsidian-memory` out (both `enabled: false` in `skills.sources.yaml`)

Do not vendored upstream skills into this repo.

## AGENT_BOOTSTRAP_HOME

Derived from clone location — **not** set in `.env`. `install.sh` exports it from the repo root.

## Global vs per-repo agent files

- **Authored:** `global/AGENTS.md` (machine baseline), `<repo>/AGENTS.md` (project overlay via agentboot)
- **Generated:** `~/.codex/AGENTS.md`, `~/.claude/AGENTS.md`, `~/.claude/CLAUDE.md`, repo `CLAUDE.md` from agentboot — do not hand-edit as canonical policy

## Legacy archive (external)

Superseded v1 assets live at `../temp/archive/` (outside this repo). Do not add new work there.

## Guardrails

- `install.sh` is the primary interface
- Don't restore archived modules without re-wiring imports (see `archive/README.md`)
- Never run uninstall flows without explicit user request
- Don't modify `temp/archive/` unless asked
