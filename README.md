# Agentbot

Agentbot is a local bootstrap CLI for agent policy, curated Agent Skills, and
registered workspace outputs. It keeps policy in canonical Markdown, renders
provider-specific compatibility files, and makes mutating operations explicit.

Use `./install.sh` from a checkout or `agentbot` after installation. Run
`agentbot help` for the command index and `agentbot help COMMAND` for details.

## Requirements

- Bash, Git, Python 3, and PyYAML
- Node.js, npm, and `npx` for managed skill sources
- optional `graphify` and `boost` CLIs installed by Dotfiles

If PyYAML is unavailable, install the repository requirements in a local
environment:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## Quick start

```bash
git clone <your-remote>/agentbot ~/agentbot
cd ~/agentbot
./install.sh install
```

Install validates the checkout, installs enabled skill sources, refreshes
optional Graphify and Boost integrations when their CLIs exist, renders global
outputs, runs Doctor, and links `bin/agentbot` to `~/bin/agentbot`. Ensure
`~/bin` is on `PATH`.

The repository is not copied. The installed launcher remains linked to the
checkout that ran install. Confirm the active checkout before maintenance:

```bash
command -v agentbot
readlink -f "$(command -v agentbot)"
```

Private state is stored under
`${XDG_CONFIG_HOME:-$HOME/.config}/agentbot`, not in the repository.

## Common workflows

```bash
agentbot                         # open the interactive menu
agentbot status                 # inspect managed state
agentbot doctor                 # validate skills, links, and outputs
agentbot update --dry-run       # preview repository and lifecycle changes
agentbot update                 # confirm and apply an update
agentbot full                   # install, then update
agentbot boot /path/to/repo     # render and register a workspace
agentbot workspaces             # list registered workspaces
agentbot resync --dry-run --all # preview every registered workspace
agentbot token                  # manage the optional private GitHub token
```

The menu and direct CLI share the same command model and lifecycle code. Token
input is silent, and normal output shows only a fingerprint.

## Skills

[`skills.sources.yaml`](skills.sources.yaml) is the canonical source manifest.
Global installs and pins live under `~/.agents/`; the committed
[`skills-lock.json`](skills-lock.json) is a project-level stub, not a copy of
the global lock.

```bash
./install.sh skills install
./install.sh skills update
./install.sh skills list
./install.sh skills doctor
./install.sh skills prune             # preview source reconciliation
./install.sh skills prune --yes       # remove selected managed candidates
./install.sh skills remove-manual     # preview user-placed skills
```

Graphify is installed through its own CLI and is not a curated Git source.
Dotfiles owns the Graphify and Boost binaries; Agentbot owns their assistant
integration. See [Skills and integrations](docs/skills.md) for source syntax,
lock ownership, pruning rules, and integration policy.

## Workspaces

`base/AGENTS.md` is the canonical project scaffold. Agentbot always maintains
an `AGENTS.md` managed block and can render Claude and Cursor compatibility
surfaces. Project-owned content outside the marked block is preserved, and an
unmarked custom `AGENTS.md` is not overwritten.

A successful apply registers the canonical workspace path in private local
state. Workspace and resync operations preview by default; `--yes` authorizes
writes. Removing a registry entry never deletes workspace files.

`global/AGENTS.md` is the authored machine baseline. Generated global Codex and
Claude files must be refreshed through Agentbot rather than edited directly.
See [Workspaces and rendering](docs/workspaces-and-rendering.md).

## Documentation

- [Technical documentation index](docs/README.md)
- [Architecture](docs/architecture.md)
- [Skills and integrations](docs/skills.md)
- [Workspaces and rendering](docs/workspaces-and-rendering.md)
- [Lifecycle and updates](docs/lifecycle-and-updates.md)
- [Validation](docs/validation.md)
- [Roadmap](docs/roadmap.md)
- [Archived MCP research inputs](archive/docs/README.md)
- [Quick start](QUICKSTART.md)

## Development

Python owns lifecycle behavior. Bash is limited to bootstrap, repository
self-update, terminal presentation, secret scoping, and process adapters.
Change canonical sources rather than rendered outputs, and keep Dotfiles-owned
binary installation separate from Agentbot-owned integration.

Run the complete local gate before handing off a change:

```bash
env -u NO_COLOR bash tests/run.sh
```

For Ruff and coverage checks matching CI, put the development tools in a local
virtual environment:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt -r requirements-dev.txt
PATH="$PWD/.venv/bin:$PATH" env -u NO_COLOR bash tests/run.sh
```
