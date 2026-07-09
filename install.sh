#!/usr/bin/env bash
set -euo pipefail

BOOTSTRAP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export AGENT_BOOTSTRAP_HOME="$BOOTSTRAP_DIR"

SKILLS_INSTALL_SH="${BOOTSTRAP_DIR}/bin/skills-install.sh"
CLAUDE_BRIDGE_SH="${BOOTSTRAP_DIR}/bin/claude-skills-bridge.sh"

die() {
  printf '[err] %s\n' "$*" >&2
  exit 1
}

info() {
  printf '[info] %s\n' "$*"
}

check_deps() {
  if ! command -v python3 >/dev/null 2>&1; then
    die "python3 is required"
  fi
  if ! command -v node >/dev/null 2>&1; then
    die "node is required (install Node.js for npx skills)"
  fi
  if ! command -v npx >/dev/null 2>&1; then
    die "npx is required (install Node.js/npm for npx skills)"
  fi
}

run_cli() {
  python3 -m src.agent_bootstrap.cli --root "$BOOTSTRAP_DIR" "$@"
}

cli_ready() {
  python3 -m src.agent_bootstrap.cli --root "$BOOTSTRAP_DIR" status >/dev/null 2>&1
}

cli_supports_skills() {
  if ! cli_ready; then
    return 1
  fi
  if ! grep -q '"skills"' "${BOOTSTRAP_DIR}/src/agent_bootstrap/cli.py" 2>/dev/null; then
    return 1
  fi

  local output=""
  if output="$(python3 -m src.agent_bootstrap.cli --root "$BOOTSTRAP_DIR" skills list 2>&1)"; then
    return 0
  fi

  if [[ "$output" == *"unknown command"* ]]; then
    return 1
  fi

  printf '%s\n' "$output" >&2
  return 1
}

cli_supports_bootstrap() {
  cli_ready && grep -q '"bootstrap"' "${BOOTSTRAP_DIR}/src/agent_bootstrap/cli.py" 2>/dev/null
}

run_skills() {
  local subcmd="$1"
  shift

  if cli_supports_skills; then
    run_cli skills "$subcmd" "$@"
    return $?
  fi

  case "$subcmd" in
    install)
      "$SKILLS_INSTALL_SH" install
      ;;
    update)
      "$SKILLS_INSTALL_SH" update
      ;;
    list)
      "$SKILLS_INSTALL_SH" list
      ;;
    doctor)
      "$SKILLS_INSTALL_SH" doctor
      ;;
    *)
      die "skills subcommand not supported by CLI fallback: ${subcmd}"
      ;;
  esac
}

run_claude_bridge() {
  "$CLAUDE_BRIDGE_SH"
}

link_agentboot() {
  local source="${BOOTSTRAP_DIR}/bin/agentboot"
  local target="${HOME}/bin/agentboot"

  mkdir -p "${HOME}/bin"
  ln -sf "$source" "$target"
  info "linked ${target} -> ${source}"
}

run_bootstrap() {
  check_deps
  info "bootstrapping agent_bootstrap from ${BOOTSTRAP_DIR}"

  local rc=0
  if cli_supports_bootstrap; then
    run_cli bootstrap || rc=$?
  else
    run_skills install || rc=$?
    run_claude_bridge
    run_cli global || rc=$?
    run_cli doctor || true
  fi

  link_agentboot
  info "bootstrap complete"
  return "$rc"
}

map_legacy_flags() {
  if [[ $# -eq 0 ]]; then
    return 0
  fi

  case "$1" in
    --status) set -- status "${@:2}" ;;
    --global) set -- global "${@:2}" ;;
    --workspace|--all)
      die "workspace/all render is archived — see archive/README.md"
      ;;
  esac
}

usage() {
  cat <<EOF
Usage: ./install.sh [command] [args]

Commands:
  (default)              Full bootstrap: skills install, Claude bridge, render global, doctor
  bootstrap              Same as default
  skills install         Install curated upstream skills from skills.sources.yaml
  skills update          Refresh global skills from ~/.agents/.skill-lock.json
  skills list            List installed skills
  skills doctor          Validate skills installer prerequisites
  doctor                 Run slim doctor (skills + global baseline)
  status                 Show skills and global render status
  global                 Render global agent outputs
  link-agentboot         Symlink bin/agentboot -> ~/bin/agentboot (idempotent)

After bootstrap, run agentboot in any repo to scaffold AGENTS.md + CLAUDE.md.
Ensure ~/bin is on PATH (install.sh creates ~/bin/agentboot when bin/agentboot exists).

Archived commands (see archive/README.md): workspace, all, interactive,
import-local, remove-managed, delete-local.

Legacy flags (backward compatible):
  --status, --global
EOF
}

main() {
  cd "$BOOTSTRAP_DIR"

  if [[ $# -gt 0 ]]; then
    map_legacy_flags "$@"
  fi

  local cmd="${1:-bootstrap}"

  case "$cmd" in
    ""|bootstrap|install)
      run_bootstrap
      ;;
    skills)
      check_deps
      if [[ $# -lt 2 ]]; then
        die "usage: ./install.sh skills <install|update|list|doctor>"
      fi
      run_skills "${2}" "${@:3}"
      ;;
    doctor|status|global)
      if [[ "$cmd" == "global" ]]; then
        check_deps
      fi
      run_cli "$cmd" "${@:2}"
      ;;
    link-agentboot)
      link_agentboot
      ;;
    workspace|all|interactive|import-local|remove-managed|delete-local)
      die "${cmd} is archived — see archive/README.md"
      ;;
    -h|--help|help)
      usage
      ;;
    *)
      die "unknown command: ${cmd} (run ./install.sh --help)"
      ;;
  esac
}

main "$@"
