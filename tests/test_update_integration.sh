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
  [[ "$(<"$TEST_ROOT/calls")" == 'cli:update --dry-run' ]]
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

check 'repo gate short-circuits stopped and relaunch states' test_repo_gate_short_circuits_unsafe_states
check 'dirty update stops with manual-resolution guidance' test_dirty_state_has_manual_resolution_guidance
test_harness_verify_safety || failed=$((failed + 1))
printf '\nRan %d update-integration test(s); %d failure(s).\n' "$((passed + failed))" "$failed"
test_harness_cleanup || failed=$((failed + 1))
((failed == 0))
