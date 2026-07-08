#!/usr/bin/env bash
# Symlink ~/.agents/skills/* -> ~/.claude/skills/* for Claude Code fallback.
set -euo pipefail

AGENTS_SKILLS="${HOME}/.agents/skills"
CLAUDE_SKILLS="${HOME}/.claude/skills"

info() {
  printf '[info] %s\n' "$*"
}

warn() {
  printf '[warn] %s\n' "$*" >&2
}

mkdir -p "$CLAUDE_SKILLS"

if [[ ! -d "$AGENTS_SKILLS" ]]; then
  info "no ${AGENTS_SKILLS}; skipping Claude skills bridge"
  exit 0
fi

shopt -s nullglob
linked=0
skipped=0

for source_dir in "$AGENTS_SKILLS"/*; do
  [[ -d "$source_dir" ]] || continue

  name="$(basename "$source_dir")"
  target="${CLAUDE_SKILLS}/${name}"

  if [[ -L "$target" ]]; then
    current="$(readlink "$target")"
    if [[ "$current" == "$source_dir" ]]; then
      linked=$((linked + 1))
      continue
    fi
    rm "$target"
    ln -s "$source_dir" "$target"
    info "updated bridge: ${target} -> ${source_dir}"
    linked=$((linked + 1))
    continue
  fi

  if [[ -e "$target" ]]; then
    warn "${target} exists and is not a symlink; skipping"
    skipped=$((skipped + 1))
    continue
  fi

  ln -s "$source_dir" "$target"
  info "bridged: ${target} -> ${source_dir}"
  linked=$((linked + 1))
done

info "Claude skills bridge complete (${linked} linked, ${skipped} skipped)"
