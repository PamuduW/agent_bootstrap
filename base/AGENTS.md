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

Replace this paragraph with concrete repository facts: purpose/boundaries;
stack and important versions; key paths; exact setup, run, test, lint, format,
typecheck, and build commands; generated files and canonical sources;
architecture/public-contract constraints; required external services and
non-secret environment expectations; release/deployment notes; and
repository-specific hazards or approval checkpoints. Agentbot preserves this
section on resync.
