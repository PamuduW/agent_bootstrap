# OpenClaw Integration Plan

This document tracks how the Bootstrap-first architecture should evolve into an
OpenClaw-compatible adapter in a future phase.

## Current Direction

- Keep `agent_bootstrap` as the primary control plane for Codex CLI, Cursor,
  Copilot, and Claude Code readiness.
- Treat OpenClaw as a future adapter, not the v1 runtime foundation.
- Preserve one canonical authored `AGENTS.md` per scope and map OpenClaw onto
  that model later.

## Planned Adapter Shape

- Reuse the canonical global `AGENTS.md` as the machine-level baseline.
- Reuse repo `AGENTS.md` files as project overlays.
- Generate any OpenClaw-required workspace files from the merged canonical
  instructions instead of introducing a second authored policy format.
- Keep OpenClaw-specific auth/runtime configuration isolated in the adapter
  layer.

## Auth Notes

- Prefer Codex/ChatGPT-login-compatible authentication paths over API-key-only
  designs where OpenClaw supports them.
- Avoid assuming paid API credits; design for the current subscription mix
  first.

## Migration Notes

- The old shell implementation mixed discovery presence, local enablement, and
  repo management into the same flags. The future OpenClaw adapter must keep
  those states separate too.
- Generated compatibility files should remain disposable outputs. OpenClaw
  should consume rendered artifacts or generated wrappers, not become the
  canonical source of instructions.
