# AGENTS.md

Engineering policy for this repository. Keep it specific and verifiable —
prefer "run `pytest tests/`" over "test your changes".

## Policy files

- This file is canonical. Every other instruction file Agentbot renders for
  this repo (see the enabled targets in `agentos.yaml`) is a generated adapter
  — edit this file and re-render, never edit an adapter.
- Resync rewrites the prefix between the Agentbot baseline markers and keeps
  everything after them. An `AGENTS.md` with no markers whose prefix no longer
  matches the base template is treated as custom and left untouched.
- Put anything repo-specific under `## Project`.

## Non-negotiables

- Never claim a command, test, commit, or external action ran or succeeded
  without evidence in this session.
- Never commit or push without explicit authorization for this task.
- Never print, log, or write a secret value.

## When to plan first

Write a plan before touching code if any of these hold:

- the change spans more than ~5 files or more than one repository;
- it touches auth, permissions, secrets, CI/CD, deployment, or data migration;
- it changes a public interface, a schema, or a cross-service contract;
- the requirements are ambiguous enough that two readings give different code.

Otherwise implement directly. If the deliverable is a plan, do not implement.

A plan states: objective, non-goals, evidence gathered, assumptions, affected
files, phases with dependencies, compatibility and migration, failure handling,
tests, rollback, and completion criteria. Update it when reality diverges.

## When to keep a requirement ledger

For any request with 3+ numbered requirements, or any multi-phase plan, track:
goal, current state, required behavior, non-goals, edge cases, acceptance
criteria, unresolved decisions. Map each numbered requirement to the code that
implements it and the check that proves it. Audit against this ledger before
reporting completion — passing tests do not excuse a requirement mismatch.

## Working in this repo

1. Read the request in full, plus the relevant code, tests, and `git status`,
   before editing.
2. Change the smallest coherent surface. Avoid unrelated cleanup.
3. Preserve existing architecture and user-authored content unless an approved
   plan changes them.
4. Validate each phase before widening scope; respect requested checkpoints.

## Definition of done

- Format/lint checks for the changed files pass.
- Focused tests for the changed behavior pass; broaden when a shared contract,
  infrastructure, or deployment path changed.
- Stated edge cases are exercised; tests updated when behavior changed.
- Both sides of any cross-repo or cross-service contract are verified.
- `git diff` and `git status` reviewed — nothing unrelated is staged.
- Durable docs updated when commands, interfaces, setup, or ops behavior
  changed.
- The report names the checks that ran, the checks that could not run, and the
  remaining risk.

## Git

- No commit or push without explicit authorization for this task.
- Never stage unrelated files. Keep credentials out of tracked files, prompts,
  logs, and command history.

## Project

**Purpose:** Agentbot installs curated upstream skills via `npx`, renders a
machine-level baseline from `global/AGENTS.md`, and manages per-folder agent
policy surfaces with `agentbot boot`, `workspace`, and `resync`. Treat this
repo as a small CLI plus shell entrypoint, not a full config plane.

**Stack:** Bash (`install.sh`, `bin/*`), Python 3 (`src/` via
`python3 -m src.cli`), and Node.js (`npx skills`).

| Path | Role |
|---|---|
| `install.sh` | Repository entrypoint for install, skills, global render, Doctor, and workspace commands. |
| `skills.sources.yaml` | Curated upstream skill manifest; global pins live in `~/.agents/.skill-lock.json`. |
| `src/` | Python CLI, global rendering, skill reconciliation, and workspace services. |
| `bin/agentbot` | Public dispatcher; `boot` renders and registers a workspace. |
| `agentos.yaml` | Safe-default profile and fixed workspace output allowlist. |
| `base/` | Canonical project-policy templates; keep its managed baseline synchronized with this file. |
| `${XDG_CONFIG_HOME:-$HOME/.config}/agentbot/workspaces.json` | Private local workspace registry; never Git-tracked. |
| `global/AGENTS.md` | Authored machine baseline rendered to managed agent homes. |
| `global/claude/statusline-command.sh` | Managed Claude Code status line installed to `~/.claude/statusline-command.sh` during global render, update refresh, workspace resync, and Doctor/Status checks. |
| `tests/` | Python and shell regression suites. |
| `archive/` | Deferred catalog/MCP material and sanitized historical notes; Phase 4 design lives in the workspace `temp/mem/` notes. |

**Commands:**

```bash
./install.sh install
./install.sh update
./install.sh update --yes
./install.sh skills install
./install.sh global
./install.sh doctor
python3 -m unittest discover -s tests
bash tests/test_agentbot.sh
bash tests/test_agentbot_menu.sh
```

**Repository constraints:**

- `install.sh` is the supported bootstrap interface.
- Plain `./install.sh update` refreshes upstream skills and, after successful
  or no-delta reconciliation, refreshes registered workspaces and managed
  global Codex/Claude outputs (including statusline).
- `./install.sh update --dry-run` previews reconciliation and managed-surface
  changes without writing. `--yes` pre-approves source-owned skill additions,
  removals, and manifest changes that would otherwise require confirmation.
- Do not vendor upstream skills; use the manifest and global Skills CLI flow.
- Keep Graphify CLI installation opt-in and owned by Dotfiles. When the CLI
  exists, main Agentbot Install and Update run only
  `graphify install --platform agents`; CLI absence is a non-failing skip and
  setup failure fails the main flow. Neither path builds project graphs.
- The TUI does not register repositories. Keep explicit `boot` and
  `workspace --yes` CLI setup available. `workspaces --remove PATH` changes
  only the private registry and never removes or regenerates workspace files.
- Archived commands (`all`, `interactive`, `import-local`, and similar) must
  remain unavailable until their archived modules are deliberately restored.
