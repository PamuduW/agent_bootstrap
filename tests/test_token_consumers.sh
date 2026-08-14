#!/usr/bin/env bash
# shellcheck disable=SC1091  # Owned entrypoints are intentionally sourced in isolated subshell tests.
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=tests/lib/test_harness.sh
source "$ROOT/tests/lib/test_harness.sh"
test_harness_setup "$ROOT"

passed=0
failed=0
seq=0
pass() { printf 'PASS: %s\n' "$1"; passed=$((passed + 1)); }
fail() { printf 'FAIL: %s\n' "$1" >&2; failed=$((failed + 1)); }
expect() { local name="$1"; shift; if "$@"; then pass "$name"; else fail "$name"; fi; }

token() {
  seq=$((seq + 1))
  printf '%s_%s_%024d' "${1:-consumer}" "$(date +%s%N)" "$seq"
}

active_file() { printf '%s\n' "$XDG_CONFIG_HOME/agentbot/github.env"; }
legacy_file() { printf '%s\n' "$XDG_CONFIG_HOME/agent_bootstrap/github.env"; }

write_token_file() {
  local file="$1" value="$2" mode="${3:-600}"
  mkdir -p "$(dirname "$file")"
  chmod 700 "$(dirname "$file")"
  printf 'GITHUB_TOKEN=%s\n' "$value" >"$file"
  chmod "$mode" "$file"
}

reset_state() {
  rm -rf "$XDG_CONFIG_HOME/agentbot" "$XDG_CONFIG_HOME/agent_bootstrap"
  unset GITHUB_TOKEN AGENTBOT_QUIET AGENTBOT_TUI
  unset TEST_CHILD_PID_FILE TEST_CHILD_RELEASE_FILE TEST_NPX_EXIT TEST_PYTHON_EXIT
  : >"$TEST_COMMAND_LOG"
  : >"$TEST_URL_LOG"
  : >"$TEST_SIBLING_LOG"
  : >"$TEST_RELAUNCH_LOG"
  : >"$TEST_ROOT/child-env.log"
}

install_child_fakes() {
  TEST_REAL_PYTHON3="$(command -v python3)"
  export TEST_REAL_PYTHON3
  cat >"$TEST_FAKE_BIN/npx" <<'FAKE'
#!/usr/bin/env bash
set -u
valid=no
source_kind=none
if [[ "${GITHUB_TOKEN:-}" =~ ^[A-Za-z0-9_]{20,}$ ]]; then valid=yes; fi
case "${GITHUB_TOKEN:-}" in
  envpreferred_*) source_kind=environment ;;
  saved_*) source_kind=saved ;;
esac
source "${TEST_HARNESS_LIB:?}"
_harness_append_sanitized "$TEST_COMMAND_LOG" npx "$@" "valid=$valid" "source=$source_kind"
printf 'npx\tvalid=%s\tsource=%s\n' "$valid" "$source_kind" >>"${TEST_ROOT:?}/child-env.log"
if [[ -n "${TEST_CHILD_PID_FILE:-}" ]]; then
  printf '%s\n' "$$" >"$TEST_CHILD_PID_FILE"
  while [[ ! -e "${TEST_CHILD_RELEASE_FILE:?}" ]]; do sleep 0.01; done
fi
printf '%s' "${FAKE_NPX_STDOUT:-}"
printf '%s' "${FAKE_NPX_STDERR:-}" >&2
exit "${TEST_NPX_EXIT:-${FAKE_NPX_EXIT:-0}}"
FAKE
  chmod 700 "$TEST_FAKE_BIN/npx"

  cat >"$TEST_FAKE_BIN/python3" <<'FAKE'
