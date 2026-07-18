# AGENTS.md

Repository-level operating instructions. These refine the global Agentbot
baseline and should remain practical, current, and specific to this repository.

## Environment

- **Primary environment:** WSL2 Ubuntu
- **Shell:** bash
- **Primary agent surfaces:** Codex CLI, Cursor, Claude Code, GitHub Copilot
- **Agentbot home:** `$AGENTBOT_HOME`
- Prefer repository-relative paths and commands that work from the repository
  root.

Invoke a skill using the syntax supported by the active agent surface. Installed
skill metadata and `skills.sources.yaml` are the source of truth.

## Default Task Workflow

1. Read the entire request and all referenced files before changing anything.
2. Build a requirement ledger:
   - goal;
   - current state and relevant paths;
   - required changes;
   - constraints and non-goals;
   - examples and edge cases;
   - acceptance criteria;
   - requested deliverables;
   - unresolved decisions.
3. Inspect the repository instructions, current implementation, tests, and git
   state before proposing architecture.
4. For complex work, plan before coding. For small, well-scoped work, proceed
   directly with a short internal plan.
5. Make the smallest coherent change, validate it, inspect the diff, and report
   evidence.
6. Do not proceed to a later phase when the user explicitly requested a review or
   approval checkpoint.

For requests containing many numbered changes, maintain a traceability table in
the plan or working notes that maps each requirement to affected components,
implementation phase, and validation.

## Planning Contract

Use plan mode or the `writing-plans` skill for cross-repository, multi-phase,
architectural, migration, security-sensitive, or ambiguous work.

The planning parent must:

- retain ownership of requirements and architectural decisions;
- inspect critical primary evidence itself;
- use `co-council` only for bounded independent investigation;
- reconcile conflicting delegate findings;
- write and audit the final plan itself;
- avoid implementing when the requested deliverable is only a plan.

A substantial plan should include:

- objective and non-goals;
- current-state findings with file/path references;
- assumptions, decisions, and open questions;
- proposed architecture, interfaces, and data flow;
- exact repositories, modules, and files expected to change;
- ordered phases with dependencies and ownership boundaries;
- migration, compatibility, security, and failure handling;
- testing and validation per phase;
- rollout/rollback where applicable;
- completion criteria and requirement traceability.

When the user asks for clarification questions in a file, create that file only
for material blockers. Do not manufacture questions that can be resolved safely
from repository evidence.

## Delegation Contract

Use the global **delegation-first, not delegation-only** policy.

- The parent remains the planner, integrator, reviewer, and final author.
- Use the parent directly for known-file reads, ordinary shell commands, simple
  edits, plan writing, integration, and final validation.
- Use `co-council` for genuinely independent exploration, research, review,
  testing, or non-overlapping implementation.
- Default planning fan-out: 2–3 delegates; maximum 4.
- Default implementation fan-out: 0–2 delegates; maximum 3 per phase.
- Maximum two concurrent writers with explicit, non-overlapping ownership.
- No nested delegation.
- One targeted follow-up is allowed after the initial batch; do not rerun the
  whole council because one result was weak.
- Stop spawning once the evidence is sufficient.

Do not interpret “act as the higher brain” as “perform no direct work.” Interpret
it as:

> Keep requirements, judgment, synthesis, final artifacts, integration, and
> validation in the parent. Delegate only bounded independent work where a
> separate context or parallel execution materially improves quality or speed.

## Skills

Select only the skills needed for the current phase.

### Common workflow skills

- `brainstorming`: explore options before committing.
- `grilling`: challenge assumptions and expose failure modes.
- `co-council`: bounded Codex subagent investigation with Luna routing.
- `writing-plans`: create phased implementation plans.
- `executing-plans`: implement a reviewed plan incrementally.
- `diagnosing-bugs`: evidence-driven debugging.
- `tdd` or `test-driven-development`: red-green-refactor.
- `yagni`: remove unnecessary complexity.
- `handoff`: write a compact continuation artifact.

### Load on demand

Use architecture, security, documentation, Kubernetes, Terraform, CI/CD, or
other domain skills only when the task requires them. Do not load overlapping
skills without a clear reason.

## Implementation Contract

- Work in reviewable phases with explicit completion criteria.
- Preserve existing architecture and conventions unless the plan explicitly
  changes them.
- Avoid unrelated cleanup while implementing a feature or fix.
- Do not overwrite user-authored changes.
- Give each implementation delegate an explicit file or directory boundary.
- Inspect every delegated diff before accepting it.
- Update the plan or progress notes when reality differs from the plan.
- For cross-repository changes, verify contracts at both sides of each boundary.

## Testing and Validation

Fill in repository-specific commands under `## Project`.

At minimum:

- run formatting/lint checks relevant to changed files;
- run focused tests for changed behavior;
- run broader integration/build checks when shared contracts, infrastructure, or
  deployment behavior changes;
- exercise stated examples and edge cases;
- review the final diff and git status;
- state checks that could not be run.

Passing tests do not excuse a requirement mismatch. Audit the result against the
original requirement ledger before reporting completion.

## Research and Documentation

- Use live research when the task depends on current APIs, versions, security
  guidance, pricing, limits, or external behavior.
- Prefer primary sources and record URLs or citations in durable research or plan
  artifacts when requested.
- Keep implementation comments focused on why, not on restating obvious code.
- Update durable documentation when commands, interfaces, behavior, setup, or
  operational procedures change.

## Git and Secrets

- Do not commit or push unless the current user request explicitly authorizes it.
- For authorized commits, stage only intended files and use a descriptive,
  task-specific message.
- Never print or persist secrets in tracked files. Store credentials outside the
  repository with restrictive permissions.
- Token-entry interfaces should mask values by default and display only a short
  fingerprint when confirming an existing token.
- Treat changes to CI/CD, credentials, permissions, deployments, package
  management, and infrastructure as high-risk and validate them explicitly.

## Interaction Style

- Lead with the first material problem, conflict, or unsupported assumption.
- Do not agree by default or add empty praise.
- Separate facts, assumptions, and recommendations.
- Be concise, but include enough evidence to make decisions reviewable.
- Never claim a file, command, test, commit, or deployment exists or succeeded
  without checking it.

## Project

<!-- Fill in per-repo: purpose, stack, key paths, testing commands, deployment notes. -->
