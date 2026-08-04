#!/usr/bin/env bash
# shellcheck shell=bash

agentbot_menu_update() {
	local answer='' rc=0
	if AGENTBOT_UPDATE_INTERACTIVE=1 "$AGENTBOT_HOME/install.sh" update --dry-run; then
		:
	else
		rc=$?
		if ((rc == 2)); then
			printf '%s[info]%s repository pull complete; press %sEnter%s to reload Agentbot from the updated checkout.\n' "$C_CYAN" "$C_RESET" "$C_CYAN" "$C_RESET"
			ui_pause
			agentbot_menu_relaunch
			return $?
		fi
		return "$rc"
	fi
	printf '%sApply the Agentbot update (skills, workspaces, and global outputs)?%s [y/N] ' "$C_YELLOW" "$C_RESET" >/dev/tty
	IFS= read -r answer </dev/tty || answer=n
	case "$answer" in
		y|Y|yes|YES) AGENTBOT_UPDATE_SHOW_STATUS=0 "$AGENTBOT_HOME/install.sh" update --yes ;;
		*) printf '%sUpdate cancelled.%s\n' "$C_DIM" "$C_RESET"; return 0 ;;
	esac
}

agentbot_menu_relaunch() {
	exec "$AGENTBOT_HOME/install.sh"
}
