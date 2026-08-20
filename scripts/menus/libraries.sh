#!/usr/bin/env bash
# shellcheck shell=bash
# shellcheck disable=SC2034  # MENU_SIMPLE_* globals are consumed by menu_simple_run.

agentbot_menu_libraries_dispatch() {
	local choice="$1" rc=0
	case "$choice" in
	command_lib) agentbot_menu_command_lib || rc=$? ;;
	graphify_lib) agentbot_menu_graphify_lib || rc=$? ;;
	*) printf 'Unknown Libraries action: %s\n' "$choice" >&2; rc=2 ;;
	esac
	if ((rc != 0)); then
		printf '%sAction failed (exit %d).%s\n' "$C_RED" "$rc" "$C_RESET" >&2
	fi
	return "$rc"
}

agentbot_menu_libraries() {
	local choice rc

	while true; do
		MENU_SIMPLE_TITLE='Libraries'
		MENU_SIMPLE_BREADCRUMB='Agentbot › Libraries'
		MENU_SIMPLE_LABELS=('Command Lib' 'Graphify Lib')
		MENU_SIMPLE_KEYS=(command_lib graphify_lib)
		MENU_SIMPLE_DESCS=(
			$'Show Agentbot commands and whether they read or mutate state.\nUse this as the local command reference.'
			$'Show Graphify assistant and shell commands plus safety boundaries.\nRead-only; Install and Update own generic skill synchronization.'
		)

		if ! menu_simple_run; then
			MENU_SIMPLE_TITLE='Agentbot'
			MENU_SIMPLE_BREADCRUMB='Agentbot'
			return 0
		fi
		choice="${MENU_SIMPLE_RESULT:-}"
		tui_clear
		rc=0
		agentbot_menu_libraries_dispatch "$choice" || rc=$?
		((rc == 0)) || tui_pause
	done
}
