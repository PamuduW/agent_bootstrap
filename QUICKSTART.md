# Quickstart

Get all 35 skills, 2-3 MCP servers, and 5 rule sets deployed in under a minute.

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

## 2. Preview what will happen (optional)

```bash
./install.sh global --dry-run
./install.sh all ~/ATOM/ --dry-run
```

## 3. Install globally

```bash
./install.sh global
source ~/.bashrc
```

This does:
- **Cursor**: Merges MCP servers (Atlassian, GitLab, and JFrog if `JFROG_PLATFORM_URL` is set) into `~/.cursor/mcp.json`
- **Codex**: Symlinks 35 skills into `~/.codex/skills/`, generates `~/.codex/AGENTS.md` with full catalog
- **Claude Code**: Merges MCP into `~/.claude/mcp.json`, generates `~/.claude/CLAUDE.md` with full catalog (if installed)
- **Shell**: Adds `AGENT_BOOTSTRAP_HOME` to your `.bashrc`

## 4. Set up your workspaces

```bash
# All repos at once:
./install.sh all ~/ATOM/

# Or one at a time:
./install.sh workspace ~/ATOM/my-repo
```

This does per-repo setup for all platforms:
- **Cursor**: Symlinks rules into `.cursor/rules/`, generates skill catalog rule, merges MCP
- **Claude Code**: Generates a `CLAUDE.md` with skill/command/agent catalog
- **Codex**: Already covered by global setup (skills in `~/.codex/skills/`)

## 5. Verify

```bash
./install.sh status
```

## Done

Open any repo under `~/ATOM/` with a CLI agent. It now has access to all skills, MCP servers, and rules.

---

## Day-to-day usage

### New repo cloned?

```bash
./install.sh workspace ~/ATOM/new-repo
```

### Plugins updated?

```bash
./sync.sh --check          # see what changed
./sync.sh --pull           # pull into bootstrap
./install.sh all ~/ATOM/   # propagate to workspaces
./install.sh all /home/test/Dev/ # propagate to workspaces
```

Or just open an agent in this repo and say "update this".

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
~/ATOM/agent_bootstrap/install.sh global
~/ATOM/agent_bootstrap/install.sh all ~/ATOM/
source ~/.bashrc
```

### Removing everything?

```bash
./install.sh uninstall
```
