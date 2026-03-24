# Quickstart

Get all skills, MCP servers, and rule sets deployed interactively.

## Prerequisites

```bash
# jq is required (check with: jq --version)
sudo apt install jq
```

You need at least one CLI agent installed: Cursor, Codex, or Claude Code.

## 1. Clone

```bash
cd ~/ATOM   # or wherever you keep your repos
git clone git@github.com:PamuduW/agent_bootstrap.git
cd agent_bootstrap
```

## 2. Run the interactive installer

```bash
./install.sh
```

This shows a menu:

```
  === Agent Bootstrap ===

  1) Update        Pull latest from GitHub
  2) Initialize    Manage plugins (add/remove, deploy/undeploy)
  3) Status        Show current installation state
  4) Quit
```

Choose **2) Initialize** to see the plugin manager:

```
  === Plugin Manager ===
  ↑/↓ navigate   Space toggle   Tab switch column   a all   n none   Enter confirm

       Repo Local  Plugin
  > 1. [x]  [x]   atlassian
    2. [x]  [x]   compound-engineering
    3. [x]  [x]   cursor-native
    ...
```

- **Repo** column: whether to include the plugin in the git repo
- **Local** column: whether to deploy it on this machine
- Use **Space** to toggle, **Tab** to switch between Repo/Local columns
- Press **Enter** to confirm, then review the change summary

After confirming, the installer:
- Pulls/removes plugins from the repo as needed
- Syncs MCP servers to Cursor, Claude Code (selective per plugin)
- Symlinks skills into Codex
- Generates skill catalog files for all workspaces
- Offers to git commit + push

## 3. Set up workspaces

After the interactive setup, deploy to your workspaces:

```bash
# All repos at once:
./install.sh --all ~/ATOM/

# Or one at a time:
./install.sh --workspace ~/ATOM/my-repo
```

Per-workspace setup:
- **Cursor**: Symlinks rules into `.cursor/rules/`, generates skill catalog, merges MCP
- **Claude Code**: Generates `CLAUDE.md` with skill/command/agent catalog
- **AGENTS.md**: Symlinked to `CLAUDE.md` for other agents
- **Codex**: Already covered by global setup (skills in `~/.codex/skills/`)

## 4. Verify

```bash
./install.sh --status
```

## Done

Open any repo under `~/ATOM/` with a CLI agent. It now has access to all selected skills, MCP servers, and rules.

---

## Day-to-day usage

### Plugins updated or new ones available?

```bash
./install.sh    # Choose 2) Initialize — shows updated plugins automatically
```

### New repo cloned?

```bash
./install.sh --workspace ~/ATOM/new-repo
```

### Want to remove a plugin (e.g., JFrog)?

```bash
./install.sh    # Choose 2) Initialize, untick JFrog in both columns, confirm
```

The installer removes all JFrog skills, rules, agents, MCP servers from the repo and all local configs.

### Need environment variables?

```bash
# JFrog (if using JFrog MCP)
export JFROG_PLATFORM_URL="myteam.jfrog.io"

# Grafana (if using Grafana skill)
export GRAFANA_URL="https://mystack.grafana.net"
export GRAFANA_SA_TOKEN="glsa_xxxx"
```

See `.env.example` for the full list.

### Deploying to another machine?

```bash
git clone git@github.com:PamuduW/agent_bootstrap.git ~/ATOM/agent_bootstrap
cd ~/ATOM/agent_bootstrap
./install.sh    # Interactive — choose what to deploy on this machine
```

### CI / scripted mode (no TUI)?

```bash
./install.sh --global              # Deploy everything (or respect .local-config)
./install.sh --all ~/ATOM/         # Set up all workspaces
./install.sh --status              # Check state
```

### Removing everything?

```bash
./install.sh --uninstall
```
