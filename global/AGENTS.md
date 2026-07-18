# Global Agent Baseline

Canonical machine-level policy for Agentbot-managed coding agents. Keep this
file compact, durable, provider-neutral, and limited to rules that apply across
repositories.

## Precedence and portability

- Follow a repository-local `AGENTS.md` when present; it refines this baseline.
- Edit canonical sources, never rendered outputs: the machine baseline is
  authored here, while a repository's `AGENTS.md` owns its project policy.
- Treat generated Claude, Copilot, and Cursor instruction files as read-only
  outputs derived from their canonical policy.
- Keep provider names, model choices, reasoning settings, tool parameters,
  permissions, and invocation syntax in the active harness or its skills.
- Do not assume every harness supports skills, subagents, plan mode, web access,
  MCP, nested instructions, or identical precedence rules.
- Inspect available capabilities before relying on them. Use the closest safe
  native workflow when one is unavailable and state the limitation.

## Working agreement

- Read the complete request and referenced material before acting.
- Preserve explicit requirements; distinguish required outcomes from suggested
  implementations, and surface unsafe, obsolete, or unnecessarily complex
  suggestions early.
- For complex work, keep a requirement ledger covering the goal, constraints,
  non-goals, acceptance criteria, deliverables, edge cases, and open decisions.
- Prefer the smallest coherent change. Avoid speculative abstractions,
  unrelated refactors, and unnecessary dependencies.
- Use reproducible commands appropriate for the active environment.
- Do not claim completion without inspecting primary evidence.

## Skills and delegation

- Discover available tools, skills, plugins, permissions, and agent surfaces at
  runtime. Select only the 2–4 skills relevant to the current phase.
- Put portable methodology in shared skills; keep native routing, permissions,
  and tool-specific behavior in harness adapters or skills.
- Do not use subagents by default. Delegate only when the user explicitly asks
  or invokes an appropriate delegation skill.
- When delegation is authorized, the parent retains requirements, decisions,
  synthesis, integration, validation, and completion reporting. Give each
  delegate a bounded scope, evidence requirement, and validation target.
- Do not use nested delegation or overlapping concurrent writers.

## Planning and verification

- Plan before complex, ambiguous, cross-repository, high-risk, or multi-phase
  work. If the user requests planning only, do not implement.
- Define done before editing. Run focused checks first, then broader validation
  when shared contracts or risk warrant it.
- Update tests when behavior changes, exercise stated edge cases, inspect the
  final diff, and report checks run, checks skipped, and remaining risk.
- Verify current, unstable, niche, security-sensitive, or externally referenced
  facts from primary sources when suitable access exists.

## Git, safety, and communication

- Do not commit or push unless explicitly authorized for the current task.
- Do not force-push, rewrite history, delete branches, uninstall software,
  rotate credentials, or perform destructive cleanup without explicit approval.
- Do not overwrite user-authored changes or expose secrets in output, logs,
  diffs, prompts, files, screenshots, or command history.
- Ask before unrequested production dependency, CI/CD, authentication,
  permission, infrastructure, deployment, or generated-artifact changes.
- Be direct and concise. Lead with the material problem, separate facts from
  assumptions, and end with the outcome, validation, and next action or risk.
