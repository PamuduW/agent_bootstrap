# Agentbot expansion roadmap

**Status:** Phase 0 and Phase 1 are complete and verified against the live
repositories (2026-07-18). Phase 2 is the next implementation phase. Phases 3
and 4 remain deferred.

This is a living design roadmap, not a promise that the archived architecture
will be restored unchanged. The implementation, tests, and current README files
are the source of truth. Update this document when a design decision changes.

## Current system

| Area | Current source of truth | Status |
|------|-------------------------|--------|
| Agentbot CLI and menu | `install.sh`, `bin/agentbot`, `scripts/menu.sh` | Live |
| Per-repo bootstrap | `bin/agentbot boot`, `base/AGENTS.md`, `base/CLAUDE.md` | Live |
| Global baseline | `global/AGENTS.md` and `./install.sh global` | Live |
| Curated skills | `skills.sources.yaml`, `./install.sh skills ...` | Live |
| Dotfiles integration | sibling `dotfiles` `--agents` bridge | Live |
| Workspace render and tracked repos | `archive/` design/config plus Git history | Phase 2 |
| Package catalog and MCP bundles | `archive/catalog/`, `archive/mcp/` | Phase 3 |
| Durable memory and Graphify | `archive/memory-vault/` and disabled sources | Phase 4 |

`agent_bootstrap` remains the Git repository and clone directory. **Agentbot**
is the installed product and public command. Legacy symlink cleanup is isolated
to migration code and test fixtures; it is not part of the current public
surface.

## Phase dependency

```text
Phase 0: slim skills + global baseline + static repo bootstrap
    │
    ▼
Phase 1: standalone Agentbot menu + Dotfiles bridge + unified agentbot boot  ✅
    │
    ▼
Phase 2: profiles + workspace render + tracked workspaces + batch CLI
    │
    ▼
Phase 3: package catalog + profile-filtered MCP bundles
    │
    ▼
Phase 4: human-owned memory vault + on-demand Graphify
```

Hermes/Proxmox, Mem0, Graphiti, GraphRAG, and an always-on laptop harness are
separate future projects, not hidden requirements for these phases.

---

## Phase 0 — slim bootstrap ✅

The slim foundation is live:

- `skills.sources.yaml` declares curated upstream sources.
- `./install.sh skills install|update|list|doctor` manages skills through
  `npx skills` and the global lock.
- `./install.sh global` renders the authored `global/AGENTS.md` baseline to
  Codex and Claude surfaces.
- `agentbot boot` copies the canonical `AGENTS.md` and `CLAUDE.md` templates
  into a repository.
- `./install.sh doctor` validates the manifest, links, lock, and rendered
  outputs.

The personal skills repository is now a normal public Skills CLI source:
`PamuduW/agent_bootstrap_skills`, currently publishing `co-council`.

---

## Phase 1 — standalone UX + unified Agentbot ✅

**Goal:** Agentbot works without Dotfiles; Dotfiles is a thin launcher and
sibling-path resolver.

### Delivered

- The Agentbot menu is owned by `agent_bootstrap/scripts/menu.sh`.
- The menu covers status, install, update, token configuration, repository
  setup, command reference, doctor, and the reciprocal Dotfiles route.
- `./install.sh` with no arguments opens the menu on a controlling TTY.
- `agentbot` with no arguments opens the same menu after installation; a
  headless invocation gives explicit CLI guidance.
- Dotfiles `./install.sh --agents`, the Dotfiles menu’s Agentbot action, and
  `dotfiles agentbot` validate the sibling repository and launch its
  `install.sh` menu.
- `agentbot boot` is the single bootstrap command. Its default output is
  `AGENTS.md` plus `CLAUDE.md`; `--agents`, `--claude`, and `--force` select
  the current static-copy behavior.
- The legacy minimal/full split and pre-Agentbot binary are gone. Installation
  removes only an old symlink that can be proven to belong to this repository
  and preserves unrelated paths.
