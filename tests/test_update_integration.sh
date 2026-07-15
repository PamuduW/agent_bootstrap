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
    }
    run_update_backend --dry-run >/dev/null 2>&1
  }
  set +e
  run_update_backend_for stopped dirty; dirty_rc=$?
  run_update_backend_for relaunch-required pulled; pulled_rc=$?
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

test_dirty_state_has_manual_resolution_guidance() (
  AGENTBOT_SOURCE_ONLY=1 source "$ROOT/install.sh"
  run_update_decision() { return 1; }
  repo_update_run() {
    printf -v "$3" '%s' stopped
    printf -v "$4" '%s' dirty
  }
  local output rc
  set +e; output="$(run_update_backend --dry-run 2>&1)"; rc=$?; set -e
  [[ "$rc" -ne 0 && "$output" == *'review, commit, discard'* ]]
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
  [[ "$output" == *$'\033[1mRepository update\033[0m'* ]] || return 1
  [[ "$output" == *$'\033[33mcheck\033[0m'* ]]
)

check 'repo gate short-circuits stopped and relaunch states' test_repo_gate_short_circuits_unsafe_states
check 'dirty update stops with manual-resolution guidance' test_dirty_state_has_manual_resolution_guidance
check 'interactive update decisions use the TTY prompt seam' test_interactive_repo_decision_uses_tty_prompt_contract
check 'repository update table honors the Agentbot TUI color mode' test_repo_update_table_honors_tui_color_mode
check 'direct update shows the status table before reconciliation' test_direct_update_shows_status_before_reconciliation
test_harness_verify_safety || failed=$((failed + 1))
printf '\nRan %d update-integration test(s); %d failure(s).\n' "$((passed + failed))" "$failed"
test_harness_cleanup || failed=$((failed + 1))
((failed == 0))
