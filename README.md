# agent_bootstrap

Portable, self-updating source of truth for AI agent configurations. Clone it once, run one command, and every repo you open with Cursor, Codex, or Claude Code inherits 35 skills, 2-3 MCP servers, 5 rule sets, 9 commands, 4 subagents, and 2 hook configs -- automatically.

Built for a workflow where you work inside a parent folder (e.g. `~/ATOM/`), clone repos into it, and want every AI agent session to have the same capabilities regardless of which repo you're in.

---

## Why this exists

Cursor plugins give the GUI IDE chat access to skills, rules, MCP servers, commands, subagents, and hooks. But **CLI agents** (Cursor background agent, Codex CLI, Claude Code CLI) don't get any of that automatically. Each component type has a different mechanism:

| Component | Where it needs to live |
|-----------|----------------------|
| MCP servers | `~/.cursor/mcp.json` (global) or `{workspace}/.cursor/mcp.json` |
| Rules (.mdc) | `{workspace}/.cursor/rules/` -- no global folder exists |
| Skills (SKILL.md) | Readable from any absolute path, just need to be referenced |
| Commands (.md) | Prompt templates -- no native auto-loading for CLI agents |
| Agents (.md) | Agent definitions -- referenced manually |
| Hooks | Lifecycle scripts -- framework-specific setup |

This repo solves that by extracting everything from Cursor's plugin cache and deploying it to the right places via `install.sh`. The `sync.sh` script keeps it alive -- detecting new or updated plugins and pulling them in.

---

## What's inside

### Source plugins (7)

| Plugin | Skills | Rules | Agents | Commands | MCP | Hooks |
|--------|--------|-------|--------|----------|-----|-------|
| **Cursor Team Kit** | 12 | 2 | 1 | -- | -- | -- |
| **Superpowers** | 14 | -- | 1 | 3 | -- | 1 |
| **Continual Learning** | 1 | -- | -- | -- | -- | 1 |
| **Atlassian** | 5 | -- | -- | -- | 1 | -- |
| **GitLab** | 1 | 1 | 1 | 6 | 1 | -- |
| **Grafana Assistant** | 1 | 1 | -- | -- | -- | -- |
| **JFrog** | 1 | 1 | 1 | -- | 1 | -- |
| **Total** | **35** | **5** | **4** | **9** | **3** | **2** |

### Skills (35)

<details>
<summary>Atlassian (5) -- Jira and Confluence workflows</summary>

| Skill | What it does |
|-------|-------------|
| `atlassian-capture-tasks-from-meeting-notes` | Extract action items from meeting notes, create Jira tasks with assignees |
| `atlassian-generate-status-report` | Query Jira issues, generate status reports, publish to Confluence |
| `atlassian-search-company-knowledge` | Search Confluence/Jira for internal concepts, processes, architecture |
| `atlassian-spec-to-backlog` | Convert a Confluence spec into Epics and implementation tickets |
| `atlassian-triage-issue` | Triage bugs, search for duplicates, create or update Jira issues |

</details>

<details>
<summary>Cursor Team Kit (12) -- CI, code review, shipping</summary>

| Skill | What it does |
|-------|-------------|
| `cursor-team-kit-check-compiler-errors` | Run compile/type-check commands and report failures |
| `cursor-team-kit-deslop` | Remove AI-generated code slop, clean up style |
| `cursor-team-kit-fix-ci` | Find failing CI jobs, inspect logs, apply focused fixes |
| `cursor-team-kit-fix-merge-conflicts` | Resolve merge conflicts non-interactively, validate build |
| `cursor-team-kit-get-pr-comments` | Fetch and summarize review comments from active PR |
| `cursor-team-kit-loop-on-ci` | Watch CI runs and iterate on failures until all checks pass |
| `cursor-team-kit-new-branch-and-pr` | Create a branch, complete work, open a PR |
| `cursor-team-kit-pr-review-canvas` | Generate interactive HTML PR review walkthrough |
| `cursor-team-kit-review-and-ship` | Structured review, close issues, ship via PR |
| `cursor-team-kit-run-smoke-tests` | Run Playwright smoke tests, debug failures |
| `cursor-team-kit-weekly-review` | Weekly synthesis of commits (bugfix, tech debt, new work) |
| `cursor-team-kit-what-did-i-get-done` | Summarize authored commits over a time period |

