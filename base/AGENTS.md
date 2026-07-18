# AGENTS.md

Repository-level instructions. These refine the global Agentbot baseline and
should stay practical, current, and specific to this repository.

## Scope and ownership

- Verify the active environment, shell, repository root, available tools, and
  repository-local instructions before running environment-sensitive commands.
- `AGENTS.md` is the canonical repository policy for an Agentbot-managed
  workspace. Agentbot may render harness-specific instruction adapters from it.
- Treat Agentbot-managed adapter files as generated outputs. Edit canonical
  policy, then use the supported preview/apply workflow to regenerate them.
- Do not overwrite user-authored instruction files or assume every harness uses
  the same file names, syntax, skills, tools, or precedence model.

## Default task workflow

1. Read the complete request, relevant implementation, tests, documentation,
   repository instructions, and git state before changing files.
2. For complex work, maintain a requirement ledger: goal, current state,
   required behavior, constraints, non-goals, edge cases, acceptance criteria,
   deliverables, and unresolved decisions.
3. For long numbered requests, map each requirement to affected components,
   implementation or plan steps, and validation.
4. Plan cross-repository, multi-phase, architectural, migration,
   security-sensitive, infrastructure, deployment, or ambiguous work before
   coding. Proceed directly only for small, well-scoped changes.
5. Make the smallest coherent change, validate it, inspect the complete diff,
   and report evidence. Respect requested review or approval checkpoints.

## Agentbot-managed capability references

The identifiers below are maintained with the enabled Agentbot manifest. They
are capability references, not a promise that every harness supports every
skill or its invocation syntax. Discover availability before use.

| Capability | Managed identifiers | Use only when the active harness supports it |
|---|---|---|
| Planning and execution | `brainstorming`, `writing-plans`, `executing-plans`, `subagent-driven-development`, `test-driven-development` | Exploration, structured planning, plan execution, authorized delegation, or test-first changes. |
| Research and security | `literature-review`, `owasp` | Research synthesis or security review. |
| Delivery and infrastructure | `kubernetes`, `k8s`, `kubernetes-specialist`, `terraform`, `github-actions`, `gitlab-ci`, `devops-engineer` | Kubernetes, infrastructure, CI/CD, or delivery work. |

## Delegation and planning

- Delegation is opt-in. Use it only when the user explicitly requests it or
  explicitly invokes a compatible workflow.
- This shared policy does not name or require a particular council skill. Select
  a harness-compatible council or delegation workflow only when authorized.
- The parent owns requirements, decisions, synthesis, integration, validation,
  and the final response. Delegate only bounded independent work with explicit
  scope, evidence, and validation expectations.
- Do not use nested delegation, overlapping writers, or unlimited fan-out.
- A substantial plan should state objectives, non-goals, evidence, assumptions,
  affected files, phases, dependencies, failure handling, validation, rollout,
  and completion criteria. If the requested deliverable is a plan, do not
  implement.

## Implementation, validation, and safety

- Preserve established architecture and user-authored content unless an approved
  plan explicitly changes them. Avoid unrelated cleanup.
- Run formatting or lint checks relevant to changed files, focused behavior
  tests, and broader checks when shared contracts or risk warrant them.
- Exercise stated edge cases, inspect git diff and status, and state checks that
  could not run. Passing tests do not excuse a requirement mismatch.
- Update durable documentation when commands, interfaces, setup, deployment, or
  operational behavior changes. Use primary sources for current external facts.
- Do not commit or push without explicit authorization. Never stage unrelated
  files, overwrite user changes, perform destructive cleanup, or expose secrets.
- Treat CI/CD, authentication, permissions, dependencies, releases,
  deployments, package management, and infrastructure as high-risk.
- Lead with material problems or unsupported assumptions. Separate facts,
  assumptions, and recommendations; do not claim a result without checking it.

## Project

<!-- Project-owned section. Add purpose, supported environments, stack, key
paths, setup/run/test commands, generated files, architecture constraints,
external services, deployment notes, hazards, approval checkpoints, and the
definition of done. Agentbot preserves this section during baseline resync. -->
