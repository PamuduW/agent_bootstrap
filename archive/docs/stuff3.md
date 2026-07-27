# Agentbot expansion roadmap

**Status:** Phases 0, 1, 2, and 5 are complete and verified against the live
repositories (2026-07-27); supporting documentation was reconciled on
2026-07-28. Phase 4 is the next workstream; its Slice 4M migration gate is
complete in the working tree and pending review/merge. Phase 3 remains
deferred. Phase 5 branches directly from the completed Phase 2 foundation.

This is a living roadmap. The runtime source and operational documentation are
the authority; this file records the delivered contracts and the future
direction. Historical research may retain older names, but active instructions
must use Agentbot and agentbot.

## Current source of truth

| Area | Live source | Status |
|---|---|---|
| Agentbot CLI and menu | install.sh, bin/agentbot, scripts/menu.sh | Live |
| Workspace profile | agentos.yaml, src/workspace_profiles.py | Live |
| Canonical repository policy | base/AGENTS.md | Live |
| Claude template | base/CLAUDE.md | Live |
| Workspace renderer | src/workspace_render.py | Live |
| Local registration and resync | src/workspace_state.py, src/workspace_service.py | Live |
| Workspace commands | src/cli.py, install.sh | Live |
| Workspaces menu | scripts/menus/workspaces.sh | Live |
| Global machine baseline | global/AGENTS.md and install.sh global | Live |
| Curated skills | skills.sources.yaml and install.sh skills ... | Live |
| Dotfiles integration | sibling dotfiles Agentbot bridge | Live |
| Package catalog and MCP bundles | archive/catalog/, archive/mcp/ | Phase 3 (deferred) |
| Durable memory | workspace `temp/mem/` design plus sanitized legacy note | Next (Phase 4; Slice 4M migration gate) |
| Graphify CLI and assistant integration | sibling dotfiles component plus Agentbot integration | Live (Phase 5) |

Agentbot is the installed product and public command. agent_bootstrap remains
the Git repository and clone directory. AGENTBOT_TUI is the active TUI
environment variable.

## Phase dependency

```
Phase 0: slim skills + global baseline + static repository bootstrap ✅
    |
    v
Phase 1: standalone Agentbot menu + Dotfiles bridge + unified boot ✅
    |
    v
Phase 2: profiles + managed workspace render + local resync ✅
    |\
    | \--> Phase 5: optional Graphify CLI + assistant integration ✅
    |
    +----> Phase 3: package catalog + profile-filtered MCP bundles (deferred)
    |
    +----> Phase 4: durable memory (next: Slice 4M migration gate)
```

## Phase 0 — slim bootstrap ✅

The foundation is live:

- skills.sources.yaml declares curated public upstream sources;
- install.sh skills install/update/list/doctor manages skills through the Skills
  CLI and global lock;
- install.sh global renders global/AGENTS.md to machine-level agent outputs;
- agentbot boot provides the Phase 1 scaffold entrypoint;
- install.sh doctor validates the slim manifest, links, locks, and outputs.

## Phase 1 — standalone UX and unified Agentbot ✅

Phase 1 delivered the independent Agentbot menu and sibling bridge:

- install.sh and agentbot with no arguments open the TUI on a controlling TTY;
- headless invocation gives explicit Agentbot CLI guidance;
- Dotfiles launches the sibling Agentbot menu without duplicating its logic;
- agentbot update remains skill reconciliation and is separate from workspace
  resync;
- boot is the single project setup entrypoint and Agentbot is the active public
  product name.

## Phase 2 — profiles, workspace render, and local resync ✅

**Goal:** Maintain one canonical repository policy while generating the
compatibility files required by the selected agent surfaces, and allow the
operator to refresh registered folders safely.

### Ownership model

```
base/AGENTS.md
        |
        v
target/AGENTS.md
  Agentbot-managed baseline block
  project-owned ## Project section
        |
        +--> target/CLAUDE.md
        +--> target/.github/copilot-instructions.md
        +--> target/.cursor/rules/agentbot-policy.mdc
```