#!/usr/bin/env bash
set -u
if [[ "${1:-}" == '-c' ]]; then exit 0; fi
if [[ "${1:-}" == '-' ]]; then exec "${TEST_REAL_PYTHON3:?}" "$@"; fi
valid=no
source_kind=none
if [[ "${GITHUB_TOKEN:-}" =~ ^[A-Za-z0-9_]{20,}$ ]]; then valid=yes; fi
case "${GITHUB_TOKEN:-}" in
  envpreferred_*) source_kind=environment ;;
  saved_*) source_kind=saved ;;
esac
source "${TEST_HARNESS_LIB:?}"
_harness_append_sanitized "$TEST_COMMAND_LOG" python3 "$@" "valid=$valid" "source=$source_kind"
printf 'python3\tvalid=%s\tsource=%s\n' "$valid" "$source_kind" >>"${TEST_ROOT:?}/child-env.log"
exit "${TEST_PYTHON_EXIT:-0}"
FAKE
  chmod 700 "$TEST_FAKE_BIN/python3"
}

run_skills_script() {
  bash "$ROOT/bin/skills-install.sh" "$@"
}

run_install_script() {
  bash "$ROOT/install.sh" "$@"
}

test_sources_local_helper_only() {
  grep -Fq 'source "${REPO_ROOT}/scripts/lib/github_token.sh"' "$ROOT/install.sh" || return 1
  grep -Fq 'source "${BOOTSTRAP_DIR}/scripts/lib/github_token.sh"' "$ROOT/bin/skills-install.sh" || return 1
  ! grep -Eq 'source .*dotfiles|source .*/agent_bootstrap/github\.env' "$ROOT/install.sh" "$ROOT/bin/skills-install.sh"
}

test_saved_add_normal_and_quiet() (
  reset_state
  write_token_file "$(active_file)" "$(token saved)"
  run_skills_script install >/dev/null || return 1
  [[ -z "${GITHUB_TOKEN:-}" ]] || return 1
  grep -q $'^npx\tskills\tadd\t.*\tvalid=yes\tsource=saved$' "$TEST_COMMAND_LOG" || return 1
  ! grep -q $'^npx\tskills\tadd\t.*\tvalid=no' "$TEST_COMMAND_LOG" || return 1
  reset_state
  write_token_file "$(active_file)" "$(token saved)"
  AGENTBOT_QUIET=1 run_skills_script install >"$TEST_ROOT/quiet.out" 2>"$TEST_ROOT/quiet.err" || return 1
  grep -q $'^npx\tskills\tadd\t.*\tvalid=yes\tsource=saved$' "$TEST_COMMAND_LOG" || return 1
  [[ ! -s "$TEST_ROOT/quiet.err" ]]
)

test_saved_update_probe_normal_and_quiet() (
  reset_state
  write_token_file "$(active_file)" "$(token saved)"
  run_skills_script update >/dev/null || return 1
  grep -Fqx $'npx\tskills\tupdate\t--help\tvalid=yes\tsource=saved' "$TEST_COMMAND_LOG" || return 1
  grep -Fqx $'npx\tskills\tupdate\t-g\t-y\tvalid=yes\tsource=saved' "$TEST_COMMAND_LOG" || return 1
  reset_state
  write_token_file "$(active_file)" "$(token saved)"
  AGENTBOT_TUI=1 run_skills_script update >"$TEST_ROOT/update-quiet.out" 2>"$TEST_ROOT/update-quiet.err" || return 1
  grep -Fqx $'npx\tskills\tupdate\t--help\tvalid=yes\tsource=saved' "$TEST_COMMAND_LOG" || return 1
  grep -Fqx $'npx\tskills\tupdate\t-g\t-y\tvalid=yes\tsource=saved' "$TEST_COMMAND_LOG"
)

