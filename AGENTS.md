# Agent Bootstrap

This is the agent bootstrap repo — a single source of truth for AI agent configurations (skills, rules, MCP servers, commands, subagents, hooks) that get deployed across all workspaces.

## Repo structure

```
skills/         35+ skill definitions (SKILL.md + references)
rules/          Cursor rule files (.mdc)
mcp/            MCP server configs (mcp.json) and documentation
agents/         Subagent definitions (.md)
commands/       Command/prompt templates (.md)
hooks/          Lifecycle hook scripts
templates/      Templates for new projects (AGENTS.md, .codexignore)
manifest.json   Tracks sources, plugin hashes, sync timestamps, MCP provenance
install.sh      Interactive plugin manager + deployment tool
sync.sh         Deprecated — redirects to install.sh
.local-config   Per-machine plugin selections (gitignored)
```

## Quick start

```bash
./install.sh          # Interactive mode — menu with Update/Initialize/Status
```

## When asked to update or sync

Run `./install.sh` and choose option **1) Update** to pull the latest from GitHub, then **2) Initialize** to review and sync plugins.

The Initialize flow:
1. Discovers plugins from three sources: repo manifest, Cursor plugin cache, local installs
2. Shows an interactive dual-checkbox menu (Repo + Local per plugin)
3. Previews changes and asks for confirmation
4. Syncs: pulls new plugins into repo, removes deselected ones, deploys/removes locally
5. Offers to git commit + push if the repo changed

## When asked to install or set up

### Interactive (recommended)
```bash
./install.sh          # Choose option 2: Initialize
```

### Scripted / CI
```bash
./install.sh --global              # Global MCP, Codex skills, shell env
./install.sh --all ~/ATOM/         # All repos under ATOM
./install.sh --workspace <path>    # Single repo
./install.sh --status              # Show what's configured
```

These commands respect `.local-config` if present (created by the interactive menu). Without it, all repo plugins are deployed.

## Plugin model

Everything is grouped by plugin name (e.g., `jfrog`, `atlassian`, `cursor-team-kit`). A plugin includes all `<plugin>-*` assets across skills/, rules/, agents/, commands/, hooks/, plus its MCP server keys.

Each plugin has two independent states:
- **Repo**: whether the plugin's files are tracked in this git repo
- **Local**: whether the plugin is deployed on this machine

`Local` requires `Repo` — you can't deploy locally without the files being in the repo.

## MCP provenance

The manifest.json (v2) tracks which MCP server keys each plugin contributes via the `mcp_servers` array. This enables clean removal: deselecting a plugin removes exactly its MCP servers from all configs without touching user-added servers.

## Workspace-level agent config files

At each workspace, `CLAUDE.md` is generated as the primary skill catalog. `AGENTS.md` is a symlink to `CLAUDE.md`, preventing divergence between agent config files.

## Conventions

- Skill directories: `skills/<source-plugin>-<skill-name>/`
- Rule files: `rules/<source-plugin>-<rule-name>.mdc`
- Agent/command files: `agents/<source-plugin>-<name>.md`, `commands/<source-plugin>-<name>.md`
- Hooks: `hooks/<source-plugin>/`
- The manifest.json tracks where each component came from

## Guardrails

- Don't modify files under `skills/`, `rules/`, `agents/`, `commands/` without being asked
- The install.sh script is the primary interface for managing this repo
- Never run `install.sh --uninstall` without explicit user request