AGENTS.md is always created or preserved and is the canonical repository
policy. The managed block is delimited by:

```
<!-- BEGIN AGENTBOT MANAGED BASELINE -->
...
<!-- END AGENTBOT MANAGED BASELINE -->
```

Only that block is refreshed from base/AGENTS.md. The ## Project section and all
other content remain project-owned. An existing unmarked AGENTS.md is preserved
as custom policy and is never overwritten by base resync.

CLAUDE.md is a generated pointer to AGENTS.md. Copilot receives a generated
copy of the resolved AGENTS.md. Cursor receives the generated
.cursor/rules/agentbot-policy.mdc Project Rule with alwaysApply: true. The
Cursor filename describes policy, not skill installation.

### Profiles and targets

agentos.yaml contains the intentionally small safe-default profile. The fixed
Phase 2 targets are agents, claude, copilot, and cursor. With no selector,
Agentbot selects all four. Codex and agents are aliases for the canonical
AGENTS.md target; no separate Codex file is created. Any custom selection still
includes AGENTS.md.

Phase 2 does not install skills, execute community scripts, write MCP files, or
choose arbitrary filesystem paths from profile data.

### Registration and state

Every successful agentbot boot, whether it targets the current directory or an
explicit path, registers the canonical folder locally. A Git target is stored
at its Git root; a non-Git target is stored at its canonical directory path.
agentbot workspace PATH --yes has the same registration behavior.

The local registry is
${XDG_CONFIG_HOME:-${HOME}/.config}/agentbot/workspaces.json. It is
private local operator state, mode 0600 inside a mode 0700 directory, versioned,
atomic, and credential-free. It is never written into a project or Git-tracked.

### Public operations

```
agentbot boot
agentbot boot --claude
agentbot boot --copilot
agentbot boot --cursor
agentbot boot --codex

agentbot workspace PATH
agentbot workspace --yes PATH
agentbot workspaces
agentbot resync --dry-run --all
agentbot resync --yes --all
agentbot resync --yes PATH
```

Workspace commands preview by default. Existing unmarked compatibility files
are conflicts and are not replaced. The legacy --force boot option is not part
of Phase 2. No command stages, commits, pushes, resets, deletes, or changes
Git ignore rules automatically.

Batch resync processes enabled records independently, reports every result, and
does not delete missing records or silently convert a recorded Git workspace
into a directory record. Dirty Git state is reported but does not by itself
block an explicit apply.

### Phase 2 verification

The implementation is covered by:

- profile schema and invalid-configuration tests;
- managed-boundary, legacy migration, conflict, idempotency, and atomic-write
  renderer tests;
- private state, permissions, malformed-state, and symlink tests;
- folder/Git identity, custom policy, resync, and failure-isolation tests;
- CLI preview/apply/list/resync tests;
- Agentbot dispatcher, boot, menu, syntax, and temporary-folder acceptance
  tests.

## Phase 3 — package catalog and MCP bundles

**Goal:** Let an explicit package catalog determine which MCP servers and
related artifacts are rendered for a selected profile or workspace.

Planned work:

1. validate and promote archive/catalog/packages.json;
2. restore catalog load/filter and provenance-aware managed-artifact behavior;
3. add profile-filtered MCP output only after the Phase 2 renderer contract is
   stable;
4. reintroduce import-local and remove-managed only with explicit ownership and
   conflict reporting;
5. extend Doctor for orphaned, conflicting, or unowned MCP entries.

Phase 3 must extend the Phase 2 renderer; it must not create a second unrelated
configuration system.

## Phase 4 — durable memory (next: Slice 4M migration gate)

**Goal:** Add human-approved durable project knowledge only when the current
Markdown policy surface is no longer sufficient.

Current gate status:

- [x] remove the public `archive/memory-vault/` prototype from the current
  branch;
- [x] retain only a sanitized historical note under `archive/docs/`;
- [x] keep the private-memory design and implementation contracts in workspace
  `temp/mem/`;
- [ ] review and merge the migration gate before implementation slices begin.

Later planned work:

