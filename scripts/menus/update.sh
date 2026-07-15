#!/usr/bin/env bash
# shellcheck shell=bash

agentbot_menu_update() {
	local answer=''
	if ! "$AGENTBOT_HOME/install.sh" update --dry-run; then
		return 1
	fi
	printf 'Apply the Agentbot reconciliation update? [y/N] ' >/dev/tty
	IFS= read -r answer </dev/tty || answer=n
	case "$answer" in
		y|Y|yes|YES) "$AGENTBOT_HOME/install.sh" update --yes ;;
		*) printf 'Update cancelled.\n'; return 0 ;;
	esac
}
