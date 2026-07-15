#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/tests/lib/test_harness.sh"
test_harness_setup "$ROOT"

passed=0 failed=0
pass() { printf 'PASS: %s\n' "$1"; passed=$((passed + 1)); }
fail() { printf 'FAIL: %s\n' "$1" >&2; failed=$((failed + 1)); }
expect() { local name="$1"; shift; if "$@"; then pass "$name"; else fail "$name"; fi; }

install_git_scenario_fake() {
  cat >"$TEST_FAKE_BIN/git" <<'FAKE'
#!/usr/bin/env bash
set -u
source "${TEST_HARNESS_LIB:?}"
_harness_append_sanitized "$TEST_COMMAND_LOG" git "$@"
args=("$@")
if [[ "${args[0]:-}" == -C ]]; then args=("${args[@]:2}"); fi
cmd="${args[*]}" scenario="${REPO_SCENARIO:-current}"
case "$cmd" in
  'rev-parse --is-inside-work-tree') [[ "$scenario" == invalid-repository ]] && { printf 'false\n'; exit 0; }; printf 'true\n' ;;
  'rev-parse --is-bare-repository') printf 'false\n' ;;
  'remote get-url origin')
    case "$scenario" in
      invalid-origin) printf 'https://github.com/other/repo.git\n' ;;
      token-origin) printf 'https://credential@github.com/PamuduW/agent_bootstrap.git\n' ;;
      absent-origin) exit 2 ;;
      *) printf 'https://github.com/PamuduW/agent_bootstrap.git\n' ;;
    esac ;;
  'rev-parse --abbrev-ref --symbolic-full-name @{upstream}') [[ "$scenario" == no-upstream ]] && exit 1; printf 'origin/main\n' ;;
  'fetch --prune') [[ "$scenario" == fetch-failed ]] && exit 29; : ;;
  'status --porcelain') [[ "$scenario" == status-failed ]] && exit 43; [[ "$scenario" == dirty ]] && printf '?? local-change\n'; : ;;
  'symbolic-ref --quiet --short HEAD') [[ "$scenario" == detached ]] && exit 1; printf 'main\n' ;;
  'rev-list --left-right --count HEAD...@{upstream}')
    case "$scenario" in
      ahead) printf '2\t0\n' ;; behind|pull-failed) printf '0\t3\n' ;; diverged) printf '2\t3\n' ;;
      invalid-counts) printf 'not-counts\n' ;; *) printf '0\t0\n' ;;
    esac ;;
  'pull --ff-only') [[ "$scenario" == pull-failed ]] && exit 31; : ;;
  *) printf 'unconfigured fake Git operation: %s\n' "$cmd" >&2; exit 97 ;;
esac
FAKE
  chmod 700 "$TEST_FAKE_BIN/git"
}

decision() {
  printf '%s\n' "$1" >>"$TEST_ROOT/decisions.log"
  [[ "${DECISION_APPROVE:-no}" == yes ]]
}

reset_case() {
  : >"$TEST_COMMAND_LOG"; : >"$TEST_URL_LOG"; : >"$TEST_SIBLING_LOG"; : >"$TEST_RELAUNCH_LOG"; : >"$TEST_ROOT/decisions.log"
  REPO_SCENARIO="$1" DECISION_APPROVE="${2:-no}"
  export REPO_SCENARIO DECISION_APPROVE
  OUTCOME=unset REASON=unset
}

run_case() { reset_case "$1" "${2:-no}"; repo_update_run "$TEST_ROOT/repo" decision OUTCOME REASON >/dev/null 2>&1; }
pull_count() { grep -c $'git\t-C\t.*\tpull\t--ff-only$' "$TEST_COMMAND_LOG" 2>/dev/null || true; }
decision_count() { wc -l <"$TEST_ROOT/decisions.log"; }

