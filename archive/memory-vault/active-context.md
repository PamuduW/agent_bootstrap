# Active context

> Refresh when focus shifts. Agents may draft updates; you approve before commit.

**Last updated:** 2026-07-08

## Current focus

- Phase 7.1: scaffold memory vault in `agent_bootstrap/memory-vault/`
- Config plane solid: `agentboot`, skills via `npx skills`, `doctor` clean

## Active repos

| Repo | Role |
|------|------|
| `new_setup` | Master plan, research, orchestration |
| `agent_bootstrap` | Config plane — skills, exports, vault |
| `dotfiles` | Machine bootstrap (`dotfiles upgrade`) |

## Blockers

- Hermes / Proxmox home server — deferred (user handles later)
- Live mutations (`dotfiles upgrade`, `ext restore`) — need maintenance window

## Next 3 actions

1. Commit vault scaffold; open in Obsidian to verify layout
2. Run `./install.sh doctor` on WSL2; fix any drift
3. Populate `projects/` with one note per active repo
