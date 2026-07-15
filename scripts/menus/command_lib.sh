#!/usr/bin/env bash
# shellcheck shell=bash

agentbot_menu_command_lib() {
	printf '%s\n' 'Agentbot commands:'
	printf '  status       Read-only health and installation summary.\n'
	printf '  install      Install skills, render outputs, doctor, and link agentbot.\n'
	printf '  update       Reconcile skills and update the repository (future slice).\n'
	printf '  token        Configure the optional GitHub API token.\n'
	printf '  boot         Scaffold AGENTS.md and CLAUDE.md.\n'
	printf '  doctor       Validate the Agentbot installation.\n'
	printf '  dotfiles     Open the sibling Dotfiles installer (future slice).\n'
}
