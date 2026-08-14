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
	[[ "$output" == *'1. Check status'* && "$output" == *'8. Quit'* ]] || return 1
	[[ "$output" == *$'8. Quit\n\n'* ]] || return 1
	[[ "$output" == *'Libraries'* ]] || return 1
	[[ "$output" != *'Repo setup (agentbot)'* ]] || return 1
	[[ "$output" == *'Workspaces'* ]] || return 1
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

test_status_combines_status_and_doctor_backends() (
	AGENTBOT_MENU_SOURCE_ONLY=1 source "$ROOT/scripts/menu.sh"
	local calls="$TEST_ROOT/status.calls"
	: >"$calls"
	agentbot_run_backend() { printf '%s\n' "$*" >>"$calls"; }
	agentbot_menu_status
	[[ "$(<"$calls")" == $'status\ndoctor' ]]
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

test_command_lib_documents_full_help_catalog() (
	AGENTBOT_MENU_SOURCE_ONLY=1 source "$ROOT/scripts/menu.sh"
	local output
	output="$(AGENTBOT_MENU_COLS=100 agentbot_menu_command_lib)"
	agentbot_command_catalog_validate
	for needle in \
		'--claude' \
		'Include generated Claude output' \
		'default: opt-in' \
		'--profile NAME' \
		'--targets LIST' \
		'--dry-run' \
		'--paths0' \
		'--remove PATH' \
		'No workspace files are changed' \
		'AGENTBOT_HOME' \
		'XDG_CONFIG_HOME' \
		'GITHUB_TOKEN' \
		'AGENTS.md' \
		'Dotfiles integration'; do
		[[ "$output" == *"$needle"* ]] || {
			printf 'missing Command Lib detail: %s\n' "$needle" >&2
			return 1
		}
	done
)

test_failed_dotfiles_launch_pauses_before_redraw() (
	AGENTBOT_MENU_SOURCE_ONLY=1 source "$ROOT/scripts/menu.sh"
	local dispatches=0 pauses=0
	MENU_SIMPLE_RESULT=''
	menu_simple_run() {
		if ((dispatches == 0)); then
			MENU_SIMPLE_RESULT=dotfiles
		else
			MENU_SIMPLE_RESULT=quit
		fi
		dispatches=$((dispatches + 1))
		return 0
	}
	sibling_dotfiles_launch() { return 23; }
	ui_clear() { :; }
	ui_pause() { pauses=$((pauses + 1)); }

	agentbot_menu_loop
	[[ "$dispatches" -eq 2 && "$pauses" -eq 1 ]]
)

test_command_lib_details_fit_narrow_terminal() (
	AGENTBOT_MENU_SOURCE_ONLY=1 source "$ROOT/scripts/menu.sh"
	local output line
	output="$(NO_COLOR=1 AGENTBOT_MENU_COLS=48 agentbot_menu_command_lib)"
	while IFS= read -r line; do
		(( ${#line} <= 48 )) || {
			printf 'line exceeds 48 columns (%d): %s\n' "${#line}" "$line" >&2
			return 1
		}
	done <<<"$output"
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

test_workspaces_menu_uses_scrollable_submenu_contract() (
	AGENTBOT_MENU_SOURCE_ONLY=1 source "$ROOT/scripts/menu.sh"
	local capture="$TEST_ROOT/workspaces-menu-contract.calls"
	: >"$capture"
	menu_simple_run() {
		printf '%s|%s|%s|%s\n' "$MENU_SIMPLE_TITLE" "$MENU_SIMPLE_BREADCRUMB" \
			"${MENU_SIMPLE_LABELS[*]}" "${MENU_SIMPLE_KEYS[*]}" >"$capture"
		MENU_SIMPLE_RESULT=''
		return 1
	}
	ui_clear() { :; }
	agentbot_menu_workspaces
	[[ "$(<"$capture")" == 'Workspaces|Agentbot › Workspaces|List recorded workspaces Preview resync (all) Apply resync (all) Remove recorded workspaces|list preview apply remove' ]] || return 1
	[[ "$MENU_SIMPLE_TITLE" == Agentbot && "$MENU_SIMPLE_BREADCRUMB" == Agentbot ]]
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
	MENU_TEST_CHOICES=(status install update token workspaces libraries dotfiles quit)
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
	agentbot_menu_workspaces() { printf 'workspaces\n' >>"$calls"; }
	agentbot_menu_libraries() { printf 'libraries\n' >>"$calls"; }
	agentbot_menu_dotfiles() { printf 'dotfiles\n' >>"$calls"; }
	agentbot_menu_loop
	[[ "$(<"$calls")" == $'status\npause\ninstall\npause\nupdate\npause\ntoken\npause\nworkspaces\nlibraries\npause\ndotfiles' ]]
)

test_graphify_lib_is_read_only_and_documents_platform_forms() (
	AGENTBOT_MENU_SOURCE_ONLY=1 source "$ROOT/scripts/menu.sh"
	local calls="$TEST_ROOT/graphify-lib.calls" output
	: >"$calls"
	agentbot_run_backend() { printf 'backend:%s\n' "$*" >>"$calls"; }
	output="$(AGENTBOT_MENU_COLS=100 agentbot_menu_graphify_lib 2>&1)"
	for needle in \
		'Graphify Lib' \
		'Agentbot › Graphify Lib' \
		'Claude/Cursor: /graphify .' \
		"Codex: \$graphify ." \
		'graphify update .' \
		'graphify query "what connects auth to the database?"' \
		'Agentbot Install and Update run only: graphify install --platform agents' \
		'graphify install --platform agents' \
		'graphify claude install' \
		'graphify agents install' \
		'graphify codex install' \
		'graphify cursor install' \
		'Direct agentbot graphify status|setup commands remain available'; do
		[[ "$output" == *"$needle"* ]] || {
			printf 'missing Graphify command detail: %s\n' "$needle" >&2
			return 1
		}
	done
	[[ ! -s "$calls" ]]
)

test_main_menu_rebuilds_after_workspaces_returns() (
	AGENTBOT_MENU_SOURCE_ONLY=1 source "$ROOT/scripts/menu.sh"
	local capture="$TEST_ROOT/main-after-workspaces.calls" choice_index=0 choice
	local choices=(workspaces back quit)
	: >"$capture"
	menu_simple_run() {
		choice="${choices[$choice_index]}"
		choice_index=$((choice_index + 1))
		if [[ "$choice" == back ]]; then
			MENU_SIMPLE_RESULT=''
			return 1
		fi
		if [[ "$choice" == quit ]]; then
			printf '%s|%s|%s\n' "$MENU_SIMPLE_TITLE" "$MENU_SIMPLE_BREADCRUMB" \
				"${MENU_SIMPLE_LABELS[*]}" >"$capture"
		fi
		MENU_SIMPLE_RESULT="$choice"
	}
	ui_clear() { :; }
	ui_pause() { :; }
	agentbot_menu_loop
	[[ "$(<"$capture")" == 'Agentbot|Agentbot|Check status Install Agentbot Update Configure GitHub token Workspaces Libraries Dotfiles Quit' ]]
)

test_agentbot_libraries_submenu_uses_q_back() (
	AGENTBOT_MENU_SOURCE_ONLY=1 source "$ROOT/scripts/menu.sh"
	local capture="$TEST_ROOT/agentbot-libraries-menu.capture"
	menu_simple_run() {
		printf '%s|%s|%s|%s\n' "$MENU_SIMPLE_TITLE" "$MENU_SIMPLE_BREADCRUMB" \
			"${MENU_SIMPLE_LABELS[*]}" "${MENU_SIMPLE_KEYS[*]}" >"$capture"
		return 1
	}
	agentbot_menu_libraries
	[[ "$(<"$capture")" == 'Libraries|Agentbot › Libraries|Command Lib Graphify Lib|command_lib graphify_lib' ]]
)

test_workspaces_menu_actions() (
	AGENTBOT_MENU_SOURCE_ONLY=1 source "$ROOT/scripts/menu.sh"
	local calls="$TEST_ROOT/workspaces.calls" choice_index=0 choice
	: >"$calls"
	local choices=(list preview apply back)
	menu_simple_run() {
		choice="${choices[$choice_index]}"
		choice_index=$((choice_index + 1))
		if [[ "$choice" == back ]]; then
			MENU_SIMPLE_RESULT=''
			return 1
		fi
		MENU_SIMPLE_RESULT="$choice"
		return 0
	}
	ui_clear() { :; }
	ui_pause() { printf 'pause\n' >>"$calls"; }
	agentbot_menu_workspaces_confirm() { return 0; }
	agentbot_run_backend() { printf 'backend:%s\n' "$*" >>"$calls"; }
	agentbot_menu_workspaces
	[[ "$(<"$calls")" == $'backend:workspaces\npause\nbackend:resync --all\npause\nbackend:resync --all --yes\npause' ]]
)

test_workspaces_remove_forgets_exact_record_and_reloads() (
	AGENTBOT_MENU_SOURCE_ONLY=1 source "$ROOT/scripts/menu.sh"
	local calls="$TEST_ROOT/workspaces-remove.calls" choice_index=0 list_count=0
	local choices=(1 back)
	: >"$calls"
	menu_simple_run() {
		local choice="${choices[$choice_index]}"
		choice_index=$((choice_index + 1))
		if [[ "$choice" == back ]]; then
			MENU_SIMPLE_RESULT=''
			return 1
		fi
		MENU_SIMPLE_RESULT="$choice"
	}
	agentbot_menu_workspaces_remove_confirm() { return 0; }
	agentbot_run_backend() {
		if [[ "$*" == 'workspaces --paths0' ]]; then
			list_count=$((list_count + 1))
			if ((list_count == 1)); then
				printf '/repo/a\0/missing/b\0'
			else
				printf '/repo/a\0'
			fi
		else
			printf 'backend:%s\n' "$*" >>"$calls"
		fi
	}
	ui_clear() { :; }
	ui_pause() { printf 'pause\n' >>"$calls"; }

	agentbot_menu_workspaces_remove_recorded

	[[ "$(<"$calls")" == $'backend:workspaces --remove /missing/b\npause' ]]
)

test_workspaces_remove_decline_is_non_destructive() (
	AGENTBOT_MENU_SOURCE_ONLY=1 source "$ROOT/scripts/menu.sh"
	local calls="$TEST_ROOT/workspaces-remove-decline.calls" choice_index=0
	local choices=(0 back)
	: >"$calls"
	menu_simple_run() {
		local choice="${choices[$choice_index]}"
		choice_index=$((choice_index + 1))
		if [[ "$choice" == back ]]; then MENU_SIMPLE_RESULT=''; return 1; fi
		MENU_SIMPLE_RESULT="$choice"
	}
	agentbot_menu_workspaces_remove_confirm() { return 1; }
	agentbot_run_backend() {
		[[ "$*" == 'workspaces --paths0' ]] && printf '/repo/a\0' || printf 'backend:%s\n' "$*" >>"$calls"
	}
	ui_clear() { :; }
	ui_pause() { :; }

	agentbot_menu_workspaces_remove_recorded

	[[ ! -s "$calls" ]]
)

test_workspaces_remove_empty_registry_is_safe() (
	AGENTBOT_MENU_SOURCE_ONLY=1 source "$ROOT/scripts/menu.sh"
	local output
	agentbot_run_backend() { return 0; }
	ui_pause() { :; }
	output="$(agentbot_menu_workspaces_remove_recorded)"
	[[ "$output" == *'No recorded workspaces to remove.'* ]]
)

test_workspaces_remove_list_failure_is_not_reported_as_empty() (
	AGENTBOT_MENU_SOURCE_ONLY=1 source "$ROOT/scripts/menu.sh"
	local output pauses=0
	agentbot_run_backend() { printf 'malformed registry\n' >&2; return 9; }
	ui_pause() { pauses=$((pauses + 1)); }
	set +e
	output="$(agentbot_menu_workspaces_remove_recorded 2>&1)"
	local rc=$?
	set -e
	[[ "$rc" -eq 9 ]] || return 1
	[[ "$output" == *'malformed registry'* ]] || return 1
	[[ "$output" != *'No recorded workspaces'* ]]
)

test_failed_workspaces_remove_pauses_once_before_redraw() (
	AGENTBOT_MENU_SOURCE_ONLY=1 source "$ROOT/scripts/menu.sh"
	local calls="$TEST_ROOT/workspaces-remove-failure.calls" choice_index=0
	local choices=(remove back)
	: >"$calls"
	menu_simple_run() {
		local choice="${choices[$choice_index]}"
		choice_index=$((choice_index + 1))
		if [[ "$choice" == back ]]; then MENU_SIMPLE_RESULT=''; return 1; fi
		MENU_SIMPLE_RESULT="$choice"
	}
	agentbot_menu_workspaces_remove_recorded() { return 9; }
	ui_clear() { :; }
	ui_pause() { printf 'pause\n' >>"$calls"; }
	set +e
	agentbot_menu_workspaces >/dev/null 2>&1
	set -e
	[[ "$(<"$calls")" == pause ]]
)

test_workspaces_menu_apply_decline_is_safe() (
	AGENTBOT_MENU_SOURCE_ONLY=1 source "$ROOT/scripts/menu.sh"
	local calls="$TEST_ROOT/workspaces-decline.calls"
	: >"$calls"
	local choice_index=0
	menu_simple_run() {
		if ((choice_index == 0)); then
			choice_index=1
			MENU_SIMPLE_RESULT='apply'
			return 0
		fi
		MENU_SIMPLE_RESULT=''
		return 1
	}
	ui_clear() { :; }
	ui_pause() { printf 'pause\n' >>"$calls"; }
	agentbot_menu_workspaces_confirm() { return 1; }
	agentbot_run_backend() { printf 'backend:%s\n' "$*" >>"$calls"; }
	agentbot_menu_workspaces
	[[ "$(<"$calls")" == 'pause' ]]
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

test_update_action_preserves_detailed_dirty_report() (
	AGENTBOT_MENU_SOURCE_ONLY=1 source "$ROOT/scripts/menu.sh"
	local output rc fake_home="$TEST_ROOT/fake-agentbot-dirty"
	mkdir -p "$fake_home"
	cat >"$fake_home/install.sh" <<'FAKE'
#!/usr/bin/env bash
printf '%s\n' \
	'Repository update' \
	'agent_bootstrap repo | main@abc123 / 2 local change(s) | blocked' \
	'origin/main | current | blocked' \
	'Local changes:' \
	'  ?? .cursor/rules/agentbot-policy.mdc' \
	'Repository pull and downstream updates stopped.'
exit 1
FAKE
	chmod +x "$fake_home/install.sh"
	AGENTBOT_HOME="$fake_home"
	export AGENTBOT_HOME
	set +e
	output="$(agentbot_menu_update 2>&1)"
	rc=$?
	set -e
	[[ "$rc" -eq 1 ]] || return 1
	[[ "$output" == *'2 local change(s)'* ]] || return 1
	[[ "$output" == *'origin/main | current | blocked'* ]] || return 1
	[[ "$output" == *'?? .cursor/rules/agentbot-policy.mdc'* ]] || return 1
	[[ "$output" == *'Repository pull and downstream updates stopped.'* ]]
)

test_tui_update_routes_dirty_report_to_tty() (
	AGENTBOT_MENU_SOURCE_ONLY=1 source "$ROOT/scripts/menu.sh"
	local rc fake_home="$TEST_ROOT/fake-agentbot-dirty-tty"
	local tty_output="$TEST_ROOT/update-dirty.tty" inherited_output="$TEST_ROOT/update-dirty.inherited"
	mkdir -p "$fake_home"
	cat >"$fake_home/install.sh" <<'FAKE'
#!/usr/bin/env bash
printf '%s\n' \
	'Repository update' \
	'agent_bootstrap repo | main@abc123 / 2 local change(s) | blocked' \
	'origin/main | current | verified' \
	'Local changes:' \
	'  ?? .cursor/rules/agentbot-policy.mdc' \
	'Repository pull and downstream updates stopped.'
exit 1
FAKE
	chmod +x "$fake_home/install.sh"
	: >"$tty_output"
	: >"$inherited_output"
	AGENTBOT_HOME="$fake_home"
	AGENTBOT_TUI=1
	AGENTBOT_UPDATE_TTY_OUTPUT="$tty_output"
	export AGENTBOT_HOME AGENTBOT_TUI AGENTBOT_UPDATE_TTY_OUTPUT
	set +e
	agentbot_menu_update >"$inherited_output" 2>&1
	rc=$?
	set -e
	[[ "$rc" -eq 1 ]] || return 1
	grep -Fq 'Repository update' "$tty_output" || return 1
	grep -Fq '?? .cursor/rules/agentbot-policy.mdc' "$tty_output" || return 1
	grep -Fq 'Repository pull and downstream updates stopped.' "$tty_output" || return 1
	[[ ! -s "$inherited_output" ]]
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
	! printf '%s\n' "${MENU_SIMPLE_KEYS[@]}" | grep -Fxq dotfiles || return 1
	[[ "${#MENU_SIMPLE_LABELS[@]}" -eq "${#MENU_SIMPLE_KEYS[@]}" ]] || return 1
	[[ "${#MENU_SIMPLE_LABELS[@]}" -eq "${#MENU_SIMPLE_DESCS[@]}" ]]
)

check 'Agentbot menu source exists' test_menu_source_exists
if [[ -f "$ROOT/scripts/menu.sh" ]]; then
	check 'Agentbot menu snapshot has title, breadcrumb, spacing, and all actions' test_menu_snapshot
	check 'Agentbot menu clears stale line tails during in-place redraw' test_menu_clears_line_tails_for_in_place_redraw
	check 'Agentbot menu redraws in place without clearing on cursor movement' test_menu_uses_in_place_redraw_contract
	check 'Agentbot menu exports TUI render mode to backend reports' test_menu_exports_tui_render_mode_to_backend
	check 'Agentbot Command Lib matches the colored table contract' test_command_lib_matches_colored_table_contract
	check 'Agentbot Command Lib documents the full command/config catalog' test_command_lib_documents_full_help_catalog
	check 'failed Dotfiles launch pauses before the Agentbot menu redraws' test_failed_dotfiles_launch_pauses_before_redraw
	check 'Agentbot Command Lib wraps details to the terminal width' test_command_lib_details_fit_narrow_terminal
	check 'Agentbot input hints color the interactive key tokens' test_menu_hint_colors_key_tokens
	check 'Workspaces uses the scrollable submenu title and breadcrumb contract' test_workspaces_menu_uses_scrollable_submenu_contract
	check 'Agentbot pauses use the shared blank-line contract' test_pause_has_global_blank_line_contract
	check 'Agentbot menu dispatches actions in order and returns on Quit' test_dispatch_order_and_return
	check 'Graphify Lib is a read-only platform-aware reference' test_graphify_lib_is_read_only_and_documents_platform_forms
	check 'Agentbot menu rebuilds after returning from Workspaces' test_main_menu_rebuilds_after_workspaces_returns
	check 'Workspaces menu exposes actions and keeps apply confirmation safe' test_workspaces_menu_actions
	check 'Workspaces removal forgets the exact record and reloads the registry' test_workspaces_remove_forgets_exact_record_and_reloads
	check 'declined Workspaces removal is non-destructive' test_workspaces_remove_decline_is_non_destructive
	check 'empty Workspaces removal registry is safe' test_workspaces_remove_empty_registry_is_safe
	check 'Workspaces removal preserves backend list failures' test_workspaces_remove_list_failure_is_not_reported_as_empty
	check 'failed Workspaces removal pauses once before redraw' test_failed_workspaces_remove_pauses_once_before_redraw
	check 'declined Workspaces apply never invokes --yes' test_workspaces_menu_apply_decline_is_safe
	check 'failed Agentbot action pauses once and returns' test_failed_action_pauses_once
	check 'failed Agentbot actions use the red failure color' test_failed_action_reports_red
	check 'Update calls the real backend and Dotfiles remains guarded' test_update_action_calls_real_backend_and_dotfiles_stays_guarded
	check 'Update preserves the detailed dirty-worktree report' test_update_action_preserves_detailed_dirty_report
	check 'TUI Update routes the complete dirty report to the controlling terminal' test_tui_update_routes_dirty_report_to_tty
	check 'Update restarts the fresh install menu after a repository pull' test_update_pull_restarts_fresh_install_menu
	check 'SETUP_CALLER=dotfiles hides the reciprocal menu entry' test_caller_guard_hides_dotfiles_entry
else
	fail 'Agentbot menu snapshot has title, breadcrumb, spacing, and all actions'
	fail 'Agentbot menu clears stale line tails during in-place redraw'
	fail 'Agentbot menu redraws in place without clearing on cursor movement'
	fail 'Agentbot menu exports TUI render mode to backend reports'
	fail 'Agentbot Command Lib matches the colored table contract'
	fail 'Agentbot Command Lib documents the full command/config catalog'
	fail 'Agentbot Command Lib wraps details to the terminal width'
	fail 'Agentbot input hints color the interactive key tokens'
	fail 'Agentbot pauses use the shared blank-line contract'
	fail 'Agentbot menu dispatches actions in order and returns on Quit'
	fail 'failed Agentbot action pauses once and returns'
	fail 'failed Agentbot actions use the red failure color'
	fail 'deferred Update and Dotfiles actions are explicitly unavailable'
fi

printf '\nRan %d Agentbot menu test(s); %d failure(s).\n' "$((passed + failed))" "$failed"
((failed == 0))
