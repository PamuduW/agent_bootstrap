# Preferences

> Stable defaults. Change rarely; agents read before acting.

## Communication

- Concise, complete sentences — no telegraphic shorthand
- Proportional detail: simple fixes get short answers; architecture gets structure
- Code citations over paraphrase when referencing existing code

## Tool preferences

| Tool | Use for |
|------|---------|
| **Cursor** | Daily IDE work, council orchestration, multi-file edits |
| **Claude Code** | Deep reasoning, long refactors, plan review |
| **Codex CLI** | Focused implementation, ChatGPT subscription |
| **Copilot** | Quick inline edits, GitHub-native flows |

Laptop stays **CLI-agents-only** — no always-on harness, no heavy runtime on WSL2.

## Coding conventions

- Minimal scope — smallest correct diff
- Match existing repo conventions before inventing new patterns
- Imports at top; exhaustive switches on TypeScript unions
- No commits unless explicitly requested

## Things to avoid

- Over-building (Hermes, opencode, Graphiti before pain appears)
- Unsupervised memory writes — vault changes need human approval
- Third-party subscription proxy plugins (policy risk)
- Editing generated compatibility outputs (`CLAUDE.md` exports, etc.) — edit canonical `AGENTS.md` instead