</details>

<details>
<summary>Superpowers (14) -- TDD, debugging, planning, collaboration</summary>

| Skill | What it does |
|-------|-------------|
| `superpowers-brainstorming` | Explore intent, requirements, and design before implementation |
| `superpowers-dispatching-parallel-agents` | Run 2+ independent tasks in parallel without shared state |
| `superpowers-executing-plans` | Execute a written plan with review checkpoints |
| `superpowers-finishing-a-development-branch` | Guide merge, PR, or cleanup when implementation is done |
| `superpowers-receiving-code-review` | Process review feedback with technical rigor, not blind agreement |
| `superpowers-requesting-code-review` | Verify work meets requirements before merging |
| `superpowers-subagent-driven-development` | Execute implementation plans with independent sub-tasks |
| `superpowers-systematic-debugging` | Debug with root-cause tracing before proposing fixes |
| `superpowers-test-driven-development` | Write tests before implementation code |
| `superpowers-using-git-worktrees` | Create isolated git worktrees for feature work |
| `superpowers-using-superpowers` | Establish how to find and use skills at session start |
| `superpowers-verification-before-completion` | Run verification commands before claiming work is done |
| `superpowers-writing-plans` | Create detailed implementation plans from specs |
| `superpowers-writing-skills` | Create, edit, and test new skills |

</details>

<details>
<summary>Other (4) -- GitLab CI, Grafana, JFrog, Continual Learning</summary>

| Skill | What it does |
|-------|-------------|
| `continual-learning-continual-learning` | Mine past chats, extract preferences, update AGENTS.md |
| `gitlab-gitlab-ci-author` | Write, debug, optimize GitLab CI/CD configs |
| `grafana-assistant-grafana-assistant-cli` | Query Grafana via the grafana-assistant CLI |
| `jfrog-jfrog-platform` | JFrog Platform integration for security/artifact queries |

</details>

### MCP servers (2 + 1 optional)

| Server | Connects to | Auth | Notes |
|--------|------------|------|-------|
| `atlassian` | Jira, Confluence, Rovo | OAuth (browser flow) | Always included |
| `GitLab` | GitLab.com (or self-managed) | OAuth (browser flow) | Always included |
| `jfrog` | JFrog Platform (Artifactory, Xray) | OAuth | Only added when `JFROG_PLATFORM_URL` env var is set |

Full details in `mcp/mcp-inventory.md`.

### Rules (5)

| Rule | Applies to |
|------|-----------|
| `cursor-team-kit-no-inline-imports` | All files (always on) |
| `cursor-team-kit-typescript-exhaustive-switch` | All files (always on) |
| `gitlab-gitlab-workflow` | All files (always on) |
| `grafana-assistant-grafana-assistant` | All files (always on) |
| `jfrog-jfrog-security` | Dependency files (package.json, requirements.txt, etc.) |

### Commands (9)

Prompt templates that agents can read and execute:

| Command | What it does |
|---------|-------------|
| `superpowers-brainstorm` | Brainstorm before creative work |
| `superpowers-write-plan` | Create a detailed implementation plan |
| `superpowers-execute-plan` | Execute plan in batches with checkpoints |
| `gitlab-backlog-health` | Analyze backlog for staleness and gaps |
| `gitlab-create-issue` | Create a GitLab issue with labels/milestone |
| `gitlab-create-merge-request` | Create a MR from current branch |
| `gitlab-pipeline-status` | Check CI/CD health, drill into failures |
| `gitlab-plan-sprint` | Suggest sprint scope and priorities |
| `gitlab-review-merge-request` | Review a MR, summarize changes, flag concerns |

### Subagents (4)

| Agent | Role |
|-------|------|
| `cursor-team-kit-ci-watcher` | Watch CI, report pass/fail with failure logs |
| `gitlab-gitlab-assistant` | Agile planning, delivery tracking via GitLab MCP |
| `jfrog-supply-chain-security` | Audit deps for vulnerabilities and license compliance |
| `superpowers-code-reviewer` | Code review with structured feedback |

### Hooks (2)