test_npx_argv_contract() (
  reset_state
  run_skills_script install >/dev/null || return 1
  grep -q $'^npx\tskills\tadd\t[^\t]*\t--full-depth\t--skill\t.*\t-a\tcursor\t-a\tcodex\t-a\tclaude-code\t-a\tgithub-copilot\t-g\t-y\tvalid=no\tsource=none$' "$TEST_COMMAND_LOG" || return 1
  reset_state
  run_skills_script update >/dev/null || return 1
  grep -Fqx $'npx\tskills\tupdate\t--help\tvalid=no\tsource=none' "$TEST_COMMAND_LOG" || return 1
  grep -Fqx $'npx\tskills\tupdate\t-g\t-y\tvalid=no\tsource=none' "$TEST_COMMAND_LOG"
)

test_python_skills_children() (
  reset_state
  write_token_file "$(active_file)" "$(token saved)"
  run_install_script skills install >/dev/null || return 1
  grep -q $'^python3\t-m\tsrc\.cli\t--root\t[^\t]*\tstatus\tvalid=no\tsource=none$' "$TEST_COMMAND_LOG" || return 1
  grep -q $'^python3\t-m\tsrc\.cli\t--root\t[^\t]*\tskills\tinstall\tvalid=yes\tsource=saved$' "$TEST_COMMAND_LOG" || return 1
  [[ -z "${GITHUB_TOKEN:-}" ]] || return 1
  reset_state
  write_token_file "$(active_file)" "$(token saved)"
  run_install_script skills update >/dev/null || return 1
  grep -q $'^python3\t-m\tsrc\.cli\t--root\t[^\t]*\tskills\tupdate\tvalid=yes\tsource=saved$' "$TEST_COMMAND_LOG"
)

test_python_repo_update_child() (
  reset_state
  write_token_file "$(active_file)" "$(token saved)"
  AGENTBOT_SOURCE_ONLY=1 source "$ROOT/install.sh"
  check_deps() { :; }
  repo_update_run() {
    printf -v "$3" '%s' current
    printf -v "$4" '%s' current
  }
  run_update_backend --dry-run >/dev/null || return 1
  grep -q $'^python3\t-m\tsrc\.cli\t--root\t[^\t]*\tstatus\tvalid=no\tsource=none$' "$TEST_COMMAND_LOG" || return 1
  grep -q $'^python3\t-m\tsrc\.cli\t--root\t[^\t]*\tupdate\t--dry-run\tvalid=yes\tsource=saved$' "$TEST_COMMAND_LOG" || return 1
  reset_state
  write_token_file "$(active_file)" "$(token saved)"
  run_update_backend_as upgrade --dry-run >/dev/null || return 1
  grep -q $'^python3\t-m\tsrc\.cli\t--root\t[^\t]*\tupgrade\t--dry-run\tvalid=yes\tsource=saved$' "$TEST_COMMAND_LOG"
)

assert_readonly_skills_subcommand_unwrapped() {
  local subcmd="$1" err
  err="$TEST_ROOT/${subcmd}.err"
  reset_state
  write_token_file "$(active_file)" "saved_$(token saved)"
  run_install_script skills "$subcmd" >/dev/null 2>"$err" || return 1
  grep -q "^python3"$'\t-m\tsrc\.cli\t--root\t[^\t]*\tskills\t'"${subcmd}"$'\tvalid=no\tsource=none$' "$TEST_COMMAND_LOG" || return 1
  [[ ! -s "$err" ]] || return 1

  reset_state
  write_token_file "$(active_file)" "saved_$(token saved)" 644
  run_install_script skills "$subcmd" >/dev/null 2>"$err" || return 1
  [[ ! -s "$err" ]] || return 1
  grep -q "^python3"$'\t-m\tsrc\.cli\t--root\t[^\t]*\tskills\t'"${subcmd}"$'\tvalid=no\tsource=none$' "$TEST_COMMAND_LOG" || return 1

  reset_state
  write_token_file "$(legacy_file)" "saved_$(token legacy)"
  run_install_script skills "$subcmd" >/dev/null 2>"$err" || return 1
  [[ -e "$(legacy_file)" && ! -e "$(active_file)" && ! -s "$err" ]] || return 1
  grep -q "^python3"$'\t-m\tsrc\.cli\t--root\t[^\t]*\tskills\t'"${subcmd}"$'\tvalid=no\tsource=none$' "$TEST_COMMAND_LOG"
}