test_current() { run_case current; [[ "$OUTCOME/$REASON" == current/current && "$(decision_count)" -eq 0 && "$(pull_count)" -eq 0 ]]; }
test_dirty() { run_case dirty; [[ "$OUTCOME/$REASON" == stopped/dirty && "$(pull_count)" -eq 0 ]]; }
test_detached() { run_case detached; [[ "$OUTCOME/$REASON" == stopped/detached && "$(pull_count)" -eq 0 ]]; }
test_no_upstream() { run_case no-upstream; [[ "$OUTCOME/$REASON" == stopped/no-upstream ]] && ! grep -q $'\tfetch\t--prune$' "$TEST_COMMAND_LOG"; }
test_ahead_approved() { run_case ahead yes; [[ "$OUTCOME/$REASON" == ahead-approved/ahead && "$(pull_count)" -eq 0 ]] && grep -Fqx continue-ahead "$TEST_ROOT/decisions.log"; }
test_ahead_declined() { run_case ahead no; [[ "$OUTCOME/$REASON" == stopped/ahead-declined && "$(pull_count)" -eq 0 ]]; }
test_behind_declined() { run_case behind no; [[ "$OUTCOME/$REASON" == stopped/behind-declined && "$(pull_count)" -eq 0 ]] && grep -Fqx pull-behind "$TEST_ROOT/decisions.log"; }
test_behind_pulled() { run_case behind yes; [[ "$OUTCOME/$REASON" == relaunch-required/pulled && "$(pull_count)" -eq 1 ]]; }
test_pull_failed() { run_case pull-failed yes; [[ "$OUTCOME/$REASON" == stopped/pull-failed && "$(pull_count)" -eq 1 ]]; }
test_diverged() { run_case diverged yes; [[ "$OUTCOME/$REASON" == stopped/diverged && "$(decision_count)" -eq 0 && "$(pull_count)" -eq 0 ]]; }
test_fetch_failed() { run_case fetch-failed yes; [[ "$OUTCOME/$REASON" == stopped/fetch-failed ]] && ! grep -q $'\tstatus\t--porcelain$' "$TEST_COMMAND_LOG"; }
test_invalid_counts() { run_case invalid-counts yes; [[ "$OUTCOME/$REASON" == stopped/invalid-counts && "$(pull_count)" -eq 0 ]]; }

test_invalid_repo_and_origin() {
  local scenario
  for scenario in invalid-repository invalid-origin token-origin absent-origin; do
    run_case "$scenario" yes
    case "$scenario" in invalid-repository) [[ "$REASON" == invalid-repository ]] ;; *) [[ "$REASON" == invalid-origin ]] ;; esac || return 1
    ! grep -q $'\tfetch\t--prune$' "$TEST_COMMAND_LOG" || return 1
  done
}

test_classify_output_parameter_table() {
  local scenario expected_state expected_reason actual_state actual_reason rc
  while read -r scenario expected_state expected_reason; do
    reset_case "$scenario"
    actual_state=unset actual_reason=unset
    repo_update_classify "$TEST_ROOT/repo" actual_state actual_reason
    rc=$?
    [[ "$rc" -eq 0 && "$actual_state" == "$expected_state" && "$actual_reason" == "$expected_reason" ]] || return 1
  done <<'TABLE'
current current current
dirty dirty dirty
detached detached detached
no-upstream no-upstream no-upstream
ahead ahead ahead
behind behind behind
diverged diverged diverged
invalid-counts stopped invalid-counts
TABLE
}

test_classify_status_failure_is_machine_stopped() {
  local actual_state=unset actual_reason=unset rc
  reset_case status-failed
  repo_update_classify "$TEST_ROOT/repo" actual_state actual_reason
  rc=$?
  [[ "$rc" -eq 0 && "$actual_state/$actual_reason" == stopped/invalid-counts ]]
}

test_git_ordering() {
  run_case behind yes
  local log="$TEST_COMMAND_LOG"
  awk -F '\t' '
    /rev-parse.*--is-inside-work-tree/ {work=NR}
    /remote.*get-url.*origin/ {origin=NR}
    /rev-parse.*symbolic-full-name.*upstream/ && !upstream {upstream=NR}
    /fetch.*--prune/ {fetch=NR}
    /status.*--porcelain/ {status=NR}
    /symbolic-ref.*--quiet.*--short.*HEAD/ {branch=NR}
    /rev-list.*--left-right.*--count/ {counts=NR}
    /pull.*--ff-only/ {pull=NR}
    END { exit !(work<origin && origin<upstream && upstream<fetch && fetch<status && status<branch && branch<counts && counts<pull) }
  ' "$log"
}