- implement selected private-memory workflows with user approval before writes;
- keep memory local, reviewable, and separate from generated repository policy;
- keep obsidian-memory disabled until its source layout and provenance are
  explicitly designed.

Do not start with a vector database or an always-on laptop service.

## Phase 5 — optional Graphify integration ✅

**Goal:** Make Graphify an explicit, removable setup choice without confusing
CLI ownership, assistant integration, or Agentbot's canonical policy ownership.

### Ownership boundary

- Dotfiles owns installation and updates of the `graphifyy` Python package,
  exposed as the `graphify` CLI.
- Agentbot owns registration of the Graphify skill and its exposure to supported
  assistants.
- Graphify owns its generated `SKILL.md`, references, and
  `.graphify_version` stamp under the generic Agent Skills directory.
- Agentbot remains the only owner of its canonical `base/AGENTS.md` and
  `global/AGENTS.md` policy sources.

### Delivered behavior

1. Add a default-off `graphify_cli` component to the Dotfiles component picker.
   Selecting it installs Graphify with `uv tool install graphifyy`; an existing
   non-uv Graphify installation is reported and preserved rather than silently
   replaced.
2. Add Graphify to the existing `dotfiles update` flow. Update only a uv-owned
   `graphifyy` tool with `uv tool upgrade graphifyy`; report external
   installations as unmanaged and provide a manual command instead of taking
   ownership.
3. Add a Graphify submenu and matching non-interactive command to Agentbot.
   Status is read-only. Setup first checks for the CLI and gives a direct
   Dotfiles/manual install instruction when it is absent.
4. Setup runs the skill-only command
   `graphify install --platform agents`, then refreshes Agentbot's existing
   assistant links and global outputs. This makes the canonical skill available
   from `~/.agents/skills/graphify/` without allowing Graphify to edit a
   repository policy file.
5. Agentbot Update refreshes the Graphify skill only when Graphify integration
   is already present. It never enables Graphify as a side effect.
6. Add short conditional Graphify guidance to the canonical base and global
   policies. Agents use Graphify only when the skill and a usable
   `graphify-out/graph.json` exist, and fall back to normal source inspection
   when they do not.

### Safety and non-goals

- Do not run bare `graphify install`; it defaults to one platform rather than
  the generic Agent Skills location.
- Do not run `graphify agents install`, `graphify codex install`, or similar
  always-on setup commands because they can modify project instruction files or
  hooks.
- Do not scrape or dummy-install upstream `AGENTS.md` text into Agentbot
  templates. Agentbot owns a small reviewed policy block; version-specific
  operating detail stays in Graphify's installed skill.
- Do not automatically build graphs, install Git hooks, enable strict mode,
  purge generated data, stage files, commit, or push.
- Do not add Graphify to the curated `npx skills` manifest. Its skill is
  installed and versioned by the official Graphify CLI, not by an unrelated
  Git skill source.

Phase 5 was independent of the package-catalog and MCP work. Its completion did
not implement Phase 4; the Phase 4 migration gate is now the next workstream.

## Explicitly out of scope

- automatic Git staging, commits, pushes, resets, or destructive cleanup;
- MCP configuration in Phase 2;
- arbitrary profile-selected output paths;
- token values or secrets in repository files or workspace state;
- obsolete product names, legacy TUI variables, and broad profile modes;
- Hermes, Proxmox, vector databases, or always-on laptop services.

## Change log

| Date | Change |
|---|---|
| 2026-07-11 | Initial phase map created after the slim-bootstrap rework |
| 2026-07-18 | Reconciled Phases 0–1 with live Agentbot naming and entrypoints |
| 2026-07-18 | Marked Phase 2 complete after implementing profiles, renderer, local state, CLI, boot registration, menu, and validation |
| 2026-07-27 | Deferred Phases 3–4 and delivered Phase 5 as the independent Graphify integration phase |
| 2026-07-28 | Reconciled README, archive indexes, and Phase 4 design notes with the live Phase 5 boundary |
| 2026-07-28 | Selected Phase 4 as the next workstream and applied Slice 4M public-memory retirement in the working tree; review remains pending |