test_python_skills_list_unwrapped() (
  assert_readonly_skills_subcommand_unwrapped list
)

test_python_skills_doctor_unwrapped() (
  assert_readonly_skills_subcommand_unwrapped doctor
)

test_python_install_backend_child() (
  reset_state
  write_token_file "$(active_file)" "$(token saved)"
  mkdir -p "$HOME/bin"
  run_install_script install >/dev/null || return 1
  grep -q $'^python3\t-m\tsrc\.cli\t--root\t[^\t]*\tbootstrap\tvalid=yes\tsource=saved$' "$TEST_COMMAND_LOG" || return 1
  ! grep -q $'\tbootstrap\t.*\tGITHUB_TOKEN=' "$TEST_COMMAND_LOG"
)

test_environment_precedence() (
  reset_state
  write_token_file "$(active_file)" "$(token saved)"
  GITHUB_TOKEN="envpreferred_$(token parent)"
  export GITHUB_TOKEN
  run_skills_script update >/dev/null || return 1
  grep -Fqx $'npx\tvalid=yes\tsource=environment' "$TEST_ROOT/child-env.log" || return 1
  [[ "$GITHUB_TOKEN" == envpreferred_* ]]
)

test_missing_state_anonymous_silent() (
  reset_state
  run_skills_script update >"$TEST_ROOT/missing.out" 2>"$TEST_ROOT/missing.err" || return 1
  grep -Fqx $'npx\tvalid=no\tsource=none' "$TEST_ROOT/child-env.log" || return 1
  [[ ! -s "$TEST_ROOT/missing.err" ]]
)

test_invalid_states_warn_and_run_anonymous() (
  local state err="$TEST_ROOT/invalid.err"
  for state in malformed wrong-mode unsafe; do
    reset_state
    case "$state" in
      malformed)
        mkdir -p "$(dirname "$(active_file)")"; chmod 700 "$(dirname "$(active_file)")"
        printf 'OTHER=value\n' >"$(active_file)"; chmod 600 "$(active_file)"
        ;;
      wrong-mode) write_token_file "$(active_file)" "$(token saved)" 644 ;;
      unsafe) mkdir -p "$(dirname "$(active_file)")"; chmod 755 "$(dirname "$(active_file)")"; printf 'GITHUB_TOKEN=invalid\n' >"$(active_file)" ;;
    esac
    run_skills_script update >/dev/null 2>"$err" || return 1
    grep -q '^Warning: .*continuing anonymously\.$' "$err" || return 1
    ! grep -q $'\tvalid=yes\t' "$TEST_COMMAND_LOG" || return 1
    grep -q $'\tvalid=no\tsource=none$' "$TEST_COMMAND_LOG" || return 1
  done
)

test_child_status_propagates() (
  reset_state
  TEST_NPX_EXIT=37
  export TEST_NPX_EXIT
  set +e
  run_skills_script install >/dev/null 2>&1
  rc=$?
  set -e
  [[ "$rc" -eq 37 ]]
)

test_parent_never_gains_saved_token() (
  reset_state
  write_token_file "$(active_file)" "$(token saved)"
  set -- help
  source "$ROOT/bin/skills-install.sh" >/dev/null
  github_token_child bash -c '[[ -n "${GITHUB_TOKEN:-}" ]]' || return 1
  [[ -z "${GITHUB_TOKEN:-}" ]]
)

