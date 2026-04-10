# Global Agent Baseline

This is the canonical machine-level baseline for all agent surfaces managed by
`agent_bootstrap`.

## Working Agreement

- Follow the repo-local `AGENTS.md` when present; it refines this baseline.
- Prefer CLI-friendly workflows and idempotent commands.
- Treat generated compatibility files as read-only outputs derived from
  canonical `AGENTS.md` files.
- Never auto-commit or auto-push changes.
- Record durable instruction changes in the audit log when updating canonical
  `AGENTS.md` files through automation.

## Surface Goals

- Codex CLI: consume the shared baseline and repo overlays consistently.
- Cursor IDE/CLI: receive generated rules and MCP configs from the same source
  of truth.
- Copilot: receive generated repo instructions from the same merged policy.
- Claude Code: receive generated compatibility files from the same merged
  policy.

## Plugin Policy

- Use curated canonical packages instead of raw mirrored plugin content.
- Keep discovery, selection, and deployment state separate.
- Resolve MCP ownership before rendering outputs.
