#!/usr/bin/env bash
# shellcheck shell=bash

agentbot_menu_install() {
	local rc=0 tty_output="${AGENTBOT_INSTALL_TTY_OUTPUT:-/dev/tty}"
	if [[ -n "${AGENTBOT_TUI:-}" ]]; then
		agentbot_run_backend install >"$tty_output" 2>&1 || rc=$?
	else
		agentbot_run_backend install || rc=$?
	fi
	if ((rc == 2)); then
		# shellcheck disable=SC2034  # consumed by the sourced parent menu loop
		AGENTBOT_MENU_QUIT=true
		return 0
	fi
	if ((rc == 3)); then
		return 0
	fi
	return "$rc"
}
