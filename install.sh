#!/usr/bin/env bash
set -euo pipefail

AGENTBOT_HOME="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export AGENTBOT_HOME
REPO_ROOT="$AGENTBOT_HOME"
# shellcheck source=scripts/lib/github_token.sh
source "${REPO_ROOT}/scripts/lib/github_token.sh"

AGENTBOT_OUT_RESET=''
AGENTBOT_OUT_CYAN=''
AGENTBOT_OUT_YELLOW=''
AGENTBOT_OUT_RED=''
if [[ -z "${NO_COLOR:-}" && ( -t 1 || -t 0 || -n "${AGENTBOT_TUI:-}" || -n "${FORCE_COLOR:-}" ) ]]; then
  AGENTBOT_OUT_RESET=$'\033[0m'
  AGENTBOT_OUT_CYAN=$'\033[36m'
  AGENTBOT_OUT_YELLOW=$'\033[33m'
  AGENTBOT_OUT_RED=$'\033[31m'
fi

SKILLS_INSTALL_SH="${REPO_ROOT}/bin/skills-install.sh"
CLAUDE_BRIDGE_SH="${REPO_ROOT}/bin/claude-skills-bridge.sh"

github_token_child() (
  github_token_export_if_valid
  "$@"
)

die() {
  printf '%s[err]%s %s\n' "$AGENTBOT_OUT_RED" "$AGENTBOT_OUT_RESET" "$*" >&2
  exit 1
}

info() {
  printf '%s[info]%s %s\n' "$AGENTBOT_OUT_CYAN" "$AGENTBOT_OUT_RESET" "$*"
}

warn() {
  printf '%s[warn]%s %s\n' "$AGENTBOT_OUT_YELLOW" "$AGENTBOT_OUT_RESET" "$*" >&2
}

bootstrap_quiet() {
  [[ -n "${AGENTBOT_TUI:-}${AGENTBOT_QUIET:-}" ]]
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
  python3 -m src.cli --root "$REPO_ROOT" "$@"
}

cli_ready() {
  python3 -m src.cli --root "$REPO_ROOT" status >/dev/null 2>&1
}

run_global_render() {
  if cli_ready; then
    run_cli global
    return $?
  fi
  python3 - <<'PY'
from pathlib import Path
from src.paths import default_paths
from src.service import AgentbotService

AgentbotService(default_paths(Path(".").resolve())).render_global()
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
from src.service import AgentbotService
from src.ui import print_doctor_summary

paths = default_paths(Path(".").resolve())
service = AgentbotService(paths)
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
from src.service import AgentbotService
from src.ui import print_status_summary

paths = default_paths(Path(".").resolve())
service = AgentbotService(paths)
summary = service.status_summary()
print_status_summary(
    installed_skills=int(summary["installed_skills"]),
    global_agents_exists=bool(summary["global_agents_exists"]),
    skills_sources_exists=bool(summary["skills_sources_exists"]),
    enabled_sources=int(summary["enabled_sources"]),
    global_lock_exists=bool(summary["global_lock_exists"]),
    global_lock_skills=int(summary["global_lock_skills"]),
    claude_bridge_links=int(summary["claude_bridge_links"]),
    claude_statusline_state=str(summary.get("claude_statusline_state", "unknown")),
    manual_skill_count=int(summary["manual_skill_count"]),
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
from src.service import AgentbotService

skills = AgentbotService(default_paths(Path(".").resolve())).list_skills()
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
    case "$subcmd" in
      install|update|upgrade) github_token_child run_cli skills "$subcmd" "$@" ;;
      *) run_cli skills "$subcmd" "$@" ;;
    esac
    return $?
  fi

  case "$subcmd" in
    install)
      "$SKILLS_INSTALL_SH" install
      refresh_agent_outputs_fallback
      ;;
    update|upgrade)
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