- The old archived package/workspace Apply TUI, workspace render, catalog,
  MCP filtering, and archived CLI subcommands remain out of scope.

The supported menu entrypoints are therefore `./install.sh` and `agentbot`.
`./install.sh menu` is not a command in the current contract.

### Phase 1 verification

The following checks passed in the development clones:

```bash
# agent_bootstrap
python3 -m unittest discover -s tests
bash tests/test_agentbot.sh
bash tests/test_agentbot_menu.sh

# dotfiles
bash tests/test_agentbot_bridge.sh
bash tests/test_main_menu.sh
bash tests/regression_paths.sh
```

The shell trees also pass `bash -n`. Documentation changes in this update are
the only intended working-tree changes; no commits or pushes are performed by
the maintenance workflow.

---

## Phase 2 — profiles, workspace render, and tracked workspaces

**Goal:** Keep one authored instruction source per repository while generating
the compatibility files required by each agent surface. Make that render
repeatable for one repository or a deliberate set of repositories.

Phase 2 is not “restore every archived file.” It is a controlled render
pipeline built around the stable Phase 1 entrypoints.

### The desired ownership model

```text
global/AGENTS.md                 machine-wide authored baseline
repo/AGENTS.md                   repository-authored policy + ## Project
        │
        ▼
   Agentbot profile              export policy and trust rules
        │
        ▼
   workspace render               generated compatibility surfaces
        │
        ├── repo/CLAUDE.md
        ├── repo/.github/copilot-instructions.md
        └── repo/.cursor/rules/bootstrap-skills.mdc
```

`AGENTS.md` remains the authored source. Generated files receive a clear
Agentbot marker, are idempotent, and are never treated as independent policy.
MCP files are deliberately excluded from the first Phase 2 slice; they belong
to the catalog-driven Phase 3 pipeline.

### 2.1 Profiles and `agentos.yaml`

Promote the archived [`agentos.yaml`](../agentos.yaml) into a live configuration
location after reviewing its schema. The existing design already expresses:

- an active profile such as `safe-default`;
- trust policy for community skills and executable scripts;
- export targets for Codex, Claude, Cursor, Copilot, and repository outputs;
- placeholders for the user’s home directory and workspace path.

The loader should reject unknown or malformed profiles before writing anything.
Profile selection should be explicit or use the documented safe default. A
profile controls *where* and *what kind* of output is generated; it does not
silently install arbitrary skills or execute scripts from a community source.

### 2.2 Single-workspace render

The first implementation slice should render one Git repository:

1. Resolve and validate the repository root.
2. Require or scaffold the authored repository `AGENTS.md`; do not treat an
   old generated file as canonical without an explicit decision.
3. Read the global baseline from `global/AGENTS.md`.
4. Read the repository’s `## Project` section and preserve the rest of the
   authored file.
5. Merge the global baseline and project overlay in a deterministic order.
6. Render only the surfaces enabled by the selected profile.
7. Write generated files atomically and report created, changed, skipped, and
   conflicting paths.
8. Add generated paths to the repository’s ignore policy only with an explicit,
   reviewable rule; never overwrite an unrelated user-owned file silently.

The merge must be deterministic and testable. Running the same render twice
without source changes must produce no second diff. Existing user-authored
`CLAUDE.md`, Cursor rules, or Copilot instructions need a clear conflict policy:
skip and report by default, with an explicit force/replace path only if we later
decide that generated ownership is appropriate.

### 2.3 Tracked workspace state

After single-workspace rendering is reliable, add local operator state for
repositories the user intentionally manages. The state belongs under the
Agentbot configuration area and must be ignored by Git; it is not a shared
project manifest and must not contain secrets.

The state model should record at least:

- canonical repository path;
- repository identity and last-known branch/commit;
- selected profile;
- last render result and timestamp;
- whether the repository is enabled for batch rendering.

Discovery may scan a user-supplied root for Git repositories, but discovery
must not make every directory a managed workspace automatically. Registration
and batch application need a visible preview and a confirmation boundary.

