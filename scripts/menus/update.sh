#!/usr/bin/env bash
# shellcheck shell=bash

agentbot_menu_update() {
	local answer='' rc=0 tty_output="${AGENTBOT_UPDATE_TTY_OUTPUT:-/dev/tty}"
	if [[ -n "${AGENTBOT_TUI:-}" ]]; then
		AGENTBOT_UPDATE_INTERACTIVE=1 "$AGENTBOT_HOME/install.sh" update --dry-run >"$tty_output" 2>&1 || rc=$?
	else
		AGENTBOT_UPDATE_INTERACTIVE=1 "$AGENTBOT_HOME/install.sh" update --dry-run || rc=$?
	fi
	if ((rc != 0)); then
		if ((rc == 2)); then
			printf '%s[info]%s repository pull complete; Agentbot update stopped. Run Update again when ready.\n' "$C_CYAN" "$C_RESET"
			AGENTBOT_MENU_QUIT=true
			return 0
		fi
		return "$rc"
	fi
	printf '%sApply the Agentbot update (skills, workspaces, and global outputs)?%s [y/N] ' "$C_YELLOW" "$C_RESET" >/dev/tty
	IFS= read -r answer </dev/tty || answer=n
	case "$answer" in
		y|Y|yes|YES)
			if [[ -n "${AGENTBOT_TUI:-}" ]]; then
				AGENTBOT_UPDATE_SHOW_STATUS=0 "$AGENTBOT_HOME/install.sh" update --yes >"$tty_output" 2>&1
			else
				AGENTBOT_UPDATE_SHOW_STATUS=0 "$AGENTBOT_HOME/install.sh" update --yes
			fi
			;;
		*) printf '%sUpdate cancelled.%s\n' "$C_DIM" "$C_RESET"; return 0 ;;
	esac
}
