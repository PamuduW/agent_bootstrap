# AGENTS.md

Repository-level instructions. These refine the global Agentbot baseline and
should stay practical, current, provider-neutral, and specific to this
repository.

## Scope and ownership

- Verify the active environment, shell, repository root, available tools,
  permissions, sandbox constraints, and repository-local instructions before
  running environment-sensitive commands.
- `AGENTS.md` is the canonical repository policy for an Agentbot-managed
  workspace.
- Agentbot may render or link harness-specific instruction adapters from this
  policy.
- Treat Agentbot-managed adapters as generated outputs. Edit canonical policy,
  then use the supported Agentbot workflow to refresh them.
- Do not overwrite user-authored instruction files.
- Do not assume every harness uses the same file names, syntax, skills, agents,
  tools, or precedence model.

## Default task workflow

1. Read the complete request, relevant implementation, tests, documentation,
   repository instructions, and git state before changing files.
2. For complex work, maintain a requirement ledger covering:
   - goal;
   - current state;
   - required behavior;
   - constraints and non-goals;
   - edge cases;
   - acceptance criteria;
   - deliverables;
   - unresolved decisions.
3. For long numbered requests, map each requirement to affected components,
   implementation or plan steps, and validation.
4. Plan cross-repository, multi-phase, architectural, migration,
   security-sensitive, infrastructure, deployment, or ambiguous work before
   coding.
5. Proceed directly only for small, well-scoped changes.
6. Make the smallest coherent change, validate it, inspect the complete diff,
   and report evidence.
7. Respect requested review or approval checkpoints.

## Agentbot-managed capabilities

- Agentbot's enabled manifest and installed skill metadata are the source of
  truth for reusable capabilities.
- Discover available compatible skills through the active harness before
  selecting capabilities. When Agentbot is available, its installed inventory
  and manifest provide the durable capability catalog.
- Select only the capabilities needed for the current phase.
- Use portable skills for shared methodology.
- Use a harness-compatible skill for native council behavior, model routing,
  permissions, or delegation.
- Do not assume a skill written for a different harness works in the active one.
- Follow the active harness's skill discovery and invocation mechanism.

## Optional Graphify evidence

- Use the installed Graphify skill for repository-wide relationship,
  architecture, or impact questions only when the active harness exposes the
  skill and `graphify-out/graph.json` exists and is readable.
- Treat `graphify-out/graph.json` as belonging to the current project root;
  do not implicitly use a graph from a sibling or unrelated repository.
- Prefer a scoped Graphify query before a broad repository scan, then inspect
  primary source files for claims that affect code changes.
- Fall back to `rg`, direct file reads, and normal repository analysis when the
  graph is absent, stale, incomplete, or the query fails.
- Never install Graphify, build or purge a graph, add hooks, enable strict
  mode, or commit graph output without an explicit request.
- Treat Graphify output as derived evidence, not as a replacement for current
  source and tests.

## Delegation and planning

- Delegation is opt-in. Use it only when the user explicitly requests it or
  explicitly invokes a compatible workflow; task complexity alone is not
  authorization.
- Do not delegate routine work merely because delegation is available.
- This shared policy does not name or require a particular council
  implementation.
- If no compatible workflow exists, use the active harness directly rather than
  emulating subagents with extra CLI processes.

When delegation is used:

- The parent owns requirements, decisions, synthesis, final artifacts,
  integration, validation, and the final response.
- The parent directly handles known-file reads, routine commands, simple file
  operations, small or tightly coupled edits, final plan writing, integration,
  diff inspection, and final validation.
- Delegate only bounded independent work with explicit scope, evidence, and
  validation expectations.
- Planning or reconnaissance: normally 2–3 delegates; maximum 4.
- Implementation: normally 0–2 delegates; maximum 3 per phase.
- Concurrent writers: maximum 2 with non-overlapping ownership.
- Deep reviewer or conflict resolver: maximum 1.
- After the initial fan-out: maximum 1 targeted follow-up.
- Nested delegation, overlapping writers, and unlimited fan-out are prohibited.
- Provide task-local context rather than copying the complete parent
  conversation into every delegate.
- Inspect delegated evidence and diffs before accepting them.

Interpret “act as the higher brain” as:

> Keep requirements, architectural judgment, synthesis, final artifacts,
> integration, and validation in the parent. Delegate only bounded independent
> work where a separate context materially improves the result.

A substantial plan should state objectives, non-goals, current evidence,
assumptions, decisions, affected repositories and files, phases, dependencies,
ownership boundaries, compatibility, migration, security and failure handling,
testing, rollout or rollback, completion criteria, and requirement
traceability.

The planning parent writes and audits the final plan. If the requested
deliverable is a plan, do not implement.

## Implementation, validation, and safety

- Preserve established architecture and user-authored content unless an approved
  plan explicitly changes them.
- Avoid unrelated cleanup.
- Work in reviewable phases and validate each phase before widening scope.
- Give each implementation delegate a non-overlapping file or directory
  boundary.
- Inspect every delegated diff before accepting it.
- Update the plan when implementation reality differs from it.
- Verify both sides of cross-repository or cross-service contracts.
- Run formatting or lint checks relevant to changed files.
- Run focused behavior tests and broader checks when shared contracts,
  infrastructure, or deployment behavior changes.
- Exercise stated edge cases.
- Inspect git diff and status.
- State checks that could not run.
- Passing tests do not excuse a requirement mismatch. Audit the result against
  the original requirement ledger.
- Update durable documentation when commands, interfaces, setup, deployment, or
  operational behavior changes.
- Use primary sources for current external facts when suitable access exists.

## Git, secrets, and interaction

- Do not commit or push without explicit authorization.
- Never stage unrelated files, overwrite user changes, or perform destructive
  cleanup without approval.
- Keep credentials out of tracked files, prompts, logs, command history, and
  output.
- Mask stored secret values by default.
- Treat CI/CD, authentication, permissions, dependencies, releases,
  deployments, package management, and infrastructure as high-risk.
- Lead with material problems or unsupported assumptions.
- Separate facts, assumptions, and recommendations.
- Do not claim a file, test, command, commit, deployment, or external action
  exists or succeeded without checking it.

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
