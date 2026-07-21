# Agentbot Review Sidecars

## Goal

When Agentbot encounters an existing regular instruction file that is not
owned by Agentbot or does not match the current template, it must preserve the
original and write a reviewable sibling template instead of failing or
overwriting user content.

## Scope

The behavior applies to workspace outputs rendered from `base/AGENTS.md`:

- `AGENTS.md`
- `CLAUDE.md`
- `.github/copilot-instructions.md`
- `.cursor/rules/agentbot-policy.mdc`

It also applies to the three global outputs rendered from `global/AGENTS.md`:

- `~/.codex/AGENTS.md`
- `~/.claude/AGENTS.md`
- `~/.claude/CLAUDE.md`

The canonical source files `base/AGENTS.md` and `global/AGENTS.md` remain
authoritative inputs. Missing canonical source files remain errors; this
feature does not invent a source template.

## Behavior

For each target file:

1. If the target is missing, create the canonical output directly.
2. If the target is Agentbot-owned and valid, update it directly.
3. If the target is a regular unowned or incompatible file, leave it
   unchanged and create a sibling review file.
4. If a review file already exists and is unchanged since Agentbot generated
   it, update that same review file to the newest template.
5. If a review file was edited and its recorded template version is stale,
   preserve it and use the next suffix (`_temp_1`, `_temp_2`, and so on).
6. If an edited review file already represents the current template version,
   preserve it without creating another copy on every run.

Review names use the target stem and suffix:

```text
AGENTS.md                         -> AGENTS_temp.md, AGENTS_temp_1.md
CLAUDE.md                         -> CLAUDE_temp.md, CLAUDE_temp_1.md
.github/copilot-instructions.md   -> .github/copilot-instructions_temp.md
.cursor/rules/agentbot-policy.mdc -> .cursor/rules/agentbot-policy_temp.mdc
```

`AGENTS_temp.md` contains the current base template. Other review files
contain the current generated output for their target.

## Review provenance

Each generated review file starts with an HTML comment containing a SHA-256
of the review body:

```md
<!-- Agentbot review template: sha256=<digest> -->
```

The digest is stored in the review file itself; no separate metadata file is
created. Agentbot compares the digest with the body to detect user edits and
can therefore update an untouched old review file after a template change.
The marker is ignored when recognizing a copied `AGENTS_temp.md` as a valid
canonical AGENTS file.

## Safety

Existing originals are never overwritten merely because they conflict.
Existing review files are never overwritten after user edits. Symlinks,
directories, and unsafe output locations remain hard errors because they are
filesystem-safety violations rather than ordinary template conflicts.

## Validation

Tests will verify direct creation/update, original preservation, review-file
refresh, suffix rollover, copied AGENTS review files, all workspace targets,
all global targets, and unchanged behavior for owned outputs.
