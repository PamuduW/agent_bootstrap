# agent_bootstrap

Personal bootstrap for AI agent tooling on a fresh machine:

- **Skills** — curated upstreams in [`skills.sources.yaml`](skills.sources.yaml), installed globally via [`npx skills`](https://www.npmjs.com/package/skills)
- **agentboot** — scaffold `AGENTS.md` + `CLAUDE.md` in any git repo from [`base/`](base/)
- **Global baseline** — machine-level policy in [`global/AGENTS.md`](global/AGENTS.md), rendered to agent home dirs

Deferred features (catalog, MCP bundles, workspace render, memory vault, interactive menus) live in [`archive/`](archive/README.md).

## Fresh machine

**Prerequisites:** Git, Python 3, Node.js (for `npx`). Install Python deps:

```bash
python3 -m pip install -r requirements.txt
```

### Clone paths

**With dotfiles (recommended):** clone as a **sibling** of the dotfiles repo so the Agents menu finds the canonical path:

```text
parent/
├── dotfiles/
└── agent_bootstrap/    # e.g. ~/Dev/agent_bootstrap next to ~/Dev/dotfiles
```

```bash
git clone <your-remote>/agent_bootstrap ~/Dev/agent_bootstrap   # sibling of dotfiles
cd ~/Dev/agent_bootstrap
./install.sh
```

**Standalone:** clone anywhere; `AGENT_BOOTSTRAP_HOME` derives from the clone path:

```bash
git clone <your-remote>/agent_bootstrap /any/path/agent_bootstrap
cd /any/path/agent_bootstrap
./install.sh
```

When dotfiles is also installed, set `AGENT_BOOTSTRAP_ALLOW_OVERRIDE=1` only if you intentionally use a non-sibling path.

Default bootstrap runs: skills install → Claude bridge → global render → doctor, and symlinks `bin/agentboot` → `~/bin/agentboot`. Ensure `~/bin` is on your PATH.

`AGENT_BOOTSTRAP_HOME` is exported from the clone path (not from `.env`). With a sibling clone next to dotfiles, dotfiles sets this automatically. For standalone installs, add to your shell profile:

```bash
export AGENT_BOOTSTRAP_HOME="/any/path/agent_bootstrap"
```

## Skills

Curated upstreams are listed in [`skills.sources.yaml`](skills.sources.yaml). Install or refresh:

```bash
./install.sh skills install   # idempotent install from manifest
./install.sh skills update    # npx skills update -g + Claude bridge + Codex symlinks
./install.sh skills list
./install.sh skills doctor
```

### Lockfile strategy

| File | Role |
| ---- | ---- |
| [`skills-lock.json`](skills-lock.json) | **Project stub** — committed placeholder (`sources: []`, v1). Not populated by `-g` installs. |
| `~/.agents/.skill-lock.json` | **Authoritative for global installs** — v3 per-skill pins written by `npx skills add … -g`. |

Do not copy the global lock into the repo by hand (schemas differ). **Future:** populate `skills-lock.json` from the manifest for CI/reproducible project-scoped installs.

See [`archive/LOCKFILE-NOTES.md`](archive/LOCKFILE-NOTES.md) for historical notes.

To add a skill: add an entry under `sources` in `skills.sources.yaml`, then run `./install.sh skills install` (not `update`).

## agentboot

Scaffold base agent files in any git repo:

```bash
cd ~/Dev/my-project
agentboot              # AGENTS.md + CLAUDE.md (skip if exists)
agentboot --force      # overwrite existing files
```

Templates: [`base/AGENTS.md`](base/AGENTS.md), [`base/CLAUDE.md`](base/CLAUDE.md). Machine baseline stays in `global/AGENTS.md`.

Re-link after moving the clone:

```bash
./install.sh link-agentboot
```

## Other commands

```bash
./install.sh global     # re-render ~/.codex and ~/.claude outputs from global/AGENTS.md
./install.sh status     # skills count + global baseline status
./install.sh doctor     # validate skills manifest and global baseline
```

## Repo layout

```text
agent_bootstrap/
├── install.sh
├── skills.sources.yaml
├── skills-lock.json
├── bin/                  # agentboot, skills-install, claude-skills-bridge
├── base/                 # agentboot templates
├── global/AGENTS.md      # machine-level baseline (authored)
├── src/agent_bootstrap/  # slim Python CLI
├── tests/
└── archive/              # deferred capabilities — see archive/README.md
```

## Tests

```bash
python3 -m unittest discover -s tests
bash tests/test_agentboot.sh
```

## Deferred / archived

Workspace render, package catalog, MCP filtering, memory vault, interactive control-plane menus, and `agentboot --full` coupling were moved to [`archive/`](archive/README.md). Restore from there if you need those workflows.

Legacy v1 vendored assets (outside this repo) remain at [`../temp/archive/`](../temp/archive/) for history only.
