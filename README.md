# agent_bootstrap

Bootstrap-first control plane for multi-agent development environments.

This repo now treats agent configuration as a layered system instead of a
single shell script that mixes discovery, selection, rendering, and deployment.
The goal is one canonical authored `AGENTS.md` per scope, generated
compatibility outputs for each agent surface, curated package ownership, and a
terminal-first operator workflow.

## Core model

The architecture is split into four layers:

- `Catalog`: curated canonical packages declared in
  [`catalog/packages.json`](catalog/packages.json)
- `Discovery`: read-only detection of what exists in the repo and in local
  sources such as Cursor plugin cache
- `Selection`: operator-managed enablement state stored in `state/`
- `Render`: generated outputs for Codex, Claude, Cursor, Copilot, and future
  adapters

This keeps these concepts separate:

- managed package
- detected package
- enabled package
- applied package

## Canonical instruction files

There is exactly one authored instruction file per scope:

- global baseline: [`global/AGENTS.md`](global/AGENTS.md)
- project overlay: `<repo>/AGENTS.md`

Everything else is generated compatibility output:

- `CLAUDE.md`
- `.github/copilot-instructions.md`
- `.cursor/rules/bootstrap-skills.mdc`
- `.cursor/mcp.json`
- `~/.codex/AGENTS.md`
- `~/.claude/AGENTS.md`
- `~/.claude/CLAUDE.md`

Generated files are disposable outputs. Edit canonical `AGENTS.md` files
instead.

Canonical `AGENTS.md` changes are hash-tracked in `state/audit.log` when the
control plane renders global or workspace outputs.

## Current implementation

The new engine lives in [`src/agent_bootstrap`](src/agent_bootstrap).

Key modules:

- `catalog.py`: loads curated package metadata and repo-owned artifacts
- `discovery.py`: scans managed repo packages and local Cursor cache
- `state.py`: stores enablement, tracked workspaces, and audit history
- `render.py`: writes compatibility outputs for supported surfaces
- `service.py`: high-level orchestration for status, selection, and apply flows
- `cli.py`: terminal-first command interface

`install.sh` is now a thin launcher for the Python control plane.

## Operator workflow

Interactive mode:

```bash
./install.sh
```

Non-interactive commands:

```bash
./install.sh status
./install.sh global
./install.sh workspace /path/to/repo
./install.sh all /path/to/parent
./install.sh import-local <package-id>
./install.sh remove-managed <package-id>
./install.sh delete-local <package-id>
./install.sh doctor
```

What they do:

- `status`: show managed, detected, enabled, and tracked state counts
- `global`: render global Codex, Claude, and Cursor outputs from
  `global/AGENTS.md`
- `workspace`: track a repo and render workspace outputs from merged global +
  repo `AGENTS.md` at a git repository root
- `all`: track and render every git repo under a parent directory, then refresh
  global outputs
- `import-local`: copy a detected local package from Cursor cache into this repo
  and add/update its managed catalog entry
- `remove-managed`: remove a managed package from this repo catalog and repo
  artifacts
- `delete-local`: delete a detected local package from the local Cursor cache
- `doctor`: validate tracked workspaces and catalog state for common problems

## Repo layout

```text
agent_bootstrap/
├── install.sh
├── catalog/
│   └── packages.json
├── docs/
│   └── openclaw-plan.md
├── global/
│   └── AGENTS.md
├── src/
│   └── agent_bootstrap/
├── state/
├── skills/
├── rules/
├── commands/
├── agents/
├── hooks/
└── templates/
```

## OpenClaw

OpenClaw is planned as a future adapter, not the current foundation. The
forward plan is captured in [`docs/openclaw-plan.md`](docs/openclaw-plan.md).

The intent is to map OpenClaw onto the same canonical global/repo `AGENTS.md`
model rather than creating a second authored policy system.

## Tests

Run the current foundation tests with:

```bash
python3 -m unittest tests.test_bootstrap_engine
```
