#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=tests/lib/test_harness.sh
source "$ROOT/tests/lib/test_harness.sh"
test_harness_setup "$ROOT"
AGENTBOT_MENU_SOURCE_ONLY=1 source "$ROOT/scripts/menu.sh"
AGENTBOT_HOME="$ROOT"
export AGENTBOT_HOME

passed=0 failed=0
pass() { printf 'PASS: %s\n' "$1"; passed=$((passed + 1)); }
fail() { printf 'FAIL: %s\n' "$1" >&2; failed=$((failed + 1)); }
check() { local name="$1"; shift; if "$@"; then pass "$name"; else fail "$name"; fi; }

test_status_uses_one_diagnostics_snapshot() (
	local calls="$TEST_ROOT/status.calls"; : >"$calls"
	agentbot_run_backend() { printf '%s\n' "$*" >>"$calls"; }
	agentbot_menu_status
	[[ "$(<"$calls")" == 'status --doctor' ]]
)

test_main_dispatch_and_pause_ownership() (
	local calls="$TEST_ROOT/menu.calls"; : >"$calls"
	local index=0
	local -a choices=(status install update token workspaces libraries quit)
	menu_simple_run() { MENU_SIMPLE_RESULT="${choices[$index]}"; index=$((index + 1)); }
	tui_clear() { :; }; tui_pause() { printf 'pause\n' >>"$calls"; }
	agentbot_menu_status() { printf 'status\n' >>"$calls"; }
	agentbot_menu_install() { printf 'install\n' >>"$calls"; }
	agentbot_menu_update() { printf 'update\n' >>"$calls"; }
	agentbot_menu_token() { printf 'token\n' >>"$calls"; }
	agentbot_menu_workspaces() { printf 'workspaces\n' >>"$calls"; }
	agentbot_menu_libraries() { printf 'libraries\n' >>"$calls"; }
	agentbot_menu_loop
	[[ "$(<"$calls")" == $'status\npause\ninstall\npause\nupdate\npause\ntoken\nworkspaces\nlibraries' ]]
)

test_repository_change_exits_without_pause() (
	local calls="$TEST_ROOT/repository-change.calls"; : >"$calls"
	local index=0
	menu_simple_run() { ((index++ == 0)) || return 1; MENU_SIMPLE_RESULT=update; }
	tui_clear() { :; }; tui_pause() { printf 'pause\n' >>"$calls"; }
	agentbot_menu_dispatch() { AGENTBOT_MENU_QUIT=true; }
	agentbot_menu_loop
	[[ ! -s "$calls" ]]
)

test_command_lib_selects_one_detail() (
	local capture="$TEST_ROOT/command-lib.capture" output calls=0
	menu_simple_run() {
		calls=$((calls + 1))
		if ((calls == 1)); then
			printf '%s\n' "${MENU_SIMPLE_LABELS[*]}" >"$capture"
			MENU_SIMPLE_RESULT='boot'; return 0
		fi
		return 1
	}
	tui_clear() { :; }; tui_wait_back() { :; }
	output="$(AGENTBOT_MENU_COLS=80 agentbot_menu_command_lib)"
	[[ "$(<"$capture")" == *'status [read-only]'* ]] || return 1
	[[ "$(<"$capture")" == *'Bootstrap commands'* ]] || return 1
	[[ "$output" == *'Agentbot › Help › boot'* && "$output" == *'agentbot boot'* ]]
)

test_graphify_library_is_data_driven_and_supported() (
	local output step=0 fake_help
	menu_simple_run() {
		step=$((step + 1))
		case "$step" in
		1) MENU_SIMPLE_RESULT=assistant ;;
		2) MENU_SIMPLE_RESULT='/graphify query "what connects auth to the database?"' ;;
		3) return 1 ;;
		4) MENU_SIMPLE_RESULT=boundary ;;
		*) return 1 ;;
		esac
	}
	tui_clear() { :; }; tui_wait_back() { :; }
	output="$(AGENTBOT_MENU_COLS=100 agentbot_menu_graphify_lib)"
	[[ "$output" == *'/graphify query "what connects auth to the database?"'* ]] || return 1
	[[ "$output" == *'graphify install --platform agents'* ]] || return 1
	fake_help=$'Commands:\n  install [--platform P]\n  extract <path>\n  update <path>\n  cluster-only <path>\n  query "<question>"\n  path "A" "B"\n  explain "X"\n  export callflow-html\n  hook status\n  merge-graphs <g1> <g2>'
	agentbot_graphify_validate_rows "$fake_help"
)

