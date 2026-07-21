# Agentbot

Personal AI-agent tooling installer. The Git repository and clone directory remain
`agent_bootstrap`; the installed product and command are Agentbot / `agentbot`.

- **Skills** — curated upstreams in [`skills.sources.yaml`](skills.sources.yaml), installed globally via [`npx skills`](https://www.npmjs.com/package/skills)
- **agentbot boot** — register a folder or Git repo and render `AGENTS.md` plus selected agent surfaces from [`base/`](base/)
- **Global baseline** — machine-level policy in [`global/AGENTS.md`](global/AGENTS.md), rendered to agent home dirs

Deferred features and the phased expansion plan live in [`archive/`](archive/README.md) ([stuff3.md](archive/docs/stuff3.md)).

## Current roadmap status

Phase 0, Phase 1, and the Phase 2 workspace pipeline are complete. The live
surface includes the standalone Agentbot menu, profile-driven workspace
rendering, local workspace registration/resync, global baseline rendering,
curated skills management, and the Dotfiles sibling bridge. The detailed,
implementation-aware roadmap is
[`archive/docs/stuff3.md`](archive/docs/stuff3.md).

The supported menu entrypoints are `./install.sh` on a controlling TTY and
`agentbot` after installation. `./install.sh menu` is not a separate command.

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
./install.sh install
```

**Standalone:** clone anywhere; `AGENTBOT_HOME` derives from the clone path:

```bash
git clone <your-remote>/agent_bootstrap /any/path/agent_bootstrap
cd /any/path/agent_bootstrap
./install.sh install
```

Explicit install runs skills install → Claude bridge → global render → doctor, and
symlinks `bin/agentbot` → `~/bin/agentbot`. Ensure `~/bin` is on your PATH.
Running `./install.sh` or `agentbot` without arguments requires a controlling TTY
and opens the Agentbot menu when that menu is available.

`AGENTBOT_HOME` is exported from the clone path (not from `.env`). The active
configuration directory is `${XDG_CONFIG_HOME:-$HOME/.config}/agentbot`. For a
standalone install, add the repository path to your shell profile if needed:

```bash
export AGENTBOT_HOME="/any/path/agent_bootstrap"
```

## Skills

Curated upstreams are listed in [`skills.sources.yaml`](skills.sources.yaml). Install or refresh:

```bash
./install.sh skills install   # idempotent install from manifest, then refresh Claude/Codex outputs
./install.sh skills update    # npx skills update -g + Claude bridge + Codex symlinks
./install.sh update --dry-run # repo-first reconciliation preview
./install.sh update --yes     # confirmed repo-first reconciliation
./install.sh skills list
./install.sh skills doctor
```

Agent policy does not maintain a hardcoded list of skill names. Before choosing
a skill, an agent should use the active harness's discovery mechanism and select
only compatible capabilities for the current task. Agentbot's installed
inventory is available with `agentbot skills list` (or
`./install.sh skills list`); `skills.sources.yaml` and
`~/.agents/.skill-lock.json` remain the durable source records.

### Lockfile strategy

| File | Role |
| ---- | ---- |
| [`skills-lock.json`](skills-lock.json) | **Project stub** — committed placeholder (`sources: []`, v1). Not populated by `-g` installs. |
| `~/.agents/.skill-lock.json` | **Authoritative for global installs** — v3 per-skill pins written by `npx skills add … -g`. |

Do not copy the global lock into the repo by hand (schemas differ). **Future:** populate `skills-lock.json` from the manifest for CI/reproducible project-scoped installs.

See [`archive/LOCKFILE-NOTES.md`](archive/LOCKFILE-NOTES.md) for historical notes.

To add a skill: add an entry under `sources` in `skills.sources.yaml`, then run `./install.sh skills install` (not `update`).

GitHub skill sources are shallow-cloned locally with a two-minute bound before `npx skills` installs from that checkout. This avoids the Skills CLI's unbounded GitHub API preflight on fresh machines. The subsequent `npx` operation has a 15-minute bound; set `AGENTBOT_NPX_TIMEOUT_SECONDS` to a positive number of seconds when needed. Clone failures now report a Git error instead of silently waiting for the outer timeout.

### Manual skill folders

A folder copied into `~/.agents/skills/` is a valid **manual local skill**. `./install.sh global` (and both skill install/update commands) links every valid local skill into Codex and Claude without replacing conflicting user-owned links. Manual skills remain distinct from managed installs: `doctor` and `status` report them as available-but-not-reproducible until their repository and selected skill names are added to `skills.sources.yaml` and installed through `npx skills`, which records them in the global lock.

## Workspace setup and repository scaffolding

Set up the current directory. With no selectors, Agentbot creates or preserves
the canonical `AGENTS.md`, `CLAUDE.md`, Copilot instructions, and the Cursor
rule, then records the canonical folder or Git root in local XDG state:

```bash
cd ~/Dev/my-project
agentbot boot
agentbot boot --claude             # AGENTS.md + CLAUDE.md
agentbot boot --copilot            # AGENTS.md + Copilot instructions
agentbot boot --cursor             # AGENTS.md + .cursor/rules/agentbot-policy.mdc
agentbot boot --codex              # AGENTS.md only; Codex consumes AGENTS.md
```

All write-capable workspace commands preview by default; `--yes` applies a
render. Existing unmarked compatibility files are preserved and receive a
review copy instead of blocking the render. An existing unmarked `AGENTS.md`
is preserved as custom policy and receives `AGENTS_temp.md` containing the
current base template. The project-owned `## Project` section remains outside
Agentbot's managed baseline block.

Review copies use the target stem, for example `CLAUDE_temp.md`,
`.github/copilot-instructions_temp.md`, and
`.cursor/rules/agentbot-policy_temp.mdc`. Each generated review copy stores a
SHA-256 marker in its first HTML comment. An untouched copy is refreshed in
place when the template changes; an edited stale copy is preserved and the
next available suffix (`_temp_1`, `_temp_2`, and so on) is created. Existing
original files are never overwritten just because they conflict.

```bash
agentbot workspace ~/Dev/existing-project
agentbot workspace --yes ~/Dev/existing-project
agentbot workspaces
agentbot resync --dry-run --all
agentbot resync --yes --all
agentbot resync --yes ~/Dev/existing-project
```

Workspace records are stored privately at
`${XDG_CONFIG_HOME:-$HOME/.config}/agentbot/workspaces.json`; they are not
written into projects or tracked by Git. Cursor's generated rule is
`.cursor/rules/agentbot-policy.mdc`, not a skill installer.

Templates: [`base/AGENTS.md`](base/AGENTS.md), [`base/CLAUDE.md`](base/CLAUDE.md). Machine baseline stays in `global/AGENTS.md`.
The same preserved-original and review-copy behavior applies to the rendered
files under `~/.codex` and `~/.claude`.

Re-link after moving the clone by running `./install.sh install` explicitly.

## Other commands

```bash
./install.sh global     # re-render ~/.codex and ~/.claude outputs from global/AGENTS.md
./install.sh status     # skills count + global baseline status
./install.sh doctor     # validate manifest, locks, and managed agent skill links
./install.sh update --dry-run # preview source-owned skill changes
./install.sh workspace ~/Dev/existing-project
./install.sh workspaces
./install.sh resync --dry-run --all
```

The public Agentbot command matrix is:

```text
agentbot                  # TTY menu; headless invocation fails with guidance
agentbot status [--json]
agentbot install
agentbot update [--dry-run] [--yes]
agentbot token
agentbot boot [--claude] [--copilot] [--cursor] [--codex] [--profile NAME] [target]
agentbot workspace [--profile NAME] [--targets LIST] [--yes] PATH
agentbot workspaces
agentbot resync [--all | PATH ...] [--yes | --dry-run]
agentbot doctor
agentbot dotfiles
agentbot help
```

The interactive **Command Lib**, `agentbot help`, and the bootstrap help all
show the complete supported command, option, configuration, output, and
integration reference. They are read-only and use the same catalog.

`agentbot update` is repo-first: dirty, detached, diverged, missing-upstream,
declined, or failed pull states stop before skills work. A confirmed
reconciliation never runs `git add`, `git commit`, or `git push`; tracked
manifest or policy changes are handed back as `applied-with-local-changes` for
the user to review and commit or discard.

From the TTY menu, **Update** checks the repository first. If it is behind, a
colored repository table is shown before the fast-forward pull prompt; after a
pull, press Enter to restart `install.sh` from the updated checkout. Once the
repository is current, the menu shows the colored Agentbot status and
reconciliation preview, asks whether to apply it, prints the result report,
and pauses back at the menu.

## Repo layout

```text
agent_bootstrap/
├── install.sh
├── skills.sources.yaml
├── skills-lock.json
├── bin/                  # agentbot, skills-install, claude-skills-bridge
├── agentos.yaml          # safe-default workspace profile
├── base/                 # canonical Agentbot policy templates
├── global/AGENTS.md      # machine-level baseline (authored)
├── src/                  # slim Python CLI (cli.py, service.py, …)
├── tests/
└── archive/              # deferred capabilities — docs/stuff*.md, see archive/README.md
```

## Tests

```bash
python3 -m unittest discover -s tests
bash tests/test_agentbot.sh
```

## Deferred / archived

Deferred capabilities are documented in [`archive/docs/stuff.md`](archive/docs/stuff.md); the build roadmap is [`archive/docs/stuff3.md`](archive/docs/stuff3.md).

Legacy pre-slim code is recoverable from Git history; the retained design and
configuration references are documented in [`archive/README.md`](archive/README.md).