| Hook | Trigger | Runtime |
|------|---------|---------|
| `continual-learning` | Session stop | `bun` |
| `superpowers` | Session start | `bash` |

---

## Repo structure

```
agent_bootstrap/
├── install.sh              Setup script (global + per-workspace)
├── sync.sh                 Living repo: detect and pull updates
├── manifest.json           Tracks plugin hashes and sync state
├── AGENTS.md               Instructions for agents working in this repo
├── .env.example            Environment variables reference
├── .cursor/rules/
│   └── bootstrap-meta.mdc  Cursor rule for agents in this repo
│
├── skills/                 35 skills (SKILL.md + references each)
├── rules/                  5 Cursor rules (.mdc)
├── mcp/
│   ├── mcp.json            MCP server config (Atlassian, GitLab, JFrog)
│   └── mcp-inventory.md    Detailed MCP documentation
├── agents/                 4 subagent definitions
├── commands/               9 command templates
├── hooks/                  Lifecycle scripts
│   ├── continual-learning/
│   └── superpowers/
│
└── templates/              Templates for new projects
    ├── AGENTS.md           Codex per-project template
    └── .codexignore        Default ignore patterns
```

---

## install.sh reference

```
Usage: install.sh <command> [options]

Commands:
  global              Set up global configs (MCP, Codex skills, shell env)
  workspace <path>    Set up a single workspace/repo
  all <parent-dir>    Set up all git repos under a directory
  status              Show current installation status
  uninstall           Remove all installed symlinks and configs

Options:
  --dry-run           Show what would be done without making changes
  --force             Overwrite existing files (with global)
  -h, --help          Show this help
```

### What `global` does

| Platform | Action |
|----------|--------|
| **Cursor** | Merges MCP server entries into `~/.cursor/mcp.json` (preserves existing entries) |
| **Codex** | Symlinks all 35 skills into `~/.codex/skills/`; generates global `AGENTS.md` with full skill/command/agent catalog and working-agreement guardrails (skip if exists, `--force` to overwrite) |
| **Claude Code** | Merges MCP into `~/.claude/mcp.json`; generates global `CLAUDE.md` with full skill/command/agent catalog (if `~/.claude/` exists; skip if exists, `--force` to overwrite) |
| **Shell** | Adds `export AGENT_BOOTSTRAP_HOME=...` to `~/.bashrc` (idempotent) |

### What `workspace` does

For a given repo path:

1. Creates `<repo>/.cursor/rules/` if needed
2. Symlinks every `rules/*.mdc` file into it
3. Generates a `bootstrap-skills.mdc` rule -- this is the key file that makes skills discoverable to Cursor CLI agents. It lists every skill with its absolute path so the agent can read any SKILL.md on demand.
4. Merges MCP config into `<repo>/.cursor/mcp.json`
5. Generates a `CLAUDE.md` at the repo root with the full skill/command/agent catalog for Claude Code CLI

All symlinks use absolute paths back to this repo, so edits here propagate instantly.

### What `all` does

Finds every directory with a `.git/` under the given parent, runs `workspace` on each (skipping the bootstrap repo itself).

### What `uninstall` does

Reads the `.installed` log and removes every symlink, generated file, and profile line that `install.sh` created. MCP merges can't be auto-undone (warns to edit manually).

---

## sync.sh reference

```
Usage: sync.sh <mode>

Modes:
  --check     Scan sources and report what's new/changed (read-only)
  --pull      Pull updates from sources into the bootstrap repo
```

### Sources scanned

1. **Cursor plugin cache** (`~/.cursor/plugins/cache/cursor-public/`) -- compares plugin commit hashes against `manifest.json`. Detects new plugins, updated plugins (hash changed), and removed plugins.
2. **Codex skills** (`~/.codex/skills/`) -- finds skills not already in the bootstrap (ignores system skills and symlinks back to this repo).

### What `--pull` does

For each new or updated plugin:
- Extracts skills, rules, agents, commands, hooks, MCP config
- Copies into the bootstrap structure using the `<plugin>-<name>` naming convention
- Merges any new MCP entries into `mcp/mcp.json`
- Updates `manifest.json` with the new hash

For each new Codex skill:
- Copies into `skills/`
- Records in manifest

