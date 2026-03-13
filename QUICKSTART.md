# Quickstart

Get all 35 skills, 3 MCP servers, and 5 rule sets deployed in under a minute.

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
- Merges MCP servers (Atlassian, GitLab, JFrog) into `~/.cursor/mcp.json`
- Symlinks 35 skills into `~/.codex/skills/`
- Adds `AGENT_BOOTSTRAP_HOME` to your shell

## 4. Set up your workspaces

```bash
# All repos at once:
./install.sh all ~/ATOM/

# Or one at a time:
./install.sh workspace ~/ATOM/my-repo
```

This symlinks rules into each repo's `.cursor/rules/` and generates a skill catalog so Cursor CLI agents can discover every skill.

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
