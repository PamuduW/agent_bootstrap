#!/usr/bin/env bash
# shellcheck disable=SC2030,SC2031,SC2317
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/tests/lib/test_harness.sh"
test_harness_setup "$ROOT"

AGENTBOT_SOURCE_ONLY=1 source "$ROOT/bin/agentbot"
passed=0 failed=0
pass() { printf 'PASS: %s\n' "$1"; passed=$((passed + 1)); }
fail() { printf 'FAIL: %s\n' "$1" >&2; failed=$((failed + 1)); }
check() { local name="$1"; shift; if "$@"; then pass "$name"; else fail "$name"; fi; }

test_menu_source_exists() { [[ -f "$ROOT/scripts/menu.sh" ]]; }

test_menu_snapshot() {
	local output
	set +e
	output="$(unset NO_COLOR; export AGENTBOT_TUI=1; AGENTBOT_MENU_SOURCE_ONLY=1 source "$ROOT/scripts/menu.sh"; _agentbot_menu_setup; agentbot_menu_draw 0 80 2>&1)"
	set -e
	output="${output//$'\033[K'/}"
	[[ "$output" == *'=== Agentbot ==='* ]] || return 1
	[[ "$output" == *$'\033[1m\033[38;5;208m=== Agentbot ===\033[0m'* ]] || return 1
	[[ "$output" == *'Agentbot'* ]] || return 1
	[[ "$output" == *'1. Check status'* && "$output" == *'9. Quit'* ]] || return 1
	[[ "$output" == *$'9. Quit\n\n'* ]] || return 1
	[[ "$output" == *'Check the installed Agentbot components and baseline.'* ]] || return 1
}

test_menu_clears_line_tails_for_in_place_redraw() (
	AGENTBOT_MENU_SOURCE_ONLY=1 source "$ROOT/scripts/menu.sh"
	_agentbot_menu_setup
	local output
	output="$(agentbot_menu_draw 0 80)"
	[[ "$output" == *$'\033[K\n'* ]]
)

test_menu_uses_in_place_redraw_contract() (
	AGENTBOT_MENU_SOURCE_ONLY=1 source "$ROOT/scripts/menu.sh"
	_agentbot_menu_setup
	local frame output body redraw_call='agentbot_menu_redraw_up "$menu_lines"'
	frame="$(agentbot_menu_lines 0)"
	output="$(agentbot_menu_draw 0 80)"
	[[ "$frame" -eq "$(printf '%s\n' "$output" | wc -l)" ]] || return 1
	[[ "$(agentbot_menu_redraw_up "$frame")" == $'\033['"${frame}"'A' ]] || return 1
	body="$(declare -f menu_simple_run)"
	[[ "$body" == *"$redraw_call"* ]] || return 1
	[[ "$body" != *$'while true; do\n\t\tui_clear'* ]]
)

test_menu_exports_tui_render_mode_to_backend() (
	AGENTBOT_MENU_SOURCE_ONLY=1 source "$ROOT/scripts/menu.sh"
	local calls=0
	MENU_TEST_CHOICES=(status quit)
	MENU_TEST_INDEX=0
	menu_simple_run() {
		local choice="${MENU_TEST_CHOICES[$MENU_TEST_INDEX]}"
		MENU_TEST_INDEX=$((MENU_TEST_INDEX + 1))
		MENU_SIMPLE_RESULT="$choice"
	}
	ui_clear() { :; }
	ui_pause() { :; }
	agentbot_menu_status() {
		[[ "${AGENTBOT_TUI:-}" == 1 ]] || return 1
		calls=$((calls + 1))
	}
	agentbot_menu_loop
	[[ "$calls" -eq 1 ]]
)

test_command_lib_matches_colored_table_contract() (
	unset NO_COLOR
	AGENTBOT_MENU_COLS=80
	export AGENTBOT_MENU_COLS
	AGENTBOT_MENU_SOURCE_ONLY=1 source "$ROOT/scripts/menu.sh"
	local output
	output="$(agentbot_menu_command_lib)"
	[[ "$output" == *'Agentbot › Command Lib'* ]] || return 1
	[[ "$output" == *$'\033[1m\033[38;5;208m=== Command Lib ===\033[0m'* ]] || return 1
	[[ "$output" == *'command              | behavior   | description'* ]] || return 1
	grep -Eq '^  -+\+-+\+-+' <<<"$output" || return 1
	[[ "$output" == *$'\033[33mmutating\033[0m'* ]]
)