cleanup_owned_old_agentboot_link() {
  local old_link="${HOME}/bin/agentboot" raw resolved
  [[ -e "$old_link" || -L "$old_link" ]] || return 0
  if [[ ! -L "$old_link" ]]; then
    warn "preserving non-symlink old path: ${old_link}"
    return 0
  fi
  raw="$(readlink -- "$old_link" 2>/dev/null || true)"
  if [[ -z "$raw" ]]; then
    warn "preserving unprovable old symlink: ${old_link}"
    return 0
  fi
  if [[ "$raw" == /* ]]; then resolved="$(realpath -m -- "$raw")"
  else resolved="$(realpath -m -- "$(dirname "$old_link")/$raw")"; fi
  if [[ "$resolved" == "$(realpath -m -- "$AGENTBOT_HOME/bin/agentboot")" ]]; then
    rm -- "$old_link"
    log_info "removed owned old link: ${old_link}"
  else
    warn "preserving foreign old symlink: ${old_link} -> ${raw}"
  fi
}

link_agentbot() {
  local source="${AGENTBOT_HOME}/bin/agentbot"
  local target="${HOME}/bin/agentbot"
  [[ -x "$source" ]] || die "Agentbot executable is missing: $source"
  mkdir -p "${HOME}/bin"
  ln -sfn "$source" "$target"
  log_info "linked ${target} -> ${source}"
}

run_bootstrap_backend() {
  check_deps
  log_info "installing Agentbot from ${REPO_ROOT}"

  local rc=0
  if cli_supports_bootstrap; then
    github_token_child run_cli bootstrap || rc=$?
  else
    if ! cli_ready; then
      warn "slim CLI unavailable — using bash fallback (run: git checkout -- src/cli.py)"
    fi
    export AGENTBOT_QUIET="${AGENTBOT_QUIET:-${AGENTBOT_TUI:-}}"
    run_skills install || rc=$?
    run_claude_bridge
    run_global_render || rc=$?
    run_slim_doctor || true
  fi

  return "$rc"
}

run_install() {
  local rc=0
  run_bootstrap_backend || rc=$?
  cleanup_owned_old_agentboot_link
  link_agentbot
  log_info "Agentbot install complete"
  return "$rc"
}

run_update_decision() {
  if [[ "${AGENTBOT_UPDATE_INTERACTIVE:-0}" == 1 ]]; then
    run_update_prompt "$1"
    return $?
  fi
  case "${AGENTBOT_UPDATE_CONFIRM:-no}" in
    1|true|yes|y) return 0 ;;
    *) return 1 ;;
  esac
}

print_repo_update_table() {
  local branch local_rev available action bold='' reset='' yellow='' orange=''
  if [[ -z "${NO_COLOR:-}" && ( -t 1 || -t 0 || -n "${AGENTBOT_TUI:-}" || -n "${FORCE_COLOR:-}" ) ]]; then
    bold=$'\033[1m'; reset=$'\033[0m'; yellow=$'\033[33m'; orange=$'\033[38;5;208m'
  fi
  branch="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
  local_rev="$(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo unknown)"
  case "${REPO_UPDATE_STATE:-stopped}" in
    behind) available="${REPO_UPDATE_BEHIND:-0} commit(s) behind"; action='pull --ff-only' ;;
    ahead) available="${REPO_UPDATE_AHEAD:-0} local commit(s) ahead"; action='continue' ;;
    *) available='repository state requires review'; action='check' ;;
  esac
  printf '\n  %s%sRepository update%s\n' "$bold" "$orange" "$reset"
  printf '  %s%-22s | %-40s | %s%s\n' "$bold" component detail result "$reset"
  printf '  %s\n' '-----------------------+------------------------------------------+----------'
  printf '  %-22s | %-40s | %s%s%s\n' 'agent_bootstrap repo' "${branch}@${local_rev} / ${available}" "$yellow" "$action" "$reset"
  printf '\n'
}

run_update_prompt() {
  local action="$1" prompt answer=''
  local tty_input="${AGENTBOT_UPDATE_TTY_INPUT:-/dev/tty}"
  local tty_output="${AGENTBOT_UPDATE_TTY_OUTPUT:-/dev/tty}"
  case "$action" in
    pull-behind) prompt='Pull the available repository commit(s) with --ff-only?' ;;
    continue-ahead) prompt='The local repository is ahead. Continue with the Agentbot update?' ;;
    *) return 1 ;;
  esac
  print_repo_update_table >"$tty_output"
  printf '%s [y/N]: ' "$prompt" >>"$tty_output"
  IFS= read -r answer <"$tty_input" || true
  case "$answer" in
    y|Y|yes|YES) return 0 ;;
    *) return 1 ;;
  esac
}

run_update_backend() {
  run_update_backend_as update "$@"
}

run_update_backend_as() {
  local update_command="$1"
  shift
  local confirm=no dry_run=false arg update_outcome update_reason
  for arg in "$@"; do
    case "$arg" in
      --yes) confirm=yes ;;
      --dry-run) dry_run=true ;;
      *) die "unknown update option: $arg" ;;
    esac
  done
  [[ "$confirm" == yes ]] && export AGENTBOT_UPDATE_CONFIRM=yes

  if ! declare -F repo_update_run >/dev/null; then
    # shellcheck source=scripts/lib/repo_update.sh
    source "$REPO_ROOT/scripts/lib/repo_update.sh"
  fi
  repo_update_run "$REPO_ROOT" run_update_decision update_outcome update_reason
  case "$update_outcome" in
    relaunch-required)
      info 'repository pulled; restart Agentbot from the updated checkout.'
      return 2
      ;;
    stopped)
      if [[ "$update_reason" == dirty ]]; then
        warn 'repository update stopped: dirty worktree; review, commit, discard, or otherwise resolve local changes before updating.'
      else
        warn "repository update stopped: $update_reason"
      fi
      return 1
      ;;
  esac
  if [[ "$dry_run" == true || "${AGENTBOT_UPDATE_SHOW_STATUS:-1}" == 1 ]]; then
    run_cli status
  fi
  github_token_child run_cli "$update_command" "$@"
}

usage() {
  cat <<EOF
Usage: ./install.sh <command> [args]

  Commands:
  install                Install Agentbot: skills, Graphify sync, outputs, doctor, link
  skills install         Install curated upstream skills from skills.sources.yaml
  skills update|upgrade  Refresh global skills from ~/.agents/.skill-lock.json
  skills list            List installed skills
  skills doctor          Validate skills installer prerequisites
  doctor                 Run slim doctor (skills + global baseline)
  update|upgrade [--dry-run] [--yes]
                         Repo-first skill reconciliation update/upgrade
  status [--json]        Show skills and global render status
  global                 Render global agent outputs
  workspace [--profile NAME] [--targets LIST] [--yes] PATH
                         Preview or render one workspace
  workspaces [--paths0 | --remove PATH]
                         List paths or stop managing one without changing its files
  resync [--all | PATH ...] [--yes | --dry-run]
                         Preview or refresh registered workspaces
  graphify status|setup  Inspect or set up the optional Graphify Agent Skills integration
  help                   Show this help

Run agentbot boot in a repository to create/preserve AGENTS.md and selected outputs.
With no arguments a usable controlling TTY is required for the Agentbot menu.

Archived commands (see archive/docs/README.md): all, interactive, import-local,
remove-managed, delete-local.

Legacy flags (backward compatible):
  --status, --global
EOF
}

main() {
  cd "$REPO_ROOT"

  # This must happen in main: `set --` inside a helper only changes that
  # helper's positional parameters, which broke the advertised legacy flags.
  case "${1:-}" in
    --status) set -- status "${@:2}" ;;
    --global) set -- global "${@:2}" ;;
    --workspace|--all)
      die "workspace/all render is archived — see archive/docs/README.md"
      ;;
  esac

  local cmd="${1:-}"

  case "$cmd" in
    "")
      "$AGENTBOT_HOME/bin/agentbot"
      ;;
    install)
      run_install
      ;;
    update|upgrade)
      check_deps
      run_update_backend_as "$cmd" "${@:2}"
      ;;
    skills)
      check_deps
      if [[ $# -lt 2 ]]; then
        die "usage: ./install.sh skills <install|update|upgrade|list|doctor>"
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
    workspace|workspaces|resync)
      run_cli "$cmd" "${@:2}"
      ;;
    graphify)
      run_cli graphify "${@:2}"
      ;;
    all|interactive|import-local|remove-managed|delete-local)
      die "${cmd} is archived — see archive/docs/README.md"
      ;;
    -h|--help|help)
      usage
      ;;
    *)
      die "unknown command: ${cmd} (run ./install.sh --help)"
      ;;
  esac
}

if [[ "${AGENTBOT_SOURCE_ONLY:-0}" != 1 ]]; then
  main "$@"
fi
