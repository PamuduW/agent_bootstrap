#!/usr/bin/env bash
# Symlink ~/.agents/skills/* -> ~/.claude/skills/* for Claude Code fallback.
set -euo pipefail

AGENTS_SKILLS="${HOME}/.agents/skills"
CLAUDE_SKILLS="${HOME}/.claude/skills"
VERBOSE="${AGENTBOT_BRIDGE_VERBOSE:-0}"

if [[ "${1:-}" == "--verbose" || "${1:-}" == "-v" ]]; then
  VERBOSE=1
fi

info() {
  printf '[info] %s\n' "$*"
}

warn() {
  printf '[warn] %s\n' "$*" >&2
}

resolve_path() {
  readlink -f "$1" 2>/dev/null || readlink "$1" 2>/dev/null || printf '%s' "$1"
}

mkdir -p "$CLAUDE_SKILLS"

if [[ ! -d "$AGENTS_SKILLS" ]]; then
  info "no ${AGENTS_SKILLS}; skipping Claude skills bridge"
  exit 0
fi

shopt -s nullglob
linked=0
updated=0
skipped=0

for source_dir in "$AGENTS_SKILLS"/*; do
  [[ -d "$source_dir" ]] || continue

  name="$(basename "$source_dir")"
  target="${CLAUDE_SKILLS}/${name}"
  source_resolved="$(resolve_path "$source_dir")"

  if [[ -L "$target" ]]; then
    current="$(resolve_path "$target")"
    if [[ "$current" == "$source_resolved" ]]; then
      linked=$((linked + 1))
      continue
    fi
    rm "$target"
    ln -s "$source_dir" "$target"
    if [[ "$VERBOSE" == 1 ]]; then
      info "updated bridge: ${target} -> ${source_dir}"
    fi
    updated=$((updated + 1))
    continue
  fi

  if [[ -e "$target" ]]; then
    warn "${target} exists and is not a symlink; skipping"
    skipped=$((skipped + 1))
    continue
  fi

  ln -s "$source_dir" "$target"
  if [[ "$VERBOSE" == 1 ]]; then
    info "bridged: ${target} -> ${source_dir}"
  fi
  linked=$((linked + 1))
done

msg="${linked} linked"
if (( updated > 0 )); then
  msg+=", ${updated} updated"
fi
if (( skipped > 0 )); then
  msg+=", ${skipped} skipped"
fi
if [[ -z "${AGENTBOT_TUI:-}${AGENTBOT_QUIET:-}" ]]; then
  info "Claude skills bridge complete (${msg})"
fi
