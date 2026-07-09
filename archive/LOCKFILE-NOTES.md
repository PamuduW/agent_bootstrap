# Skills lockfile notes (2026-07-09)

> **Historical:** The `ImportError: cannot import name 'summarize_install_results'` issue described below is **fixed** in the slim bootstrap. `./install.sh skills install` now works via the Python CLI. This document is retained for lockfile strategy and install-history context.

## `./install.sh skills install` (historical — fixed)

Previously failed immediately with:

`ImportError: cannot import name 'summarize_install_results' from 'src.agent_bootstrap.skills_installer'`

The CLI path is preferred when `skills` is registered in `cli.py`; the bash fallback in `bin/skills-install.sh` was not used.

## Effective install (manual / bash fallback)

Curated sources were installed with `npx skills add … -g -y` (global scope), matching `bin/skills-install.sh`.

| Source | Result |
|--------|--------|
| `obra/superpowers` | OK |
| `full-statck-skills/devops-skills` | OK |
| `anmolnagpal/devops-skills` | OK |
| `jeffallan/claude-skills` | OK |
| `ShaishavMaisuria/research-paper-lifecycle-skills` | OK |
| `Akindu23/my-agent-skills` | OK |

Disabled sources in `skills.sources.yaml` were skipped (`graphify`, `obsidian-memory`).

**Installer bugs observed in `bin/skills-install.sh`:**

1. After `IFS=$'\t' read -ra skills`, the outer `while read` loop can break (IFS not restored before next line read).
2. `npx skills add` inherits stdin from the process-substitution/file redirect and can consume remaining lines; use `</dev/null` on `npx` or a dedicated file descriptor for the source list.

## Project `skills-lock.json`

Still a stub (`"sources": []`). Global installs (`-g`) do not populate the repo lockfile.

- `npx skills --help`: project lock is tied to **project-level** installs (`npx skills add <pkg>` without `-g`) and `skills experimental_install` (restore from project `skills-lock.json`).
- Running `npx skills experimental_install` in this repo reports: *No project skills found in skills-lock.json*.

## Global lock (authoritative for `-g` installs)

Pinned skill metadata lives at:

**`~/.agents/.skill-lock.json`**

(format `version: 3`, per-skill entries with `source`, `skillFolderHash`, etc.)

Do **not** copy this file into `skills-lock.json` by hand — schemas differ (project stub uses `sources: []` v1; global uses per-skill v3).

## Follow-up

- ~~Fix `summarize_install_results` (or remove broken import from `ui.py`) so `./install.sh skills install` works.~~ **Done** (slim bootstrap).
- Fix `bin/skills-install.sh` loop (IFS + stdin) if still relevant.
- **Decision (current):** global lock (`~/.agents/.skill-lock.json`) is source of truth for curated `-g` installs; project `skills-lock.json` remains a stub until CI needs a committed project lock.
