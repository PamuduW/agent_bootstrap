# Agentbot archive

## Status and runtime boundary

This archive preserves inactive configuration payloads and historical context.
Nothing under `archive/` is loaded by `./install.sh`, the Agentbot lifecycle,
or the Skills CLI at runtime. Current behavior is documented under
[`docs/`](../../docs/README.md).

## Retained payloads

| Path | Restoration value |
|---|---|
| [`../.env.example`](../.env.example) | Names of optional MCP environment variables |
| [`../agentos.yaml`](../agentos.yaml) | Pre-slim profile and export reference |
| [`../catalog/packages.json`](../catalog/packages.json) | Deferred package-catalog schema and entries |
| [`../mcp/mcp.json`](../mcp/mcp.json) | Deferred MCP server registry |
| [`../templates/.codexignore`](../templates/.codexignore) | Historical export-ignore template |
| [`../templates/AGENTS.md`](../templates/AGENTS.md) | Historical workspace overlay template |
| [`legacy-memory-vault-design.md`](legacy-memory-vault-design.md) | Sanitized history of the removed public memory prototype |

The active repository already has a live `agentos.yaml`, workspace renderer,
registration service, and managed policy templates. Archived versions are
references, not replacements.

## Deferred capabilities

The active [roadmap](../../docs/roadmap.md) owns future scope. Deferred ideas
include package-catalog and profile-filtered MCP rendering, a larger AgentOS
TUI and ingest pipeline, additional provider adapters, home-server
orchestration, and later memory-graph technologies. None should be restored
without a new design and tests against the current lifecycle.

The Phase 4 durable-memory design lives in the parent setup workspace under
`docs/designs/memory/`. It is intentionally outside this standalone repository
and is not linked relatively from here.

## Removed code and Git recovery

The pre-slim catalog control plane was removed from the current tree. Its
catalog, discovery, state, full-render, interactive UI modules, and associated
tests remain available in Git history. Use history for code; do not expect the
retained JSON, YAML, and templates to form a working implementation by
themselves.

Useful history queries include:

```bash
git log --all -- archive/src archive/tests
git log --all -- catalog mcp
git show <commit>:<path>
```

## Restoration procedure

1. Define a narrow Phase 3 or later scope in the active roadmap and design.
2. Create a branch and identify the exact historical commit and files.
3. Reuse only the required retained payloads from `archive/`.
4. Adapt recovered code to `src/cli.py`, `src/lifecycle.py`, current workspace
   services, and current ownership rules; do not copy an old tree wholesale.
5. Restore or rewrite focused tests for every recovered contract.
6. Run `env -u NO_COLOR bash tests/run.sh` and Doctor before considering the
   feature live.

## Historical notes

The repository was slimmed in July 2026. Workspace rendering and registration
were subsequently rebuilt as the live Phase 2 implementation, while catalog
and MCP bundles remained deferred. The public memory-vault prototype was later
removed because moving personal memory into a public archive does not make it
private.

Global skill installs use `~/.agents/.skill-lock.json`. The committed
`skills-lock.json` remains a differently shaped project-install stub. That
current lock ownership is documented in
[`docs/skills.md`](../../docs/skills.md), not as an archive-only rule.
