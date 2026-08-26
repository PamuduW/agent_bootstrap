#!/usr/bin/env bash
# shellcheck shell=bash

agentbot_menu_update() {
	local rc=0
	if [[ -n "${AGENTBOT_TUI:-}" ]]; then
		tui_refresh_tty_seam
		tui_run_to_output env \
			AGENTBOT_UPDATE_INTERACTIVE=1 \
			AGENTBOT_UPDATE_TTY_INPUT="$DOTFILES_TTY_INPUT" \
			AGENTBOT_UPDATE_TTY_OUTPUT="$DOTFILES_TTY_OUTPUT" \
			AGENTBOT_UPDATE_TTY_IN_FD="$DOTFILES_TTY_IN_FD" \
			AGENTBOT_UPDATE_TTY_OUT_FD="$DOTFILES_TTY_OUT_FD" \
			"$AGENTBOT_HOME/install.sh" update --interactive || rc=$?
	else
		AGENTBOT_UPDATE_INTERACTIVE=1 "$AGENTBOT_HOME/install.sh" update --interactive || rc=$?
	fi
	if ((rc != 0)); then
		if ((rc == 3)); then
			return 0
		fi
		return "$rc"
	fi
	return 0
}