After pulling, it re-runs `install.sh global --force` to regenerate `~/.codex/AGENTS.md` and `~/.claude/CLAUDE.md` with the updated catalog, then re-runs `install.sh workspace` for every previously configured workspace to regenerate `bootstrap-skills.mdc` and per-repo `CLAUDE.md`.

### manifest.json

Tracks what was synced and when. Each plugin entry has:
- `hash` -- the commit hash from the plugin cache path
- `synced_at` -- date of last sync
- Component counts (skills, rules, agents, commands, hooks, mcp)

---

## Environment variables

| Variable | Required for | Default |
|----------|-------------|---------|
| `JFROG_PLATFORM_URL` | JFrog MCP server | -- (must set, e.g. `myteam.jfrog.io`) |
| `GRAFANA_URL` | Grafana Assistant skill | -- (e.g. `https://mystack.grafana.net`) |
| `GRAFANA_SA_TOKEN` | Grafana Assistant skill | -- (service account token) |
| `CONTINUAL_LEARNING_MIN_TURNS` | Continual Learning hook | `10` |
| `CONTINUAL_LEARNING_MIN_MINUTES` | Continual Learning hook | `120` |
| `AGENT_BOOTSTRAP_HOME` | Scripts and agent discovery | Set by `install.sh global` |

Copy `.env.example` for reference.

---

## How agents discover skills in sibling repos

Each platform has a different mechanism. `install.sh` handles all of them:

### Cursor CLI

`install.sh workspace` generates a `bootstrap-skills.mdc` in each repo's `.cursor/rules/`. With `alwaysApply: true`, it's loaded into every conversation. The agent sees the full catalog of skills with absolute paths and can read any SKILL.md on demand.

### Codex CLI

`install.sh global` symlinks all 35 skills directly into `~/.codex/skills/`, where Codex discovers them natively. It also generates a global `~/.codex/AGENTS.md` that lists all available commands and agents (with paths), so the agent knows about everything beyond just skills.

### Claude Code CLI

`install.sh global` merges MCP servers into `~/.claude/mcp.json` and generates a global `~/.claude/CLAUDE.md` with the full skill/command/agent catalog. `install.sh workspace` also generates a per-repo `CLAUDE.md` at the repo root. Claude Code reads this file automatically and gets the same skill discovery as Cursor.

---

## Living repo: keeping it updated

The whole point is that this repo stays current. Two ways to update:

### 1. Run sync.sh manually

```bash
cd ~/ATOM/agent_bootstrap
./sync.sh --check    # see what changed
./sync.sh --pull     # pull updates
git add -A && git commit -m "sync: update from sources"
git push
```

### 2. Tell an AI agent to do it

Open any CLI agent (Cursor, Codex) in this repo and say:

> "Update this repo -- check for new or updated plugins and pull them in."

The `AGENTS.md` and `.cursor/rules/bootstrap-meta.mdc` tell the agent exactly what to do: run `sync.sh --check`, then `sync.sh --pull`, review with `git diff`, commit, and optionally propagate with `install.sh all`.

---

## Deploying to a new machine / WSL instance

```bash
# 1. Clone
cd ~/ATOM
git clone git@github.com:PamuduW/agent_bootstrap.git

# 2. Install globally
./agent_bootstrap/install.sh global

# 3. Set up all repos
./agent_bootstrap/install.sh all ~/ATOM/

# 4. Reload shell
source ~/.bashrc

# 5. (Optional) Preview first
./agent_bootstrap/install.sh global --dry-run
./agent_bootstrap/install.sh all ~/ATOM/ --dry-run
```

When you clone a new repo later:

```bash
git clone git@github.com:org/new-repo.git ~/ATOM/new-repo
~/ATOM/agent_bootstrap/install.sh workspace ~/ATOM/new-repo
```

---

## Prerequisites

- **jq** -- required for JSON merging (`sudo apt install jq`)
- **bash** 4+
- At least one of: Cursor CLI, Codex CLI, Claude Code CLI
- Git (for sync.sh to detect repos)

---

## Files not tracked in git

| File | Purpose |
|------|---------|
| `.installed` | Log of everything install.sh created (used by uninstall/status) |
| `.env` | Your local environment variables |

Both are in `.gitignore`.
