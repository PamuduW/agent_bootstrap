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
	output="$(AGENTBOT_MENU_SOURCE_ONLY=1 source "$ROOT/scripts/menu.sh"; _agentbot_menu_setup; agentbot_menu_draw 0 80 2>&1)"
	set -e
	[[ "$output" == *'=== Agentbot ==='* ]] || return 1
	[[ "$output" == *'Agentbot'* ]] || return 1
	[[ "$output" == *'1. Check status'* && "$output" == *'9. Quit'* ]] || return 1
	[[ "$output" == *$'9. Quit\n\n'* ]] || return 1
	[[ "$output" == *'Check the installed Agentbot components and baseline.'* ]] || return 1
}

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
	[[ "$(<"$calls")" == $'status\npause\ninstall\npause\nupdate\npause\ntoken\npause\nboot\npause\ncommand_lib\npause\ndoctor\npause\ndotfiles\npause' ]]
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

test_update_action_calls_real_backend_and_dotfiles_stays_guarded() (
	AGENTBOT_MENU_SOURCE_ONLY=1 source "$ROOT/scripts/menu.sh"
	local output fake_home="$TEST_ROOT/fake-agentbot"
	ui_pause() { :; }
	ui_clear() { :; }
	mkdir -p "$fake_home"
	cat >"$fake_home/install.sh" <<'FAKE'
#!/usr/bin/env bash
printf 'real-update-backend %s\n' "$*"
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
	check 'Agentbot menu dispatches actions in order and returns on Quit' test_dispatch_order_and_return
	check 'failed Agentbot action pauses once and returns' test_failed_action_pauses_once
	check 'Update calls the real backend and Dotfiles remains guarded' test_update_action_calls_real_backend_and_dotfiles_stays_guarded
	check 'SETUP_CALLER=dotfiles hides the reciprocal menu entry' test_caller_guard_hides_dotfiles_entry
else
	fail 'Agentbot menu snapshot has title, breadcrumb, spacing, and all actions'
	fail 'Agentbot menu dispatches actions in order and returns on Quit'
	fail 'failed Agentbot action pauses once and returns'
	fail 'deferred Update and Dotfiles actions are explicitly unavailable'
fi

printf '\nRan %d Agentbot menu test(s); %d failure(s).\n' "$((passed + failed))" "$failed"
((failed == 0))