### 2.4 CLI and menu behavior

The planned public operations are:

```bash
./install.sh workspace ~/Dev/my-app   # render/register one workspace
./install.sh all ~/Dev                # preview/apply enabled workspaces below a root
./install.sh interactive              # review workspaces and apply selected changes
```

The exact flags may change during implementation, but the safety contract
should remain stable:

- repository state is inspected before rendering;
- dirty or ambiguous repositories are reported, not silently rewritten;
- generated changes are previewable;
- no `git add`, commit, push, or destructive cleanup occurs automatically;
- one failed workspace does not hide results for the others;
- the final report identifies every skipped, changed, and failed workspace.

`agentbot boot` should eventually call the single-workspace render path when
run inside a Git repository, while retaining the current static scaffold as a
safe fallback for a fresh target. This is how the command grows without
reintroducing a `--full` mode.

### 2.5 Phase 2 build order

1. Validate and promote the profile schema.
2. Restore/adapt the full render logic from Git history and archive templates.
3. Implement one-workspace render with atomic writes and idempotency tests.
4. Add local workspace registration and discovery.
5. Add `workspace`, `all`, and the optional interactive review surface.
6. Extend `agentbot boot` to invoke render for an existing Git repository.

### Phase 2 exit criteria

- One workspace can be rendered from global policy plus its project overlay.
- Re-running render is idempotent.
- Generated outputs are clearly marked and ignored appropriately.
- Workspace registration is explicit and local to the operator.
- Batch rendering produces an auditable per-workspace report.
- Tests cover merge order, missing overlays, conflicts, idempotency, and
  failure isolation.
- Existing Phase 0/1 tests remain green.

### Not in Phase 2

- Package enable/disable and MCP server filtering — Phase 3.
- Obsidian memory workflows and Graphify — Phase 4.
- Hermes, Proxmox, vector databases, or an always-on laptop service.

---

## Phase 3 — package catalog + MCP bundles

**Goal:** Curated packages determine which MCP servers and related artifacts
are rendered for a profile or workspace.

- Promote and validate `archive/catalog/packages.json`.
- Restore catalog load/filter and managed-artifact operations.
- Use package `mcp_keys` to filter the master `archive/mcp/mcp.json` list.
- Render only the selected MCP subset into the appropriate Cursor surfaces.
- Make `import-local` and `remove-managed` provenance-aware and reviewable.
- Extend Doctor to detect orphaned, conflicting, or unowned MCP entries.

Phase 3 depends on the Phase 2 profile and render contracts. It must not
become a second, unrelated configuration system.

---

## Phase 4 — durable memory + on-demand graphs

**Goal:** Preserve human-approved context that should survive individual
repository sessions without dumping a complete vault into every prompt.

- Populate `archive/memory-vault/` with active context, decisions, lessons,
  preferences, and project notes.
- Let agents draft memory changes; the user approves and commits them.
- Read small relevant slices or generated exports rather than the whole vault.
- Use Graphify only for a large repository where Markdown navigation and `rg`
  stop being sufficient.
- Keep `graphify` and `obsidian-memory` disabled until their source layouts and
  operational behavior are validated.

Hermes/SQLite FTS, Mem0, Graphiti, and GraphRAG remain trigger-based projects
outside this roadmap.

## Related documents

| Document | Role |
|----------|------|
| [stuff.md](./stuff.md) | Deferred capability map and restore boundaries |
| [stuff2.md](./stuff2.md) | Day-to-day impact of the deferred capabilities |
| [harness-architecture.md](./harness-architecture.md) | Three-plane model and memory tiers |
| [../README.md](../README.md) | Archive inventory and slim/live matrix |

## Changelog

| Date | Change |
|------|--------|
| 2026-07-11 | Initial phase map created after the slim-bootstrap rework |
| 2026-07-18 | Marked Phases 0–1 complete; reconciled Agentbot naming and entrypoints; expanded Phase 2 design |
