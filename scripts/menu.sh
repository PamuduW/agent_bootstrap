#!/usr/bin/env bash
# shellcheck shell=bash

_AGENTBOT_MENU_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$_AGENTBOT_MENU_DIR/lib/menu_core.sh"
# shellcheck disable=SC1091
source "$_AGENTBOT_MENU_DIR/lib/command_catalog.sh"
# shellcheck disable=SC1091
source "$_AGENTBOT_MENU_DIR/lib/command_help.sh"
# shellcheck disable=SC1091
source "$_AGENTBOT_MENU_DIR/lib/github_token.sh"
# shellcheck disable=SC1091
source "$_AGENTBOT_MENU_DIR/menus/status.sh"
# shellcheck disable=SC1091
source "$_AGENTBOT_MENU_DIR/menus/install.sh"
# shellcheck disable=SC1091
source "$_AGENTBOT_MENU_DIR/menus/update.sh"
# shellcheck disable=SC1091
source "$_AGENTBOT_MENU_DIR/menus/github_token.sh"
# shellcheck disable=SC1091
source "$_AGENTBOT_MENU_DIR/menus/workspaces.sh"
# shellcheck disable=SC1091
source "$_AGENTBOT_MENU_DIR/menus/command_lib.sh"
# shellcheck disable=SC1091
source "$_AGENTBOT_MENU_DIR/menus/graphify.sh"
# shellcheck disable=SC1091
source "$_AGENTBOT_MENU_DIR/menus/libraries.sh"

# shellcheck disable=SC2034
_agentbot_menu_setup() {
	MENU_SIMPLE_TITLE='Agentbot'
	MENU_SIMPLE_BREADCRUMB='Agentbot'
	MENU_SIMPLE_LABELS=(
		'Check status'
		'Install Agentbot'
		'Update'
		'Configure GitHub token'
		'Workspaces'
		'Libraries'
		'Quit'
	)
	MENU_SIMPLE_KEYS=(status install update token workspaces libraries quit)
	MENU_SIMPLE_DESCS=(
		$'Check the installed Agentbot components and baseline.\nRead-only status; no updates or writes are performed.'
		$'Install skills, refresh rendered outputs, run Doctor, and link agentbot.\nUse the explicit install action when changes are intended.'
		$'Update the repository, reconcile skills, and refresh workspaces plus global outputs.\nA preview and explicit confirmation are required before mutation.'
		$'Configure the optional shared GitHub API token.\nThe token is stored outside this repository.'
		$'List, preview, and resync locally registered workspaces.\nApply actions require explicit confirmation.'
		$'Open the Agentbot and Graphify command reference libraries.\nRead-only command and safety information.'
		$'Exit the Agentbot menu.\nReturn to the calling process.'
	)
}

agentbot_menu_dispatch() {
	local choice="$1" rc=0
	case "$choice" in
	status) agentbot_menu_status || rc=$? ;;
	install) agentbot_menu_install || rc=$? ;;
	update) agentbot_menu_update || rc=$? ;;
	token) agentbot_menu_token || rc=$? ;;
	workspaces) agentbot_menu_workspaces || rc=$? ;;
	libraries) agentbot_menu_libraries || rc=$? ;;
	doctor) agentbot_menu_doctor || rc=$? ;;
	*) printf 'Unknown Agentbot menu action: %s\n' "$choice" >&2; rc=2 ;;
	esac
	if ((rc != 0)); then
		printf '%sAction failed (exit %d).%s\n' "$C_RED" "$rc" "$C_RESET" >&2
	fi
	return "$rc"
}

agentbot_menu_loop() {
	local choice rc
	export AGENTBOT_TUI=1
	while true; do
		_agentbot_menu_setup
		if ! menu_simple_run; then
			return 0
		fi
		choice="${MENU_SIMPLE_RESULT:-}"
		[[ "$choice" == quit ]] && return 0
		ui_clear
		rc=0
		agentbot_menu_dispatch "$choice" || rc=$?
		# Nested menus own their action pauses and return directly to this menu;
		# do not add a stale parent pause after they exit. Failed child launches
		# still pause so their error remains visible before the parent redraws.
		if ((rc != 0)) || [[ "$choice" != workspaces ]]; then
			ui_pause
		fi
	done
}
