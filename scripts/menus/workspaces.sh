#!/usr/bin/env bash
# shellcheck shell=bash
# shellcheck disable=SC2034

agentbot_menu_workspaces_confirm() {
	local answer=''
	printf '%sApply Agentbot-managed workspace changes?%s [y/N]: ' "$C_YELLOW" "$C_RESET" >/dev/tty
	IFS= read -r answer </dev/tty || answer=n
	case "$answer" in
	y|Y|yes|YES) return 0 ;;
	*) return 1 ;;
	esac
}

agentbot_menu_workspaces_dispatch() {
	local choice="$1" rc=0
	case "$choice" in
	list) agentbot_run_backend workspaces || rc=$? ;;
	preview) agentbot_run_backend resync --all || rc=$? ;;
	apply)
		if agentbot_menu_workspaces_confirm; then
			agentbot_run_backend resync --all --yes || rc=$?
		else
			printf '%sApply cancelled.%s\n' "$C_DIM" "$C_RESET"
		fi
		;;
	setup) agentbot_run_backend workspace --yes "$PWD" || rc=$? ;;
	*) printf 'Unknown Workspaces action: %s\n' "$choice" >&2; rc=2 ;;
	esac
	if ((rc != 0)); then
		printf '%sAction failed (exit %d).%s\n' "$C_RED" "$rc" "$C_RESET" >&2
	fi
	return "$rc"
}

agentbot_menu_workspaces() {
	local choice rc

	MENU_SIMPLE_TITLE='Workspaces'
	MENU_SIMPLE_BREADCRUMB='Agentbot › Workspaces'
	MENU_SIMPLE_LABELS=(
		'List recorded workspaces'
		'Preview resync (all)'
		'Apply resync (all)'
		'Set up current repository'
	)
	MENU_SIMPLE_KEYS=(list preview apply setup)
	MENU_SIMPLE_DESCS=(
		$'Read the private local workspace registry.\nNo repository or state changes are performed.'
		$'Preview managed changes for every enabled workspace.\nNo files are written.'
		$'Apply managed changes to every enabled workspace.\nConfirmation is required before mutation.'
		$'Render and register the current folder or Git root.\nWrites only with the explicit setup action.'
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
		agentbot_menu_workspaces_dispatch "$choice" || rc=$?
		ui_pause
	done
}