test_menu_hint_colors_key_tokens() (
	unset NO_COLOR
	AGENTBOT_MENU_SOURCE_ONLY=1 source "$ROOT/scripts/menu.sh"
	local output
	output="$(agentbot_menu_color_input_hint 'Up/Down navigate   Enter confirm   q back')"
	[[ "$output" == *$'\033[36mUp/Down'* ]] || return 1
	[[ "$output" == *$'\033[36mEnter'* ]] || return 1
	[[ "$output" == *$'\033[36mq'* ]] || return 1
)

test_pause_has_global_blank_line_contract() (
	AGENTBOT_MENU_SOURCE_ONLY=1 source "$ROOT/scripts/menu.sh"
	local body
	body="$(declare -f ui_pause)"
	[[ "$body" == *"printf '\\n' > /dev/tty"* ]]
)

test_dispatch_order_and_return() (
	AGENTBOT_MENU_SOURCE_ONLY=1 source "$ROOT/scripts/menu.sh"
	local calls="$TEST_ROOT/menu.calls"
	: >"$calls"
	MENU_TEST_CHOICES=(status install update token boot command_lib doctor dotfiles quit)
	MENU_TEST_INDEX=0
	menu_simple_run() {
		local choice="${MENU_TEST_CHOICES[$MENU_TEST_INDEX]}"
		MENU_TEST_INDEX=$((MENU_TEST_INDEX + 1))
		MENU_SIMPLE_RESULT="$choice"
	}
	ui_clear() { :; }
	ui_pause() { printf 'pause\n' >>"$calls"; }
	agentbot_menu_status() { printf 'status\n' >>"$calls"; }
	agentbot_menu_install() { printf 'install\n' >>"$calls"; }
	agentbot_menu_update() { printf 'update\n' >>"$calls"; }
	agentbot_menu_token() { printf 'token\n' >>"$calls"; }
	agentbot_menu_boot() { printf 'boot\n' >>"$calls"; }
	agentbot_menu_command_lib() { printf 'command_lib\n' >>"$calls"; }
	agentbot_menu_doctor() { printf 'doctor\n' >>"$calls"; }
	agentbot_menu_dotfiles() { printf 'dotfiles\n' >>"$calls"; }
	agentbot_menu_loop
	[[ "$(<"$calls")" == $'status\npause\ninstall\npause\nupdate\npause\ntoken\npause\nboot\npause\ncommand_lib\npause\ndoctor\npause\ndotfiles' ]]
)

test_failed_action_pauses_once() (
	AGENTBOT_MENU_SOURCE_ONLY=1 source "$ROOT/scripts/menu.sh"
	local calls="$TEST_ROOT/failure.calls"
	: >"$calls"
	MENU_TEST_CHOICES=(status quit)
	MENU_TEST_INDEX=0
	menu_simple_run() { local choice="${MENU_TEST_CHOICES[$MENU_TEST_INDEX]}"; MENU_TEST_INDEX=$((MENU_TEST_INDEX + 1)); MENU_SIMPLE_RESULT="$choice"; }
	ui_clear() { :; }
	ui_pause() { printf 'pause\n' >>"$calls"; }
	agentbot_menu_status() { return 17; }
	set +e
	agentbot_menu_loop >/dev/null 2>&1
	set -e
	[[ "$(grep -c '^pause$' "$calls")" -eq 1 ]]
)

test_failed_action_reports_red() (
	unset NO_COLOR
	AGENTBOT_MENU_SOURCE_ONLY=1 source "$ROOT/scripts/menu.sh"
	agentbot_menu_status() { return 17; }
	local output rc
	set +e
	output="$(agentbot_menu_dispatch status 2>&1)"
	rc=$?
	set -e
	[[ "$rc" -eq 17 ]] || return 1
	[[ "$output" == *$'\033[31mAction failed (exit 17).\033[0m'* ]]
)

test_update_action_calls_real_backend_and_dotfiles_stays_guarded() (
	AGENTBOT_MENU_SOURCE_ONLY=1 source "$ROOT/scripts/menu.sh"
	local output fake_home="$TEST_ROOT/fake-agentbot"
	ui_pause() { :; }
	ui_clear() { :; }
	mkdir -p "$fake_home"
	cat >"$fake_home/install.sh" <<'FAKE'
#!/usr/bin/env bash
printf 'real-update-backend %s\n' "$*"
[[ "${1:-}" == status ]] && exit 0
exit 1
FAKE
	chmod +x "$fake_home/install.sh"
	AGENTBOT_HOME="$fake_home"
	export AGENTBOT_HOME
	output="$(agentbot_menu_update 2>&1)"
	[[ "$output" == *'real-update-backend update --dry-run'* ]] || return 1
	DOTFILES_HOME="$TEST_ROOT/missing-dotfiles"
	SIBLING_DOTFILES_CONFIRM=no
	export DOTFILES_HOME SIBLING_DOTFILES_CONFIRM
	output="$(agentbot_menu_dotfiles 2>&1)"
	[[ "$output" == *'Dotfiles is not cloned'* && "$output" == *'launch cancelled'* ]]
)

