# Lifecycle and updates

## Install

Install validates the repository, installs enabled curated skills, refreshes
Graphify and Boost when their Dotfiles-owned CLIs exist, renders managed global
outputs, runs Doctor, and creates the user launcher link. Installation does not
copy the checkout.

## Lifecycle update

The lifecycle builds a read-only plan before it writes. The plan covers skill
source reconciliation, optional integrations, registered workspaces, and
global outputs. Apply verifies that planned inputs have not changed, confirms
source-owned deltas once, and uses the shared rollback boundary for managed
surfaces.

Use `agentbot update --dry-run` before an interactive update. `agentbot full`
runs install and update together.

## Repository update gate

Repository maintenance validates the expected origin, inspects local changes,
fetches, and classifies the checkout as current, ahead, behind, or diverged. A
clean confirmed behind checkout advances with a fast-forward-only pull.

Replacing dirty, ahead, or diverged state requires explicit authorization.
Before replacement, Agentbot preserves tracked and untracked changes in a
stash and local commits on a timestamped `recovery/agentbot-*` branch. It
verifies those backups before reset. It does not run `git clean`, delete
recovery data, commit, push, or force-push.

When an update changes the checkout, the old process exits with status 2 so a
caller can restart from the new code. Detached HEAD, missing upstream,
declined recovery, failed fetch, or failed backup stops downstream work.

`dotfiles full-update` is the system-maintenance orchestrator. It can authorize
the documented repository recovery, restart Agentbot after a self-update, and
run the non-interactive lifecycle update.
