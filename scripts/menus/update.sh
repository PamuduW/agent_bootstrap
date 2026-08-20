#!/usr/bin/env bash
# shellcheck shell=bash

agentbot_menu_update() {
	local rc=0 tty_output="${AGENTBOT_UPDATE_TTY_OUTPUT:-/dev/tty}"
	if [[ -n "${AGENTBOT_TUI:-}" ]]; then
		AGENTBOT_UPDATE_INTERACTIVE=1 "$AGENTBOT_HOME/install.sh" update --interactive >"$tty_output" 2>&1 || rc=$?
	else
		AGENTBOT_UPDATE_INTERACTIVE=1 "$AGENTBOT_HOME/install.sh" update --interactive || rc=$?
	fi
	if ((rc != 0)); then
		if ((rc == 2)); then
			# shellcheck disable=SC2034  # consumed by the sourced parent menu loop
			AGENTBOT_MENU_QUIT=true
			return 0
		fi
		if ((rc == 3)); then
			return 0
		fi
		return "$rc"
	fi
	return 0
}
