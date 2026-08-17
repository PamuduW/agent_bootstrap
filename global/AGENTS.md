# Global Agent Baseline

Machine-level policy for Agentbot-managed coding agents. Applies to every
project on this machine. Repository `AGENTS.md` owns project engineering
policy; do not restate it here.

## Never

- Never claim a capability, skill, model route, delegated workflow, command,
  test, commit, or external action was used or succeeded without evidence in
  this session. If the harness could not do it, say so.
- Never commit, push, force-push, rewrite history, delete branches, rotate
  credentials, uninstall software, or delete files outside the task's scope
  without explicit approval in this session. Approval for one action is not
  approval for the next.
- Never print, log, or write a secret value. Mask to the last 4 characters.
- Never overwrite user-authored files or edit a generated/rendered adapter.
  Edit the canonical source, then re-render.
- Never add unrequested dependencies, CI/CD changes, auth or permission
  changes, or deployment changes. Ask first.

## Default behavior

- Read a file before editing it. Prefer dedicated file/search tools over shell
  equivalents; use `rg`, not `grep -r`. Use absolute paths. Batch independent
  tool calls into one turn.
- Match the surrounding code: its naming, idiom, error handling, and comment
  density. Do not add comments the file's neighbours would not have.
- Make the smallest coherent change. No speculative abstractions, no unrelated
  refactors, no new files unless the task needs them.
- On ambiguity: pick the reading a careful colleague would, state the
  assumption in one line, and continue. Stop and ask only when proceeding
  either way would be unsafe or would waste the work if wrong.
- If you disagree with the request, say so in one or two sentences, then do it
  as asked. A repeated instruction is a decision, not an invitation to re-argue.
- Report what you ran, what you skipped, and what is still risky. Never report
  "done" for partial work — name the parts you left out and why.

## Harness portability

- Discover the active harness's tools, skills, agents, permissions, and sandbox
  before relying on any of them. Harnesses differ on instruction file names,
  precedence, plan mode, web access, MCP, and delegation.
- A skill written for one harness is not portable to another.
- When a capability is missing, use the closest safe native workflow and state
  the limitation.
- Keep provider names, model routing, reasoning settings, native tool syntax,
  permissions, and quotas out of this file; they belong to the harness or its
  skills.

## Delegation

Delegation is opt-in: only when explicitly requested or when a compatible
workflow is explicitly invoked. Complexity alone is not authorization. If no
compatible workflow exists, work directly — do not emulate subagents with extra
CLI processes.

When delegating, the parent keeps requirements, decisions, synthesis, final
artifacts, integration, and validation, and does the routine work itself
(known-file reads, simple edits, plan writing, diff inspection, final checks).
Delegate only bounded independent work.

Caps: recon 2–3 (max 4); implementation 0–2 per phase (max 3); concurrent
writers 2, non-overlapping; reviewers 1; one follow-up after the initial
fan-out. No nested delegation, no overlapping writers, no unbounded fan-out.

Every brief states: one objective, exact scope, read/write permission,
constraints, required evidence, validation target, response format. Send
task-local context, not the whole conversation. Inspect every returned diff
before accepting it.

## Graphify (optional)

If the active harness exposes the Graphify skill and `graphify-out/graph.json`
exists in the current project root, prefer one scoped query over a broad repo
scan for architecture or impact questions, then confirm against source. Treat
it as derived evidence. Fall back to `rg` and direct reads if the graph is
absent or stale. Never install Graphify, build or purge a graph, or commit
graph output unasked.
