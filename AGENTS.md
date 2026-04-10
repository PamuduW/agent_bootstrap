# Agent Bootstrap

This is the agent bootstrap repo — a bootstrap-first control plane for AI agent configurations across global and repo scopes.

## Repo structure

```
catalog/        Curated package catalog
global/         Canonical machine-level AGENTS.md baseline
src/            Python control-plane engine
state/          Local operator state and audit log (gitignored)
skills/         Skill definitions (SKILL.md + references)
rules/          Cursor rule files (.mdc)
mcp/            MCP server config
agents/         Subagent definitions (.md)
commands/       Command/prompt templates (.md)
hooks/          Lifecycle hook scripts
templates/      Templates for new projects
install.sh      Launcher for the interactive control plane
sync.sh         Deprecated alias to install.sh
```

## Quick start

```bash
./install.sh
```

## When asked to update or sync

Run the interactive menu with `./install.sh`, or use the non-interactive commands:

1. `./install.sh status`
2. `./install.sh global`
3. `./install.sh workspace <path>`
4. `./install.sh all <parent-dir>`
5. `./install.sh import-local <package-id>`
6. `./install.sh remove-managed <package-id>`
7. `./install.sh delete-local <package-id>`

## When asked to install or set up

### Interactive (recommended)
```bash
./install.sh
```

### Scripted / CLI
```bash
./install.sh global
./install.sh all ~/ATOM/
./install.sh workspace <path>
./install.sh status
```

## Plugin model

The current control plane distinguishes these states:

- **Managed**: the package exists in `catalog/packages.json`
- **Detected local**: the package exists in local sources such as Cursor plugin cache
- **Detected repo**: the repo already contains canonical assets for that package
- **Enabled**: the package is selected for rendering into generated outputs

## MCP provenance

Package ownership for MCP keys lives in `catalog/packages.json`, and rendered outputs only include keys owned by enabled managed packages.

## Workspace-level agent config files

The canonical authored files are:

- `global/AGENTS.md` for the machine-level baseline
- `<repo>/AGENTS.md` for repo-level overlays

Everything else is generated compatibility output.

## Conventions

- Skill directories: `skills/<package>-<skill-name>/`
- Rule files: `rules/<source-plugin>-<rule-name>.mdc`
- Agent/command files: `agents/<source-plugin>-<name>.md`, `commands/<source-plugin>-<name>.md`
- Hooks: `hooks/<source-plugin>/`

## Guardrails

- Don't modify files under `skills/`, `rules/`, `agents/`, `commands/` without being asked
- The install.sh script is the primary interface for managing this repo
- Never run `install.sh --uninstall` without explicit user request
