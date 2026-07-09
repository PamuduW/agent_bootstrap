# ADR: Three-plane agent architecture

**Date:** 2026-07-08
**Status:** accepted

## Context

Daily coding needs fast, first-party CLIs. Persistent memory, cron, and background automation need an always-on agent. A single tool cannot serve both without over-building on the laptop or under-serving server automation.

## Decision

Split into three planes:

| Plane | Location | Role |
|-------|----------|------|
| **Control** | Home server (Proxmox VM/LXC) | Hermes — memory, cron, messaging, scoped automation |
| **Work** | WSL2 laptop | Native CLIs (Cursor, Claude Code, Codex, Copilot); opencode optional for experiments |
| **Config** | `agent_bootstrap` git repo | Canonical AGENTS.md, skills, MCP, Obsidian vault — feeds all agents |

Hermes is **deferred** until the home server is ready. The laptop stays CLI-only; no always-on harness locally.

## Consequences

- Config plane (`agent_bootstrap`) is the keystone — invest here first
- Memory vault is git-tracked markdown, human-approved writes
- opencode/OpenRouter are work-plane experiments, not daily requirements
- Pi-style "one CLI for all subscriptions" is dropped (ToS/billing fragility)
