#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/tests/lib/test_harness.sh"
test_harness_setup "$ROOT"

passed=0 failed=0
pass() { printf 'PASS: %s\n' "$1"; passed=$((passed + 1)); }
fail() { printf 'FAIL: %s\n' "$1" >&2; failed=$((failed + 1)); }
check() { local name="$1"; shift; if "$@"; then pass "$name"; else fail "$name"; fi; }

test_repo_gate_short_circuits_unsafe_states() (
  AGENTBOT_SOURCE_ONLY=1 source "$ROOT/install.sh"
  check_deps() { :; }
  run_cli() { printf 'cli:%s\n' "$*" >>"$TEST_ROOT/calls"; }
  : >"$TEST_ROOT/calls"
  run_update_backend_for() {
    local gate_outcome="$1" gate_reason="$2"
    repo_update_run() {
      printf -v "$3" '%s' "$gate_outcome"
      printf -v "$4" '%s' "$gate_reason"
      case "$gate_outcome" in
        stopped) return 1 ;;
        repository_changed) return 2 ;;
      esac
      return 0
    }
    run_update_backend --dry-run >/dev/null 2>&1
  }
  set +e
  run_update_backend_for stopped dirty; dirty_rc=$?
  run_update_backend_for repository_changed pulled; pulled_rc=$?
  run_update_backend_for current current; current_rc=$?
  set -e
  [[ "$dirty_rc" -ne 0 && "$pulled_rc" -eq 2 && "$current_rc" -eq 0 ]] || return 1
  [[ "$(<"$TEST_ROOT/calls")" == $'cli:status\ncli:update --dry-run' ]]
)

test_direct_update_shows_status_before_reconciliation() (
  AGENTBOT_SOURCE_ONLY=1 source "$ROOT/install.sh"
  check_deps() { :; }
  repo_update_run() {
    printf -v "$3" '%s' current
    printf -v "$4" '%s' current
  }
  run_cli() { printf 'cli:%s\n' "$*" >>"$TEST_ROOT/direct-update.calls"; }
  : >"$TEST_ROOT/direct-update.calls"
  run_update_backend --dry-run >/dev/null 2>&1 || return 1
  [[ "$(<"$TEST_ROOT/direct-update.calls")" == $'cli:status\ncli:update --dry-run' ]]
)

test_dirty_state_reports_changes_remote_history_and_blocks_backend() (
  AGENTBOT_SOURCE_ONLY=1 source "$ROOT/install.sh"
  local calls="$TEST_ROOT/dirty-update.calls"
  : >"$calls"
  run_cli() { printf 'cli:%s\n' "$*" >>"$calls"; }
  git() {
    case "$*" in
      *'rev-parse --abbrev-ref HEAD'*) printf 'main\n' ;;
      *'rev-parse --short HEAD'*) printf 'abc123\n' ;;
      *) return 1 ;;
    esac
  }
  repo_update_run() {
    REPO_UPDATE_STATE=behind
    REPO_UPDATE_AHEAD=0
    REPO_UPDATE_BEHIND=3
    REPO_UPDATE_DIRTY=1
    REPO_UPDATE_UPSTREAM=origin/main
    REPO_UPDATE_CHANGES=$' M scripts/example.sh\n?? .cursor/rules/agentbot-policy.mdc'
    printf -v "$3" '%s' stopped
    printf -v "$4" '%s' dirty
    return 1
  }
  local output rc
  set +e; output="$(run_update_backend --dry-run 2>&1)"; rc=$?; set -e
  [[ "$rc" -ne 0 ]] || return 1
  [[ "$output" == *'Repository update'* ]] || return 1
  [[ "$output" == *'2 local change(s)'* ]] || return 1
  [[ "$output" == *'origin/main'* && "$output" == *'3 commit(s) behind'* ]] || return 1
  [[ "$output" == *'blocked'* && "$output" == *'Local changes:'* ]] || return 1
  [[ "$output" == *' M scripts/example.sh'* ]] || return 1
  [[ "$output" == *'?? .cursor/rules/agentbot-policy.mdc'* ]] || return 1
  [[ "$output" == *'Repository pull and downstream updates stopped.'* ]] || return 1
  [[ ! -s "$calls" ]]
)

test_dirty_current_reports_verified_current_and_stops() (
  AGENTBOT_SOURCE_ONLY=1 source "$ROOT/install.sh"
  git() {
    case "$*" in
      *'rev-parse --abbrev-ref HEAD'*) printf 'main\n' ;;
      *'rev-parse --short HEAD'*) printf 'abc123\n' ;;
      *) return 1 ;;
    esac
  }
  repo_update_run() {
    REPO_UPDATE_STATE=current
    REPO_UPDATE_DIRTY=1
    REPO_UPDATE_UPSTREAM=origin/main
    REPO_UPDATE_CHANGES='?? local-file'
    printf -v "$3" '%s' stopped
    printf -v "$4" '%s' dirty
    return 1
  }
  local output rc
  set +e; output="$(run_update_backend --dry-run 2>&1)"; rc=$?; set -e
  [[ "$rc" -ne 0 && "$output" == *'origin/main'* && "$output" == *'current'* ]] || return 1
  [[ "$output" == *'?? local-file'* ]]
)

