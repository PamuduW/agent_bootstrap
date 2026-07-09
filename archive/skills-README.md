# Personal skills pack

This directory holds **your authored skills** only — one folder per skill, each with a `SKILL.md`.

The old vendored plugin mirrors (52 directories) were moved to `temp/archive/skills/` (outside this repo) during the Stage 5 rebuild. Upstream skills are installed globally via `npx skills` from entries in `skills.sources.yaml`, not vendored here.

## Adding a personal skill

1. Create `skills/<skill-name>/SKILL.md` following the [Agent Skills spec](https://agentskills.io).
2. Run `./install.sh skills install` (or `python3 -m src.agent_bootstrap.cli skills install`) to install `./skills` to all four agents.
3. Commit the skill folder; `skills-lock.json` records what was installed.

## Do not

- Re-vendor upstream repos into this tree — use `skills.sources.yaml` instead.
- Edit generated global installs under `~/.agents/skills/` — change sources or this pack, then re-run install/update.
