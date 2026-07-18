#!/usr/bin/env bash
# shellcheck shell=bash

agentbot_menu_workspaces_read_choice() {
	local choice=''
	printf '%sChoose an action [1-4/q]: %s' "$C_CYAN" "$C_RESET" >/dev/tty
	IFS= read -r choice </dev/tty || return 1
	printf '%s\n' "$choice"
}

agentbot_menu_workspaces_confirm() {
	local answer=''
	printf '%sApply Agentbot-managed workspace changes?%s [y/N]: ' "$C_YELLOW" "$C_RESET" >/dev/tty
	IFS= read -r answer </dev/tty || answer=n
	printf '%s\n' "$answer"
}

agentbot_menu_workspaces() {
	local choice answer
	printf '\n  %s%s=== Workspaces ===%s\n' "$C_BOLD" "$C_ORANGE" "$C_RESET"
	printf '  %sAgentbot › Workspaces%s\n\n' "$C_DIM" "$C_RESET"
	printf '  1. List recorded workspaces\n'
	printf '  2. Preview resync for all recorded\n'
	printf '  3. Apply resync for all recorded\n'
	printf '  4. Set up current repository\n'

	choice="$(agentbot_menu_workspaces_read_choice)" || return 0
	case "$choice" in
	1) agentbot_run_backend workspaces ;;
	2) agentbot_run_backend resync --all ;;
	3)
		answer="$(agentbot_menu_workspaces_confirm)"
	case "$answer" in
		y|Y|yes|YES) agentbot_run_backend resync --all --yes ;;
		*) printf '%sApply cancelled.%s\n' "$C_DIM" "$C_RESET"; return 0 ;;
		esac
		;;
	4) agentbot_run_backend workspace --yes "$PWD" ;;
	q|Q|'') return 0 ;;
	*) printf '%sUnknown Workspaces action: %s%s\n' "$C_RED" "$choice" "$C_RESET"; return 2 ;;
	esac
}
