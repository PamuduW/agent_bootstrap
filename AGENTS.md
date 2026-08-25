# AGENTS.md

Engineering policy for this repository. Keep it specific and verifiable:
prefer exact commands and canonical examples over abstract advice.

## Policy ownership

- This file is canonical for repository-wide agent policy. Agentbot-generated
  adapters are derived output: edit this file and re-render, never an adapter.
- Resync rewrites the Agentbot-managed prefix between its baseline markers and
  preserves content after it. An unmarked `AGENTS.md` whose prefix no longer
  matches the base template is custom and must be left alone.
- Put repository-wide facts under `## Project`; put component-specific guidance
  in the nearest scoped instruction file when needed instead of bloating root.
- Do not repeat machine policy here except for the safety floor below, which is
  intentionally retained for agents that run without a personal baseline.

## Safety floor

- Never claim a command, test, commit, or external action succeeded without
  evidence from this session.
- Never commit or push without explicit authorization for this task.
- Never expose a secret in chat, logs, documentation, or tracked files.
- Preserve unrelated pre-existing modified, staged, and untracked work.

## Plan first when risk or coupling requires it

Plan before editing when any of these hold:

- multiple repositories or independently deployable components are involved;
- auth, permissions, secrets, CI/CD, release/deployment behavior, or data
  migration changes;
- a public interface, schema, persistent data, or cross-service contract changes;
- implementation has dependent phases where order or rollback matters;
- material ambiguity could cause substantially different work or major rework.

File count alone does not require a plan. Keep plans proportional. Include only
applicable items from objective, non-goals, evidence, assumptions, affected
areas, dependencies, compatibility/migration, validation, failure handling,
rollback, and completion criteria. Update a plan when reality materially
diverges. If the requested deliverable is only a plan, do not implement it.

## Requirement tracking

For multi-phase work or 3+ independently verifiable acceptance criteria, keep a
lightweight `requirement -> implementation -> validation` mapping in the current
task or native plan system. Do not create a ledger file unless requested or
required by repository convention. Audit it before reporting completion;
passing tests do not excuse a requirement mismatch.

## Repository workflow

- Follow commands, conventions, generated-file rules, and constraints under
  `## Project` and any applicable scoped instruction file.
- Where guidance is absent, infer conventions from code and configuration
  instead of inventing project rules.
- Keep cross-service/repository contract changes synchronized. If one side is
  unavailable, identify exactly what remains unverified.
- Respect requested checkpoints; validate a risky phase before widening scope.

## Definition of done

- Run the narrowest applicable repo-configured format, lint, typecheck, build,
  and tests for the changed behavior. Broaden when a shared contract,
  infrastructure path, or deployment path changed.
- Exercise stated edge cases and update tests when behavior changes.
- Never delete, skip, weaken, or rewrite validation merely to make work pass;
  change a check only when the requested behavior legitimately requires it.
- Verify both sides of changed cross-service/repository contracts when available.
- Review `git diff` and `git status`; leave unrelated user-owned changes and
  staging state untouched.
- Update durable docs when commands, interfaces, setup, generated sources,
  operations, or deployment behavior change.
- If a relevant check cannot run or fails for a pre-existing/environmental
  reason, report the command, evidence, and remaining uncertainty rather than
  claiming full verification.
- Report checks run, checks not run, and remaining risk.

## Project

**Purpose:** Agentbot installs curated upstream skills via `npx`, renders a
machine-level baseline from `global/AGENTS.md`, and manages per-folder agent
policy surfaces with `agentbot boot`, `workspace`, and `resync`. Treat this
repo as a small CLI plus shell entrypoint, not a full config plane.

**Stack:** Bash (`install.sh`, `bin/agentbot`), Python 3 (`src/` via
`python3 -m src.cli`), and Node.js (`npx skills`).

| Path | Role |
|---|---|
| `install.sh` | Thin repository entrypoint for repository gating, dependency checks, token scoping, CLI delegation, and launcher linking. |
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
bash tests/run.sh
```

For focused troubleshooting, run `python3 -m unittest discover -s tests` or
an individual shell suite under `tests/test_*.sh`.

**Repository constraints:**

- `install.sh` is the supported bootstrap interface.
- Keep product behavior in the Python CLI. Do not add alternate Bash
  implementations or capability-probe fallbacks to `install.sh`.
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
- Keep Boost CLI installation disabled by default and owned by Dotfiles.
  Agentbot may preview and configure only Claude/Codex shell-output integration
  with `--no-boostgraph`; never pass `--accept-terms`, enable MCP/BoostGraph, or
  install/update the Boost binary from this repository. Boost has no
  `--no-status-line` opt-out, so a Boost-wrapped `statusline-command.sh` is
  detected and preserved, never refreshed over.
- The TUI does not register repositories. Keep explicit `boot` and
  `workspace --yes` CLI setup available. `workspaces --remove PATH` changes
  only the private registry and never removes or regenerates workspace files.
- Archived commands (`all`, `interactive`, `import-local`, and similar) must
  remain unavailable until their archived modules are deliberately restored.
