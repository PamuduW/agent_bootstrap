#!/usr/bin/env bash
# Install curated skills from skills.sources.yaml via npx skills (Vercel).
set -euo pipefail

BOOTSTRAP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCES_FILE="${BOOTSTRAP_DIR}/skills.sources.yaml"
# shellcheck source=scripts/lib/github_token.sh
source "${BOOTSTRAP_DIR}/scripts/lib/github_token.sh"

github_token_child() (
  github_token_export_if_valid
  "$@"
)

AGENT_FLAGS=(-a cursor -a codex -a claude-code -a github-copilot)
GLOBAL_FLAGS=(-g -y)

die() {
  printf '[err] %s\n' "$*" >&2
  exit 1
}

info() {
  printf '[info] %s\n' "$*"
}

require_npx() {
  if ! command -v npx >/dev/null 2>&1; then
    die "npx is required (install Node.js/npm)"
  fi
}

parse_sources() {
  if [[ ! -f "$SOURCES_FILE" ]]; then
    die "missing skills sources file: $SOURCES_FILE"
  fi

  python3 - "$SOURCES_FILE" <<'PY'
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
current = None

def flush():
    global current
    if not current:
        return
    repo = current.get("repo")
    enabled = current.get("enabled", True)
    skills = current.get("skills", [])
    if enabled and repo and skills:
        print(f"{repo}\t" + "\t".join(skills))
    current = None

for raw in path.read_text(encoding="utf-8").splitlines():
    line = raw.split("#", 1)[0].rstrip()
    if not line.strip():
        continue

    if m := re.match(r"^\s*-\s+id:\s+(.+)$", line):
        flush()
        current = {"id": m.group(1).strip(), "repo": None, "skills": [], "enabled": True}
        continue

    if not current:
        continue

    if m := re.match(r"^\s+repo:\s+(.+)$", line):
        value = m.group(1).strip()
        current["repo"] = None if value == "null" else value
    elif m := re.match(r"^\s+skills:\s+(.+)$", line):
        value = m.group(1).strip().strip("\"'")
        if value.lower() == "all":
            current["skills"] = ["*"]
    elif re.match(r"^\s+enabled:\s+false\s*$", line):
        current["enabled"] = False
    elif m := re.match(r"^\s+-\s+(.+)$", line):
        current["skills"].append(m.group(1).strip())

flush()
PY
}

install_source() {
  local repo="$1"
  shift
  local -a skill_flags=()
  local skill

  for skill in "$@"; do
    skill_flags+=(--skill "$skill")
  done

  if [[ -n "${AGENTBOT_QUIET:-}${AGENTBOT_TUI:-}" ]]; then
    if github_token_child npx skills add "$repo" --full-depth "${skill_flags[@]}" "${AGENT_FLAGS[@]}" "${GLOBAL_FLAGS[@]}" </dev/null >/dev/null 2>&1; then
      info "installed skills from ${repo}"
    else
      die "failed installing skills from ${repo}"
    fi
    return 0
  fi

  info "installing skills from ${repo}"
  github_token_child npx skills add "$repo" --full-depth "${skill_flags[@]}" "${AGENT_FLAGS[@]}" "${GLOBAL_FLAGS[@]}" </dev/null
}

install_all() {
  require_npx

  local line repo rest old_ifs
  local -a skills=()

  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ -z "$line" ]] && continue
    repo="${line%%$'\t'*}"
    rest="${line#*$'\t'}"
    skills=()
    if [[ -n "$rest" ]]; then
      old_ifs="$IFS"
      IFS=$'\t' read -ra skills <<<"$rest"
      IFS="$old_ifs"
    fi
    install_source "$repo" "${skills[@]}"
  done < <(parse_sources)
}

update_all() {
  require_npx

  if github_token_child npx skills update --help >/dev/null 2>&1; then
    if [[ -n "${AGENTBOT_QUIET:-}${AGENTBOT_TUI:-}" ]]; then
      github_token_child npx skills update -g -y </dev/null >/dev/null 2>&1
    else
      info "running npx skills update -g"
      github_token_child npx skills update -g -y </dev/null
    fi
    return 0
  fi

  info "npx skills update unavailable; re-running install"
  install_all
}

list_installed() {
  local skills_home="${HOME}/.agents/skills"

  if [[ ! -d "$skills_home" ]]; then
    printf 'No installed skills found.\n'
    return 0
  fi

  local -a skills=()
  local entry name
  shopt -s nullglob
  for entry in "$skills_home"/*/; do
    name="$(basename "$entry")"
    [[ -n "$name" ]] && skills+=("$name")
  done
  shopt -u nullglob

  if [[ "${#skills[@]}" -eq 0 ]]; then
    printf 'No installed skills found.\n'
    return 0
  fi

  printf '\n=== Installed Skills ===\n'
  printf '%s\n' "${skills[@]}" | LC_ALL=C sort
}

doctor() {
  local issues=0

  if ! command -v node >/dev/null 2>&1; then
    printf '[fail] node is not installed\n' >&2
    issues=$((issues + 1))
  fi
  if ! command -v npx >/dev/null 2>&1; then
    printf '[fail] npx is not installed\n' >&2
    issues=$((issues + 1))
  fi
  if [[ ! -f "$SOURCES_FILE" ]]; then
    printf '[fail] missing %s\n' "$SOURCES_FILE" >&2
    issues=$((issues + 1))
  fi
  if [[ ! -d "${HOME}/.agents/skills" ]]; then
    printf '[warn] ~/.agents/skills does not exist yet\n' >&2
  fi
  if [[ ! -d "${HOME}/.claude/skills" ]]; then
    printf '[warn] ~/.claude/skills does not exist yet\n' >&2
  fi

  if [[ "$issues" -gt 0 ]]; then
    exit 1
  fi

  info "skills installer prerequisites look OK"
}

usage() {
  cat <<EOF
Usage: $(basename "$0") <command>

Commands:
  install   Install curated upstream skills from skills.sources.yaml
  update|upgrade
            Refresh globally installed skills from ~/.agents/.skill-lock.json
  list      List installed skills under ~/.agents/skills
  doctor    Validate installer prerequisites
EOF
}

main() {
  local cmd="${1:-install}"
  shift || true

  case "$cmd" in
    install)
      install_all
      ;;
    update|upgrade)
      update_all
      ;;
    list)
      list_installed
      ;;
    doctor)
      doctor
      ;;
    -h|--help|help)
      usage
      ;;
    *)
      die "unknown command: $cmd"
      ;;
  esac
}

main "$@"