test_pull_only_complete_table() {
  local scenario approve expected
  while read -r scenario approve expected; do
    run_case "$scenario" "$approve"
    [[ "$(pull_count)" -eq "$expected" ]] || return 1
  done <<'TABLE'
current no 0
dirty yes 0
detached yes 0
no-upstream yes 0
ahead yes 0
behind no 0
behind yes 1
diverged yes 0
fetch-failed yes 0
invalid-counts yes 0
TABLE
}

test_success_returns_at_pull_boundary() (
  run_case behind yes
  [[ "$OUTCOME/$REASON" == relaunch-required/pulled ]] || return 1
  [[ "$(tail -n 1 "$TEST_COMMAND_LOG")" == *$'\tpull\t--ff-only' ]] || return 1
  [[ ! -s "$TEST_RELAUNCH_LOG" && ! -s "$TEST_SIBLING_LOG" && ! -s "$TEST_URL_LOG" ]]
)

test_relaunch_adapter() (
  reset_case current
  HARNESS_RELAUNCH_EXIT=41
  export HARNESS_RELAUNCH_EXIT
  set +e
  SETUP_CALLER=dotfiles repo_update_invoke_relaunch harness_relaunch "$TEST_ROOT/bin/agentbot" update --dry-run
  rc=$?
  set -e
  [[ "$rc" -eq 41 ]] && assert_relaunch_call dotfiles "$TEST_ROOT/bin/agentbot" update --dry-run
)

test_safety_and_scope() {
  [[ "$(command -v git)" == "$TEST_FAKE_BIN/git" && ! -e "$TEST_FAKE_BIN/exec" ]] || return 1
  [[ ! -s "$TEST_URL_LOG" && ! -s "$TEST_SIBLING_LOG" ]] || return 1
  ! grep -Eq 'apt|curl|npx|skills|reconcile|doctor|install|render|exec[[:space:]]' "$ROOT/scripts/lib/repo_update.sh"
}

install_git_scenario_fake
mkdir -p "$TEST_ROOT/repo"
[[ -f "$ROOT/scripts/lib/repo_update.sh" ]] && source "$ROOT/scripts/lib/repo_update.sh"
declare -F repo_update_run >/dev/null || repo_update_run() { printf -v "$3" stopped; printf -v "$4" missing; return 1; }
declare -F repo_update_invoke_relaunch >/dev/null || repo_update_invoke_relaunch() { return 1; }

expect 'current returns current without decision or pull' test_current
expect 'dirty stops without pull' test_dirty
expect 'detached stops without pull' test_detached
expect 'missing upstream stops before fetch' test_no_upstream
expect 'ahead approval continues without pull' test_ahead_approved
expect 'ahead decline stops without pull' test_ahead_declined
expect 'behind decline stops without pull' test_behind_declined
expect 'behind approval pulls ff-only once and requires relaunch' test_behind_pulled
expect 'failed confirmed pull stops with pull-failed' test_pull_failed
expect 'diverged stops without decision or pull' test_diverged
expect 'fetch failure stops before classification' test_fetch_failed
expect 'malformed counts stop with invalid-counts' test_invalid_counts
expect 'invalid repository and origin stop before fetch' test_invalid_repo_and_origin
expect 'classifier writes exact state and reason output parameters for every state' test_classify_output_parameter_table
expect 'classifier converts failed status probe to machine-stopped invalid-counts' test_classify_status_failure_is_machine_stopped
expect 'Git sequence is validate origin upstream fetch classify pull' test_git_ordering
expect 'only clean confirmed behind state pulls across full table' test_pull_only_complete_table
expect 'successful pull returns at adapter boundary without relaunch or extra commands' test_success_returns_at_pull_boundary
expect 'relaunch adapter preserves argv caller context and status' test_relaunch_adapter
expect 'harness prevents exec network skills home and repository mutation' test_safety_and_scope

test_harness_verify_safety || failed=$((failed + 1))
printf '\nRan %d repo-update test(s); %d failure(s).\n' "$((passed + failed))" "$failed"
test_harness_cleanup || failed=$((failed + 1))
((failed == 0))
