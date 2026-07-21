# Agentbot Review Sidecars Implementation Plan

> **For agentic workers:** Execute this plan inline in the current session. Do not delegate or commit automatically.

**Goal:** Preserve conflicting Agentbot instruction files and maintain
reviewable, checksum-tracked template sidecars that refresh safely over time.

**Architecture:** Add a small review-sidecar helper to `workspace_render.py`
that owns naming, checksum stamping, edit detection, and suffix selection.
Workspace planning will include sidecar actions alongside normal render actions.
`render.py` will use the same helper for the three global output paths and will
only replace outputs carrying Agentbot ownership markers.

**Tech Stack:** Python 3 standard library, `unittest`, existing atomic
workspace writer, existing global renderer.

## Global Constraints

- Preserve unowned originals byte-for-byte.
- Update missing and Agentbot-owned targets directly.
- Store review checksums inside review files as HTML comments.
- Never overwrite an edited review file; use the next numeric suffix.
- Keep canonical `base/AGENTS.md` and `global/AGENTS.md` as source files.
- Keep symlink and non-regular output safety failures.
- Do not add dependencies, commit, push, or change unrelated repositories.

## File Map

- Create: `docs/superpowers/specs/2026-07-21-agentbot-review-sidecars-design.md`
  — approved behavior and safety contract.
- Create: `docs/superpowers/plans/2026-07-21-agentbot-review-sidecars.md`
  — this executable plan.
- Modify: `src/workspace_render.py` — sidecar naming/checksum logic and
  workspace render actions.
- Modify: `src/workspace_service.py` — read existing sidecars and keep their
  filesystem safety checks.
- Modify: `src/render.py` — protect global outputs and generate/refresh
  sidecars.
- Modify: `tests/test_workspace_render.py` — red/green coverage for workspace
  sidecars and rollover.
- Modify: `tests/test_workspace_service.py` — apply behavior and preservation
  coverage.
- Modify: `tests/test_bootstrap_engine.py` — global output ownership and
  sidecar coverage.
- Modify: `README.md` — document conflict sidecars and naming.

### Task 1: Workspace sidecar contract

**Files:** `tests/test_workspace_render.py`, `src/workspace_render.py`

- [x] Write tests proving an unowned compatibility file yields a create action
  for `CLAUDE_temp.md`, preserves the original action, and places the current
  generated content in the sidecar.
- [x] Write tests proving an unmarked custom `AGENTS.md` yields
  `AGENTS_temp.md` containing the base template while preserving the custom
  file.
- [x] Write tests proving an unedited stamped sidecar is updated in place when
  the desired template changes.
- [x] Write tests proving an edited stale sidecar is preserved and the next
  suffix is created, while an edited sidecar for the current version does not
  create another copy.
- [x] Run the focused tests and confirm they fail because review-sidecar
  actions do not exist yet.
- [x] Add a checksum marker parser/stamper and deterministic sidecar selector
  in `src/workspace_render.py`.
- [x] Change workspace planning to include sidecar actions without marking
  ordinary regular-file template mismatches as fatal conflicts.
- [x] Keep malformed filesystem objects as conflicts and make the AGENTS
  marker/parser ignore the review checksum comment when recognizing a copied
  template.
- [x] Run the focused tests and confirm they pass.

### Task 2: Workspace apply and service integration

**Files:** `tests/test_workspace_service.py`, `src/workspace_service.py`

- [x] Add a test that applying a workspace with an unowned compatibility file
  leaves that file unchanged, writes its temp sidecar, and registers the
  workspace successfully.
- [x] Add a test that a second apply refreshes an untouched sidecar and does
  not replace an edited sidecar.
- [x] Extend existing-file discovery to read the deterministic sidecar names
  needed by the selected outputs, including numeric suffixes.
- [x] Run the focused service tests and confirm they pass.

### Task 3: Global output protection

**Files:** `tests/test_bootstrap_engine.py`, `src/render.py`

- [x] Add tests proving missing global outputs are created directly and
  Agentbot-owned outputs are updated directly.
- [x] Add tests proving unowned Codex and Claude outputs remain unchanged and
  receive the correct temp sidecars.
- [x] Add tests proving an untouched global sidecar refreshes, while an edited
  stale sidecar rolls to `_1`.
- [x] Run the focused global tests and confirm they fail before implementation.
- [x] Add global output ownership checks and reuse the review checksum helper
  for `~/.codex/AGENTS.md`, `~/.claude/AGENTS.md`, and
  `~/.claude/CLAUDE.md`.
- [x] Run the focused global tests and confirm they pass.

### Task 4: Documentation and regression validation

**Files:** `README.md`, all changed tests and source files

- [x] Add a concise README section describing preserved originals,
  `*_temp.md` naming, checksum markers, and suffix rollover.
- [x] Run the focused Python test modules.
- [x] Run `python3 -m unittest discover -s tests`.
- [x] Run `bash tests/test_agentbot.sh`, `bash tests/test_agentbot_menu.sh`,
  and `git diff --check`.
- [x] Inspect the complete diff and verify no sibling repository changed.