test_update_pull_restarts_fresh_install_menu() (
	AGENTBOT_MENU_SOURCE_ONLY=1 source "$ROOT/scripts/menu.sh"
	local calls="$TEST_ROOT/update-relaunch.calls" fake_home="$TEST_ROOT/fake-agentbot-relaunch"
	: >"$calls"
	mkdir -p "$fake_home"
	cat >"$fake_home/install.sh" <<'FAKE'
#!/usr/bin/env bash
printf 'install:%s\n' "$*" >>"${TEST_UPDATE_CALLS:?}"
case "$1 ${2:-}" in
  'status ') exit 0 ;;
  'update --dry-run') exit 2 ;;
esac
exit 0
FAKE
	chmod +x "$fake_home/install.sh"
	AGENTBOT_HOME="$fake_home" TEST_UPDATE_CALLS="$calls"
	export AGENTBOT_HOME TEST_UPDATE_CALLS
	ui_pause() { printf 'pause\n' >>"$calls"; }
	agentbot_menu_relaunch() { printf 'relaunch\n' >>"$calls"; }
	agentbot_menu_update || return 1
	[[ "$(<"$calls")" == $'install:update --dry-run\npause\nrelaunch' ]]
)

test_caller_guard_hides_dotfiles_entry() (
	AGENTBOT_MENU_SOURCE_ONLY=1 source "$ROOT/scripts/menu.sh"
	SETUP_CALLER=dotfiles
	export SETUP_CALLER
	_agentbot_menu_setup
	! printf '%s\n' "${MENU_SIMPLE_KEYS[@]}" | grep -Fxq dotfiles
)

check 'Agentbot menu source exists' test_menu_source_exists
if [[ -f "$ROOT/scripts/menu.sh" ]]; then
	check 'Agentbot menu snapshot has title, breadcrumb, spacing, and all actions' test_menu_snapshot
	check 'Agentbot menu clears stale line tails during in-place redraw' test_menu_clears_line_tails_for_in_place_redraw
	check 'Agentbot menu redraws in place without clearing on cursor movement' test_menu_uses_in_place_redraw_contract
	check 'Agentbot menu exports TUI render mode to backend reports' test_menu_exports_tui_render_mode_to_backend
	check 'Agentbot Command Lib matches the colored table contract' test_command_lib_matches_colored_table_contract
	check 'Agentbot input hints color the interactive key tokens' test_menu_hint_colors_key_tokens
	check 'Agentbot pauses use the shared blank-line contract' test_pause_has_global_blank_line_contract
	check 'Agentbot menu dispatches actions in order and returns on Quit' test_dispatch_order_and_return
	check 'failed Agentbot action pauses once and returns' test_failed_action_pauses_once
	check 'failed Agentbot actions use the red failure color' test_failed_action_reports_red
	check 'Update calls the real backend and Dotfiles remains guarded' test_update_action_calls_real_backend_and_dotfiles_stays_guarded
	check 'Update restarts the fresh install menu after a repository pull' test_update_pull_restarts_fresh_install_menu
	check 'SETUP_CALLER=dotfiles hides the reciprocal menu entry' test_caller_guard_hides_dotfiles_entry
else
	fail 'Agentbot menu snapshot has title, breadcrumb, spacing, and all actions'
	fail 'Agentbot menu clears stale line tails during in-place redraw'
	fail 'Agentbot menu redraws in place without clearing on cursor movement'
	fail 'Agentbot menu exports TUI render mode to backend reports'
	fail 'Agentbot Command Lib matches the colored table contract'
	fail 'Agentbot input hints color the interactive key tokens'
	fail 'Agentbot pauses use the shared blank-line contract'
	fail 'Agentbot menu dispatches actions in order and returns on Quit'
	fail 'failed Agentbot action pauses once and returns'
	fail 'failed Agentbot actions use the red failure color'
	fail 'deferred Update and Dotfiles actions are explicitly unavailable'
fi

printf '\nRan %d Agentbot menu test(s); %d failure(s).\n' "$((passed + failed))" "$failed"
((failed == 0))