test_token_entry_is_hidden_and_reveal_requires_confirmation() (
	local token='saved_token_value_1234567890' input="$TEST_ROOT/token.input" output="$TEST_ROOT/token.output"
	local reveal_input="$TEST_ROOT/reveal.input" reveal_output="$TEST_ROOT/reveal.output" fingerprint
	printf 's\n%s\ny\nq\n' "$token" >"$input"
	NO_COLOR=1; tui_init_colors
	AGENTBOT_TOKEN_TTY_INPUT="$input" AGENTBOT_TOKEN_TTY_OUTPUT="$output" agentbot_token_config_menu
	fingerprint="$(github_token_fingerprint "$token")"
	[[ "$(<"$output")" == *'Input is hidden; only its fingerprint will be shown.'* ]] || return 1
	[[ "$(<"$output")" == *"$fingerprint"* && "$(<"$output")" != *"$token"* ]] || return 1
	printf 'r\nn\nq\n' >"$reveal_input"
	unset NO_COLOR; tui_init_colors
	AGENTBOT_TOKEN_TTY_INPUT="$reveal_input" AGENTBOT_TOKEN_TTY_OUTPUT="$reveal_output" agentbot_token_config_menu
	[[ "$(<"$reveal_output")" == *$'\033[31mWARNING: the full token will be printed once on this terminal.\033[0m'* ]] || return 1
	[[ "$(<"$reveal_output")" != *"$token"* ]]
)

test_workspaces_routes_read_preview_and_apply() (
	local calls="$TEST_ROOT/workspaces.calls"; : >"$calls"
	local index=0
	local -a choices=(list preview apply back)
	menu_simple_run() {
		local choice="${choices[$index]}"; index=$((index + 1))
		[[ "$choice" != back ]] || return 1
		MENU_SIMPLE_RESULT="$choice"
	}
	tui_clear() { :; }; tui_pause() { printf 'pause\n' >>"$calls"; }
	agentbot_menu_workspaces_confirm() { return 0; }
	agentbot_run_backend() { printf 'backend:%s\n' "$*" >>"$calls"; }
	agentbot_menu_workspaces
	[[ "$(<"$calls")" == $'backend:workspaces\npause\nbackend:resync --all\npause\nbackend:resync --all --yes\npause' ]]
)

test_declined_workspace_apply_is_non_destructive() (
	local calls="$TEST_ROOT/workspace-decline.calls"; : >"$calls"
	agentbot_menu_workspaces_confirm() { return 1; }
	agentbot_run_backend() { printf 'backend:%s\n' "$*" >>"$calls"; }
	agentbot_menu_workspaces_dispatch apply >/dev/null
	[[ ! -s "$calls" ]]
)

test_failed_actions_are_red() (
	unset NO_COLOR; tui_init_colors
	agentbot_menu_status() { return 17; }
	local output rc
	set +e; output="$(agentbot_menu_dispatch status 2>&1)"; rc=$?; set -e
	[[ "$rc" -eq 17 && "$output" == *$'\033[31mAction failed (exit 17).\033[0m'* ]]
)

check 'Status uses one diagnostics snapshot' test_status_uses_one_diagnostics_snapshot
check 'main dispatch gives direct actions exactly one pause' test_main_dispatch_and_pause_ownership
check 'repository changes exit without a stale pause' test_repository_change_exits_without_pause
check 'Command Lib selects and renders one detail page' test_command_lib_selects_one_detail
check 'Graphify Lib rows match supported command families' test_graphify_library_is_data_driven_and_supported
check 'token entry is hidden and reveal is confirmed' test_token_entry_is_hidden_and_reveal_requires_confirmation
check 'Workspaces routes list preview and confirmed apply' test_workspaces_routes_read_preview_and_apply
check 'declined workspace apply performs no backend write' test_declined_workspace_apply_is_non_destructive
check 'failed menu actions use the shared red treatment' test_failed_actions_are_red

test_harness_verify_safety || failed=$((failed + 1))
printf '\nRan %d menu-action test(s); %d failure(s).\n' "$((passed + failed))" "$failed"
test_harness_cleanup || failed=$((failed + 1))
((failed == 0))
