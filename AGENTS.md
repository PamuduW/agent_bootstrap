# Agent Bootstrap

This is the agent bootstrap repo — a single source of truth for AI agent configurations (skills, rules, MCP servers, commands, subagents, hooks) that get deployed across all workspaces.

## Repo structure

```
skills/      35+ skill definitions (SKILL.md + references)
rules/       Cursor rule files (.mdc)
mcp/         MCP server configs (mcp.json) and documentation
agents/      Subagent definitions (.md)
commands/    Command/prompt templates (.md)
hooks/       Lifecycle hook scripts
templates/   Templates for new projects (AGENTS.md, .codexignore)
manifest.json  Tracks sources, plugin hashes, sync timestamps
install.sh     Deploys configs to global and per-workspace locations
sync.sh        Pulls updates from Cursor plugin cache and Codex skills
```

## When asked to update or sync

### Step 1 — Run the automated sync

1. Run `./sync.sh --check` to see what's changed (new plugins, updated plugins, new Codex skills)
2. If changes are found, run `./sync.sh --pull` to import them

sync.sh covers: Cursor plugins (`~/.cursor/plugins/cache/cursor-public/`) and Codex skills (`~/.codex/skills/`). It detects new plugins, updated plugin hashes, and independently-installed Codex skills.

### Step 2 — Check for things sync.sh does NOT cover

These sources exist outside the plugin cache and must be checked manually:

- **Cursor native skills** at `~/.cursor/skills-cursor/` — Cursor ships built-in skills (create-rule, create-skill, etc.) that are separate from plugins. List that directory and compare against `skills/` in this repo. Import any new or updated ones using the `cursor-native-<name>` naming convention.
- **Removed or deprecated plugins** — if sync.sh reports a plugin as removed (in manifest but not in cache), delete the corresponding `skills/<plugin>-*`, `rules/<plugin>-*`, `agents/<plugin>-*`, `commands/<plugin>-*` files from this repo and remove the plugin entry from `manifest.json`.
- **MCP config drift** — compare `~/.cursor/mcp.json` against `mcp/mcp.json` in this repo. If the user configured new MCP servers via the Cursor UI, they'll be in the global file but not here. Merge any missing servers back into `mcp/mcp.json`.
- **Stale content** — for each plugin in `manifest.json`, verify the hash still matches the cache. If the plugin directory in the cache has fewer skills/rules/agents than what's tracked, diff the contents and remove anything that was dropped upstream.

### Step 3 — Review and commit

3. Review the changes with `git diff`
4. Commit: `git add -A && git commit -m 'sync: <summary of what changed>'`
5. Optionally run `./install.sh all ~/ATOM/` to propagate to workspaces

## When asked to install or set up

1. `./install.sh global` — sets up MCP servers, Codex skills, shell env
2. `./install.sh all ~/ATOM/` — symlinks rules and generates skill catalogs for all repos under ~/ATOM/
3. `./install.sh workspace ~/ATOM/<repo>` — set up a single repo
4. `./install.sh status` — show what's installed

## When editing skills, rules, or MCP configs

- Skills live in `skills/<plugin>-<name>/SKILL.md`
- Rules live in `rules/<plugin>-<name>.mdc`
- MCP config is in `mcp/mcp.json`; documentation in `mcp/mcp-inventory.md`
- After editing, re-run `./install.sh all ~/ATOM/` to propagate changes

## Conventions

- Skill directories are named `<source-plugin>-<skill-name>`
- Rule files are named `<source-plugin>-<rule-name>.mdc`
- Agent/command files are named `<source-plugin>-<name>.md`
- The manifest.json tracks where each component came from

## Guardrails

- Don't modify files under `skills/`, `rules/`, `agents/`, `commands/` without being asked
- The install.sh and sync.sh scripts are the primary interface for managing this repo
- Never run `install.sh uninstall` without explicit user request
