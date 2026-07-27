#!/usr/bin/env bash
# shellcheck shell=bash
# shellcheck disable=SC2034

agentbot_menu_graphify_confirm() {
	local answer=''
	printf '%sSet up or refresh Graphify Agent Skills for the enabled assistants?%s [y/N]: ' "$C_YELLOW" "$C_RESET" >/dev/tty
	IFS= read -r answer </dev/tty || answer=n
	case "$answer" in
	y|Y|yes|YES) return 0 ;;
	*) return 1 ;;
	esac
}

agentbot_menu_graphify_cli_available() {
	command -v graphify >/dev/null 2>&1
}

agentbot_menu_graphify_dispatch() {
	local choice="$1" rc=0
	case "$choice" in
	status) agentbot_run_backend graphify status || rc=$? ;;
	setup)
		local status_output=''
		status_output="$(agentbot_run_backend graphify status 2>&1)" || rc=$?
		printf '%s\n' "$status_output"
		if ((rc != 0)); then
			return "$rc"
		fi
		if ! agentbot_menu_graphify_cli_available; then
			printf '%sGraphify CLI is not installed. Select Graphify CLI in Dotfiles first, then retry.%s\n' "$C_YELLOW" "$C_RESET"
			return 0
		fi
		if agentbot_menu_graphify_confirm; then
			agentbot_run_backend graphify setup || rc=$?
		else
			printf '%sGraphify setup cancelled.%s\n' "$C_DIM" "$C_RESET"
		fi
		;;
	*) printf 'Unknown Graphify action: %s\n' "$choice" >&2; rc=2 ;;
	esac
	if ((rc != 0)); then
		printf '%sAction failed (exit %d).%s\n' "$C_RED" "$rc" "$C_RESET" >&2
	fi
	return "$rc"
}

agentbot_menu_graphify() {
	local choice rc

	MENU_SIMPLE_TITLE='Graphify'
	MENU_SIMPLE_BREADCRUMB='Agentbot › Graphify'
	MENU_SIMPLE_LABELS=(
		'Check status'
		'Set up Agent Skills'
	)
	MENU_SIMPLE_KEYS=(status setup)
	MENU_SIMPLE_DESCS=(
		$'Read the Graphify CLI, skill, and assistant-link state.\nNo files or external commands are changed.'
		$'Run Graphify\'s generic Agent Skills installer after confirmation.\nThe CLI must already be installed through Dotfiles.'
	)

	while true; do
		if ! menu_simple_run; then
			MENU_SIMPLE_TITLE='Agentbot'
			MENU_SIMPLE_BREADCRUMB='Agentbot'
			return 0
		fi
		choice="${MENU_SIMPLE_RESULT:-}"
		ui_clear
		rc=0
		agentbot_menu_graphify_dispatch "$choice" || rc=$?
		ui_pause
	done
}
