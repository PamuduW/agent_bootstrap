#!/usr/bin/env bash
# shellcheck shell=bash

agentbot_menu_install() {
	local rc=0
	if [[ -n "${AGENTBOT_TUI:-}" ]]; then
		tui_run_to_output agentbot_run_backend install || rc=$?
	else
		agentbot_run_backend install || rc=$?
	fi
	if ((rc == 3)); then
		return 0
	fi
	return "$rc"
}
