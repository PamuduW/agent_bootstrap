# Agentbot technical documentation

This directory documents the current Agentbot implementation. The root README
is the operator entrypoint; these pages describe ownership, lifecycle, and
maintenance contracts.

Canonical policy templates live in `base/` and `global/`, the skill-source
manifest is `skills.sources.yaml`, and private workspace state lives under
`${XDG_CONFIG_HOME:-$HOME/.config}/agentbot`.

| Document | Purpose |
|---|---|
| [Architecture](architecture.md) | Runtime boundaries and code layout |
| [Skills and integrations](skills.md) | Source manifest, locks, reconciliation, Graphify, and Boost |
| [Workspaces and rendering](workspaces-and-rendering.md) | Policy ownership, generated surfaces, and registration |
| [Lifecycle and updates](lifecycle-and-updates.md) | Install, update, recovery, and transaction behavior |
| [Validation](validation.md) | Complete and focused validation commands |
| [Roadmap](roadmap.md) | Delivered phases and planned capabilities |

Historical MCP snapshots are indexed in
[the archive](../archive/docs/README.md). They are research inputs, not runtime
configuration.
