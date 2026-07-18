# Active context

> Refresh when focus shifts. Agents may draft updates; you approve before commit.

**Last updated:** 2026-07-18

## Current focus

- Phase 1 complete: standalone Agentbot menu, Dotfiles bridge, and unified `agentbot boot`
- Phase 2 is next: profiles, workspace render, and tracked workspace state

## Active repos

| Repo | Role |
|------|------|
| `new_setup` | Master plan, research, orchestration |
| `agent_bootstrap` | Config plane — skills, Agentbot, and global outputs |
| `dotfiles` | Machine bootstrap (`dotfiles upgrade`) |

## Blockers

- Hermes / Proxmox home server — deferred (user handles later)
- Live mutations outside the completed bootstrap flows — use the relevant repo runbook and a maintenance window

## Next 3 actions

1. Review the Phase 2 design in `archive/docs/stuff3.md`
2. Keep `./install.sh doctor` and the Phase 1 test gates green
3. Decide which repository should be the first tracked-workspace pilot
