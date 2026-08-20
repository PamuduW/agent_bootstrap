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

strip_ansi_stream() { sed $'s/\033\\[[0-9;?]*[A-Za-z]//g; s/[[:space:]]*$//'; }

test_main_menu_snapshot() {
	local output
	_agentbot_menu_setup
	output="$(AGENTBOT_TUI=1 tui_menu_draw 0 80 | strip_ansi_stream)"
	[[ "$output" == *$'=== Agentbot ===\n  Agentbot'* ]] || return 1
	[[ "$output" == *'1. Check Status'* && "$output" == *'7. Quit'* ]] || return 1
	[[ "$output" == *'GitHub Token Config'* && "$output" == *'Libraries'* ]] || return 1
	[[ "$output" == *'Check the installed Agentbot components and baseline.'* ]]
}

test_width_and_palette_snapshots() (
	local cols output plain line
	for cols in 48 80 120; do
		NO_COLOR=1; tui_init_colors
		output="$({
			tui_header 'Check Status' 'Agentbot › Check Status' "$cols"
			tui_section Health "$cols"
			tui_table_header "$cols" component installed available action
			tui_table_row "$cols" agentbot current current none
		} | strip_ansi_stream)"
		[[ "$output" == *'=== Check Status ==='* && "$output" == *'Health'* ]] || return 1
		while IFS= read -r line; do ((${#line} <= cols)) || return 1; done <<<"$output"

		unset NO_COLOR; tui_init_colors
		output="$(tui_header 'Check Status' 'Agentbot › Check Status' "$cols"; tui_section Health "$cols"; tui_table_header "$cols" component installed available action)"
		[[ "$output" == *$'\033[1m\033[38;5;208m=== Check Status ==='* ]] || return 1
		[[ "$output" == *$'\033[1m\033[33mHealth'* ]] || return 1
		[[ "$output" == *$'\033[1m\033[37m'* ]] || return 1
		while IFS= read -r line; do
			plain="$(strip_ansi_stream <<<"$line")"
			((${#plain} <= cols)) || return 1
		done <<<"$output"
	done
)

test_draw_clears_line_tails_and_matches_frame_height() (
	_agentbot_menu_setup
	local output frame
	output="$(tui_menu_draw 0 80)"
	frame="$(tui_menu_lines 0)"
	[[ "$output" == *$'\033[K\n'* ]] || return 1
	[[ "$frame" -eq "$(printf '%s\n' "$output" | wc -l)" ]] || return 1
	[[ "$(tui_redraw_up "$frame")" == $'\033['"${frame}"'A' ]]
)

test_shortcuts_use_cyan_tokens() (
	unset NO_COLOR; tui_init_colors
	local output
	output="$(tui_color_input_hint 'Up/Down navigate   Enter confirm   q back')"
	[[ "$output" == *$'\033[36mUp/Down'* ]] || return 1
	[[ "$output" == *$'\033[36mEnter'* ]] || return 1
	[[ "$output" == *$'\033[36mq'* ]]
)

test_pause_uses_one_blank_line_and_shared_prompt() (
	local input="$TEST_ROOT/pause.input" output="$TEST_ROOT/pause.output"
	printf '\n' >"$input"
	NO_COLOR=1; tui_init_colors
	AGENTBOT_TUI_INPUT="$input" AGENTBOT_TUI_OUTPUT="$output" tui_pause
	[[ "$(<"$output")" == $'\nPress Enter to continue: ' ]]
)

test_command_details_fit_narrow_terminals() (
	local output line
	output="$(NO_COLOR=1 AGENTBOT_MENU_COLS=48 "$ROOT/bin/agentbot" help)" || return 1
	while IFS= read -r line; do ((${#line} <= 48)) || return 1; done <<<"$output"
)

check 'main menu snapshot uses the unified labels and breadcrumb' test_main_menu_snapshot
check 'TUI frames fit 48, 80, and 120 columns with the shared palette' test_width_and_palette_snapshots
check 'menu redraw frames clear stale tails and preserve height' test_draw_clears_line_tails_and_matches_frame_height
check 'shortcut tokens use the shared cyan treatment' test_shortcuts_use_cyan_tokens
check 'pause uses one blank line and one shared prompt' test_pause_uses_one_blank_line_and_shared_prompt
check 'command details fit a 48-column terminal' test_command_details_fit_narrow_terminals

test_harness_verify_safety || failed=$((failed + 1))
printf '\nRan %d menu-core test(s); %d failure(s).\n' "$((passed + failed))" "$failed"
test_harness_cleanup || failed=$((failed + 1))
((failed == 0))
