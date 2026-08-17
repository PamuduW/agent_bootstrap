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

Purpose, stack, key paths, setup/run/test commands, generated files,
architecture constraints, external services, deployment notes, hazards,
approval checkpoints. Agentbot preserves this section on resync.
