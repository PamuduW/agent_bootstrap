# Archive — legacy v1 artifacts

This directory holds **dead or superseded artifacts** from the pre–Stage 5 `agent_bootstrap` repo. Nothing here is live code. It was moved (not deleted) to preserve git history and avoid mistaking vendored plugin mirrors for the new config-plane layout.

## Why these were archived

Stage 5 rebuilds `agent_bootstrap` as a **skills repo + installer** (see `docs/plan/plan5-agent-bootstrap-rebuild.md` and `docs/research/02-agent_bootstrap.md` §5). The v1 model vendored Cursor plugin content into the repo and described a sync workflow that v2 replaced with the Python control plane (`src/agent_bootstrap/`, `install.sh`, `catalog/packages.json`).

| Path | Reason |
|------|--------|
| `skills/` | 52+ vendored skill dirs — duplicates Cursor cache and official plugins; not the personal authored pack the rebuild targets |
| `rules/` | Imported Cursor rule files; not deployed by v2 render pipeline |
| `agents/` | Imported subagent definitions; not deployed by v2 |
| `commands/` | Imported command/prompt templates; not deployed by v2 |
| `hooks/` | Imported lifecycle hook scripts; not deployed by v2 |
| `sync.sh` | Deprecated wrapper that only forwards to `install.sh` |
| `.codex` | Empty placeholder file with no purpose in v2 |
| `bootstrap-meta.mdc` | Stale Cursor rule describing v1 layout (`manifest.json`, dual-checkbox sync menu) — contradicts current `install.sh` / Python CLI |
| `mcp-inventory.md` | Stale hand-written MCP inventory; live config is `mcp/mcp.json` + catalog provenance |

## What stayed live (repo root)

- `src/agent_bootstrap/` — render, catalog, state, service, doctor (22 tests)
- `install.sh` — bootstrap entrypoint
- `global/`, `templates/`, `catalog/` — canonical AGENTS.md and package schema
- `mcp/mcp.json` — MCP server config (catalog-filtered at render time)
- `tests/`, `docs/openclaw-plan.md`

## Do not use for new work

Do not add skills, rules, or sync scripts here. New skills belong in the rebuilt `skills/` tree (authored personal pack) or are installed via `npx skills` from upstreams listed in `skills.sources.yaml` (Stage 5 Part D).
