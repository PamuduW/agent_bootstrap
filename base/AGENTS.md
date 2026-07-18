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
- Select only the capabilities needed for the current phase.
- Use portable skills for shared methodology.
- Use a harness-compatible skill for native council behavior, model routing,
  permissions, or delegation.
- Do not assume a skill written for a different harness works in the active one.
- Follow the active harness's skill discovery and invocation mechanism.

The identifiers below are manifest references, not a promise that every harness
supports every skill or its invocation syntax. Discover availability before use.

| Capability | Managed identifiers | Use only when the active harness supports it |
|---|---|---|
| Planning and execution | `brainstorming`, `writing-plans`, `executing-plans`, `subagent-driven-development`, `test-driven-development` | Exploration, structured planning, plan execution, authorized delegation, or test-first changes. |
| Research and security | `literature-review`, `owasp` | Research synthesis or security review. |
| Delivery and infrastructure | `kubernetes`, `k8s`, `kubernetes-specialist`, `terraform`, `github-actions`, `gitlab-ci`, `devops-engineer` | Kubernetes, infrastructure, CI/CD, or delivery work. |

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

<!-- Project-owned section. Add purpose, supported environments, stack, key
paths, setup/run/test commands, generated files, architecture constraints,
external services, deployment notes, hazards, approval checkpoints, and the
definition of done. Agentbot preserves this section during baseline resync. -->
