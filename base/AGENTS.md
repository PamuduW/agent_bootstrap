# AGENTS.md

Repository-level instructions. These refine the global Agentbot baseline and
should stay practical, current, and specific to this repository.

## Environment and ownership

- **Primary environment:** WSL2 Ubuntu; **shell:** bash.
- **Primary agent surfaces:** Codex CLI, Cursor, Claude Code, and GitHub Copilot.
- Prefer repository-relative paths and commands that work from the repository
  root. Treat `$AGENTBOT_HOME` as optional tooling context, not a project path.
- `AGENTS.md` is the canonical repository policy. Do not edit generated
  `CLAUDE.md`, `.github/copilot-instructions.md`, or
  `.cursor/rules/agentbot-policy.mdc`; edit `AGENTS.md` and regenerate instead.
- Use the skill syntax supported by the active agent surface. Do not assume this
  repository contains Agentbot's skill manifest or every globally installed skill.

## Default task workflow

1. Read the complete request, repository instructions, relevant implementation,
   tests, and git state before changing files.
2. For complex work, maintain a requirement ledger: goal, current state,
   required behavior, constraints, non-goals, edge cases, acceptance criteria,
   deliverables, and unresolved decisions.
3. Plan cross-repository, multi-phase, architectural, migration,
   security-sensitive, or ambiguous work before coding. Proceed directly only
   for small, well-scoped changes.
4. Make the smallest coherent change, validate it, inspect the diff, and report
   evidence. Respect requested review or approval checkpoints.

## Skills and delegation

Select only the skills needed for the current phase. The following explicitly
managed skills may be available globally; use each only when its scope fits.

| Group | Skills | Use when |
|---|---|---|
| Planning | `brainstorming`, `writing-plans`, `executing-plans`, `subagent-driven-development`, `test-driven-development` | Exploring, planning, executing reviewed work, authorized delegation, or test-first changes. |
| Opt-in delegation | `co-council` | Explicitly requested parallel investigation with parent-owned synthesis. |
| Research and security | `literature-review`, `owasp` | Research synthesis or security review. |
| Delivery | `kubernetes`, `k8s`, `kubernetes-specialist`, `terraform`, `github-actions`, `gitlab-ci`, `devops-engineer` | The task directly concerns infrastructure, Kubernetes, IaC, or CI/CD. |

- Do not use subagents unless the user explicitly asks or invokes an appropriate
  delegation workflow. The parent owns requirements, decisions, integration,
  validation, and the final response.
- When delegation is authorized, give each delegate a bounded non-overlapping
  scope and inspect its evidence and diff before accepting it.
- Do not use nested delegation or concurrent writers with overlapping files.

## Planning, implementation, and validation

- A substantial plan should state objectives, non-goals, evidence, assumptions,
  affected files, phases, dependencies, failure handling, validation, rollout,
  and completion criteria.
- Preserve established architecture and user-authored content unless the plan
  explicitly changes it. Avoid unrelated cleanup.
- Run formatting or lint checks relevant to changed files, focused behavior
  tests, and broader checks when shared contracts change. Exercise stated edge
  cases, inspect git diff/status, and state checks that could not run.
- Update durable documentation when commands, interfaces, setup, or operational
  behavior changes. Use primary sources for current external facts when needed.

## Git, secrets, and interaction

- Do not commit or push without explicit authorization. Never stage unrelated
  files, overwrite user changes, or perform destructive cleanup without approval.
- Keep credentials out of tracked files and output. Treat CI/CD, authentication,
  permissions, deployments, package management, and infrastructure as high-risk.
- Lead with material problems or unsupported assumptions. Separate facts,
  assumptions, and recommendations; do not claim a result without checking it.

## Project

<!-- Project-owned section. Add purpose, stack, key paths, commands, deployment
notes, and repository-specific constraints here. Agentbot resync preserves this
section while refreshing only its managed baseline. -->
