#!/usr/bin/env bash
# shellcheck shell=bash

agentbot_menu_update() {
	local answer='' rc=0
	if AGENTBOT_UPDATE_INTERACTIVE=1 "$AGENTBOT_HOME/install.sh" update --dry-run; then
		:
	else
		rc=$?
		if ((rc == 2)); then
			printf '[info] repository pull complete; press Enter to reload Agentbot from the updated checkout.\n'
			ui_pause
			agentbot_menu_relaunch
			return $?
		fi
		return "$rc"
	fi
	printf 'Apply the Agentbot reconciliation update? [y/N] ' >/dev/tty
	IFS= read -r answer </dev/tty || answer=n
	case "$answer" in
		y|Y|yes|YES) AGENTBOT_UPDATE_SHOW_STATUS=0 "$AGENTBOT_HOME/install.sh" update --yes ;;
		*) printf 'Update cancelled.\n'; return 0 ;;
	esac
}

agentbot_menu_relaunch() {
	exec "$AGENTBOT_HOME/install.sh"
}