test_dirty_fetch_failure_reports_paths_and_unknown_freshness() (
  AGENTBOT_SOURCE_ONLY=1 source "$ROOT/install.sh"
  git() {
    case "$*" in
      *'rev-parse --abbrev-ref HEAD'*) printf 'main\n' ;;
      *'rev-parse --short HEAD'*) printf 'abc123\n' ;;
      *) return 1 ;;
    esac
  }
  repo_update_run() {
    REPO_UPDATE_STATE=stopped
    REPO_UPDATE_DIRTY=1
    REPO_UPDATE_UPSTREAM=origin/main
    REPO_UPDATE_CHANGES='?? local-file'
    printf -v "$3" '%s' stopped
    printf -v "$4" '%s' fetch-failed
    return 1
  }
  local output rc
  set +e; output="$(run_update_backend --dry-run 2>&1)"; rc=$?; set -e
  [[ "$rc" -ne 0 && "$output" == *'?? local-file'* ]] || return 1
  [[ "$output" == *'origin/main'* && "$output" == *'freshness unknown'* ]] || return 1
  [[ "$output" == *'Repository pull and downstream updates stopped.'* ]]
)

test_dirty_change_list_is_bounded_with_copyable_command() (
  AGENTBOT_SOURCE_ONLY=1 source "$ROOT/install.sh"
  local i output status_lines='' printed
  for i in $(seq 1 22); do status_lines+="?? path-${i}"$'\n'; done
  REPO_UPDATE_CHANGES="${status_lines%$'\n'}"
  output="$(print_repo_update_changes)"
  printed="$(grep -c '^  ?? path-' <<<"$output")"
  [[ "$printed" -eq 20 ]] || return 1
  [[ "$output" == *'... 2 more local change(s)'* ]] || return 1
  [[ "$output" == *'git -C '* && "$output" == *' status --short --untracked-files=all'* ]]
)

test_interactive_repo_decision_uses_tty_prompt_contract() (
  AGENTBOT_SOURCE_ONLY=1 source "$ROOT/install.sh"
  local prompted=''
  run_update_prompt() { prompted="$1"; [[ "${TEST_UPDATE_ANSWER:-no}" == yes ]]; }
  AGENTBOT_UPDATE_INTERACTIVE=1 TEST_UPDATE_ANSWER=yes
  export AGENTBOT_UPDATE_INTERACTIVE TEST_UPDATE_ANSWER
  run_update_decision pull-behind || return 1
  [[ "$prompted" == pull-behind ]]
)

test_repo_prompt_renders_after_table_on_the_tty_stream() (
  AGENTBOT_SOURCE_ONLY=1 source "$ROOT/install.sh"
  local tty_input="$TEST_ROOT/update-prompt.input"
  local tty_output="$TEST_ROOT/update-prompt.output"
  local captured_stdout="$TEST_ROOT/update-prompt.stdout"
  local table_line prompt_line
  printf 'y\n' >"$tty_input"
  : >"$tty_output"
  : >"$captured_stdout"
  git() {
    case "$*" in
      *'rev-parse --abbrev-ref HEAD'*) printf 'main\n' ;;
      *'rev-parse --short HEAD'*) printf 'abc123\n' ;;
      *) return 1 ;;
    esac
  }
  REPO_UPDATE_STATE=behind
  REPO_UPDATE_BEHIND=6
  REPO_UPDATE_DIRTY=0
  REPO_UPDATE_UPSTREAM=origin/main
  AGENTBOT_UPDATE_TTY_INPUT="$tty_input"
  AGENTBOT_UPDATE_TTY_OUTPUT="$tty_output"

  run_update_prompt pull-behind >"$captured_stdout" || return 1

  table_line="$(grep -n 'Repository update' "$tty_output" | cut -d: -f1)"
  prompt_line="$(grep -n 'Pull 6 commit(s) with --ff-only' "$tty_output" | cut -d: -f1)"
  [[ -n "$table_line" && -n "$prompt_line" && "$table_line" -lt "$prompt_line" ]] || return 1
  [[ ! -s "$captured_stdout" ]]
)

test_repo_update_table_honors_tui_color_mode() (
  AGENTBOT_SOURCE_ONLY=1 source "$ROOT/install.sh"
  local output
  git() {
    case "$*" in
      *'rev-parse --abbrev-ref HEAD'*) printf 'main\n' ;;
      *'rev-parse --short HEAD'*) printf 'abc123\n' ;;
      *) return 1 ;;
    esac
  }
  NO_COLOR='' AGENTBOT_TUI=1 output="$(print_repo_update_table)"
  [[ "$output" == *$'\033[1m\033[33mRepository update\033[0m'* ]] || return 1
  [[ "$output" != *$'\033[38;5;208mRepository update\033[0m'* ]] || return 1
  [[ "$output" == *$'\033[33mcheck\033[0m'* ]]
)

  check 'repo gate short-circuits stopped and changed-repository states' test_repo_gate_short_circuits_unsafe_states
check 'dirty update reports changes and remote history before blocking backend work' test_dirty_state_reports_changes_remote_history_and_blocks_backend
check 'dirty current repository reports verified current and stops' test_dirty_current_reports_verified_current_and_stops
check 'dirty fetch failure reports paths and unknown remote freshness' test_dirty_fetch_failure_reports_paths_and_unknown_freshness
check 'dirty change report caps paths and prints a copyable full-status command' test_dirty_change_list_is_bounded_with_copyable_command
check 'interactive update decisions use the TTY prompt seam' test_interactive_repo_decision_uses_tty_prompt_contract
check 'repository pull prompt renders below its table on the TTY stream' test_repo_prompt_renders_after_table_on_the_tty_stream
check 'repository update table honors the Agentbot TUI color mode' test_repo_update_table_honors_tui_color_mode
check 'direct update shows the status table before reconciliation' test_direct_update_shows_status_before_reconciliation
test_harness_verify_safety || failed=$((failed + 1))
printf '\nRan %d update-integration test(s); %d failure(s).\n' "$((passed + failed))" "$failed"
test_harness_cleanup || failed=$((failed + 1))
((failed == 0))
