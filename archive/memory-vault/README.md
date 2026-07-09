# Memory vault

Obsidian-compatible, **git-tracked** memory store in the archived config plane (`agent_bootstrap/archive/memory-vault/`).

## Policy — human-owned

| Role | Who |
|------|-----|
| **Draft** | Agents may propose edits to vault files |
| **Approve** | You review and commit — no unsupervised self-writes |
| **Source of truth** | This repo, not agent session memory |

Agents read the vault for durable context. Ephemeral chat state does not replace it.

## Layout

```
archive/memory-vault/
├── active-context.md      # Current focus (refresh often)
├── preferences.md         # Stable personal defaults
├── decisions/             # ADRs — dated, immutable once accepted
├── lessons/               # Postmortems and learned patterns
├── projects/              # Per-repo notes index
└── agent-relationships/   # Per-tool contracts
```

## Obsidian

Open this folder as a vault in Obsidian (or any markdown editor). Wikilinks and tags work; no plugins required.

## Three-plane context

- **Config plane** — this repo (skills, AGENTS.md exports, vault)
- **Work plane** — WSL2 laptop, CLI agents only (Cursor, Claude Code, Codex, Copilot)
- **Control plane** — Hermes on home server (Proxmox) — **deferred**; not on the laptop

## Sync

Changes flow via `git pull` / `git push` on `agent_bootstrap`. When Hermes lands on the server, vault markdown syncs the same way — no separate memory silo.
