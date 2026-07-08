# Agent relationships

Per-tool contracts — what each agent does in the work plane. Config plane (`agent_bootstrap`) feeds all of them.

**Environment:** WSL2 laptop, CLI-only. Hermes (control plane) deferred to home server.

| Tool | Role | When to use | Avoid |
|------|------|-------------|-------|
| **Cursor** | Council orchestrator, IDE | Multi-file edits, subagent delegation, daily coding | Long autonomous runs without review |
| **Claude Code** | Deep reasoning | Architecture, plan review, complex refactors | Quick one-liner fixes |
| **Codex CLI** | Implementation | Focused coding tasks (ChatGPT sub) | Open-ended research |
| **Copilot** | Quick edits | Inline suggestions, GitHub PR flows | Canonical policy authoring |

## Shared inputs

All tools read from the config plane:

- `global/AGENTS.md` — machine baseline
- `<repo>/AGENTS.md` — project overlay
- `memory-vault/` — durable context (this vault)
- `~/.agents/skills/` / `~/.claude/skills/` — via `npx skills` installer

## Handoff pattern

Planner (strong model) → worker (cheap/fast) → reviewer (strong model). Semi-manual; don't chase full auto-routing on the laptop.