test_canary_and_proc_safety() (
  reset_state
  local canary pid='' job cmdline output="$TEST_ROOT/canary.out"
  canary="saved_$(token canary)"
  export TEST_CANARY_SECRET="$canary"
  write_token_file "$(active_file)" "$canary"
  TEST_CHILD_PID_FILE="$TEST_ROOT/npx.pid"
  TEST_CHILD_RELEASE_FILE="$TEST_ROOT/npx.release"
  export TEST_CHILD_PID_FILE TEST_CHILD_RELEASE_FILE
  run_skills_script update >"$output" 2>&1 &
  job=$!
  for _ in {1..200}; do
    [[ -s "$TEST_CHILD_PID_FILE" ]] && { pid="$(<"$TEST_CHILD_PID_FILE")"; break; }
    sleep 0.01
  done
  [[ -n "$pid" && -r "/proc/$pid/cmdline" ]] || { touch "$TEST_CHILD_RELEASE_FILE"; wait "$job"; return 1; }
  cmdline="$(tr '\0' ' ' <"/proc/$pid/cmdline")"
  touch "$TEST_CHILD_RELEASE_FILE"
  wait "$job" || return 1
  [[ "$cmdline" != *"$canary"* && "$cmdline" != *'GITHUB_TOKEN='* ]] || return 1
  ! grep -FRq -- "$canary" "$output" "$TEST_COMMAND_LOG" "$TEST_URL_LOG" "$TEST_SIBLING_LOG" "$TEST_RELAUNCH_LOG" || return 1
  ! "$TEST_REAL_GIT" -C "$ROOT" diff --no-ext-diff | grep -Fq -- "$canary"
)

test_no_token_bearing_arguments() {
  ! grep -En -- '(-H|--header)[[:space:]].*Authorization|https?://[^/[:space:]]*@|GITHUB_TOKEN=.*(run_cli|npx)' "$ROOT/install.sh" "$ROOT/bin/skills-install.sh"
}

test_sole_migration_owner() {
  local matches
  matches="$(grep -RIl --exclude=github_token.sh 'agent_bootstrap/github.env' "$ROOT/install.sh" "$ROOT/bin" "$ROOT/scripts" 2>/dev/null || true)"
  [[ -z "$matches" ]] || return 1
  ! grep -Eq 'github_token_(migrate_legacy|read|write)' "$ROOT/install.sh" "$ROOT/bin/skills-install.sh"
}

install_child_fakes
expect 'entrypoints source only the local Task 07 helper' test_sources_local_helper_only
expect 'saved token reaches normal and quiet npx add children only' test_saved_add_normal_and_quiet
expect 'saved token reaches update probe and normal and quiet update children' test_saved_update_probe_normal_and_quiet
expect 'npx add and update argv contract remains unchanged' test_npx_argv_contract
expect 'install.sh skills install and update authenticate only Python children' test_python_skills_children
expect 'install.sh repo update authenticates only the Python update child' test_python_repo_update_child
expect 'install.sh skills list neither authenticates warns nor migrates' test_python_skills_list_unwrapped
expect 'install.sh skills doctor neither authenticates warns nor migrates' test_python_skills_doctor_unwrapped
expect 'explicit install authenticates the internal Python bootstrap child' test_python_install_backend_child
expect 'valid environment token takes precedence over saved state' test_environment_precedence
expect 'missing saved state remains silent and anonymous' test_missing_state_anonymous_silent
expect 'malformed wrong-mode and unsafe state warn then run anonymously' test_invalid_states_warn_and_run_anonymous
expect 'child nonzero status propagates unchanged' test_child_status_propagates
expect 'saved token never remains in the calling shell' test_parent_never_gains_saved_token
expect 'canary is absent from output logs diff and sampled process cmdline' test_canary_and_proc_safety
expect 'owned entrypoints contain no token-bearing argument construction' test_no_token_bearing_arguments
expect 'Task 07 helper remains the sole migration and legacy-path owner' test_sole_migration_owner

test_harness_verify_safety || failed=$((failed + 1))
printf '\nRan %d consumer test(s); %d failure(s).\n' "$((passed + failed))" "$failed"
test_harness_cleanup || failed=$((failed + 1))
((failed == 0))
