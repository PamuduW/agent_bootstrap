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

warn() {
  printf '[warn] %s\n' "$*" >&2
}

bootstrap_quiet() {
  [[ -n "${AGENT_BOOTSTRAP_TUI:-}${AGENT_BOOTSTRAP_QUIET:-}" ]]
}

log_info() {
  bootstrap_quiet && return 0
  info "$@"
}

check_deps() {
  if ! command -v python3 >/dev/null 2>&1; then
    die "python3 is required"
  fi
  if ! python3 -c "import yaml" >/dev/null 2>&1; then
    die "PyYAML is required (run: python3 -m pip install -r requirements.txt)"
  fi
  if ! command -v node >/dev/null 2>&1; then
    die "node is required (install Node.js for npx skills)"
  fi
  if ! command -v npx >/dev/null 2>&1; then
    die "npx is required (install Node.js/npm for npx skills)"
  fi
}

run_cli() {
  python3 -m src.cli --root "$BOOTSTRAP_DIR" "$@"
}

cli_ready() {
  python3 -m src.cli --root "$BOOTSTRAP_DIR" status >/dev/null 2>&1
}

run_global_render() {
  if cli_ready; then
    run_cli global
    return $?
  fi
  python3 - <<'PY'
from pathlib import Path
from src.paths import default_paths
from src.service import BootstrapService

BootstrapService(default_paths(Path(".").resolve())).render_global()
PY
}

run_slim_doctor() {
  if cli_ready; then
    run_cli doctor
    return $?
  fi
  python3 - <<'PY'
import sys
from pathlib import Path
from src.paths import default_paths
from src.service import BootstrapService
from src.ui import print_doctor_summary

paths = default_paths(Path(".").resolve())
service = BootstrapService(paths)
sys.exit(print_doctor_summary(service.doctor_issues() + service.skills_doctor_issues()))
PY
}

run_slim_status() {
  if cli_ready; then
    run_cli status "$@"
    return $?
  fi
  python3 - <<'PY'
import sys
from pathlib import Path
from src.paths import default_paths
from src.service import BootstrapService
from src.ui import print_status_summary

paths = default_paths(Path(".").resolve())
service = BootstrapService(paths)
summary = service.status_summary()
print_status_summary(
    installed_skills=int(summary["installed_skills"]),
    global_agents_exists=bool(summary["global_agents_exists"]),
    skills_sources_exists=bool(summary["skills_sources_exists"]),
    enabled_sources=int(summary["enabled_sources"]),
    global_lock_exists=bool(summary["global_lock_exists"]),
    global_lock_skills=int(summary["global_lock_skills"]),
    claude_bridge_links=int(summary["claude_bridge_links"]),
    doctor_issue_count=int(summary["doctor_issue_count"]),
)
PY
}

cli_supports_skills() {
  cli_ready
}

cli_supports_bootstrap() {
  cli_ready
}

list_installed_skills_fallback() {
  python3 - <<'PY'
from pathlib import Path
from src.paths import default_paths
from src.service import BootstrapService

skills = BootstrapService(default_paths(Path(".").resolve())).list_skills()
if not skills:
    print("No installed skills found.")
else:
    print("\n=== Installed Skills ===")
    for skill in skills:
        print(skill)
PY
}

refresh_agent_outputs_fallback() {
  run_claude_bridge
  run_global_render
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
      refresh_agent_outputs_fallback
      ;;
    update)
      "$SKILLS_INSTALL_SH" update
      refresh_agent_outputs_fallback
      ;;
    list)
      list_installed_skills_fallback
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
  log_info "linked ${target} -> ${source}"
}

run_bootstrap() {
  check_deps
  log_info "bootstrapping agent_bootstrap from ${BOOTSTRAP_DIR}"

  local rc=0
  if cli_supports_bootstrap; then
    run_cli bootstrap || rc=$?
  else
    if ! cli_ready; then
      warn "slim CLI unavailable — using bash fallback (run: git checkout -- src/cli.py)"
    fi
    export AGENT_BOOTSTRAP_QUIET="${AGENT_BOOTSTRAP_QUIET:-${AGENT_BOOTSTRAP_TUI:-}}"
    run_skills install || rc=$?
    run_claude_bridge
    run_global_render || rc=$?
    run_slim_doctor || true
  fi

  link_agentboot
  log_info "bootstrap complete"
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
      case "$cmd" in
      global) run_global_render "${@:2}" ;;
      doctor) run_slim_doctor "${@:2}" ;;
      status) run_slim_status "${@:2}" ;;
      esac
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
