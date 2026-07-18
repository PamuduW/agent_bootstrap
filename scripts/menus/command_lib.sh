#!/usr/bin/env bash
# shellcheck shell=bash

_agentbot_command_fit() {
	local value="$1" width="$2"
	if ((width <= 0)); then
		return 0
	fi
	if ((${#value} <= width)); then
		printf '%s' "$value"
	elif ((width <= 3)); then
		printf '%s' "${value:0:width}"
	else
		printf '%s...' "${value:0:$((width - 3))}"
	fi
}

_agentbot_command_cell() {
	local value="$1" width="$2" context="${3:-}" color=''
	case "$context" in
	mutating) color="$C_YELLOW" ;;
	read-only) color="$C_GREEN" ;;
	esac
	printf '%s%s%s' "$color" "$value" "$C_RESET"
	if ((width > ${#value})); then
		printf '%*s' "$((width - ${#value}))" ''
	fi
}

agentbot_menu_command_lib() {
	local cols="$(agentbot_menu_cols)" command_w=20 behavior_w=10 available description_w
	local command behavior description command_fit behavior_fit description_fit
	local command_rule behavior_rule description_rule
	local -a commands=(status install update token boot command_lib doctor dotfiles)
	local -a behaviors=(read-only mutating mutating mutating mutating read-only read-only mutating)
	local -a descriptions=(
		'Show Agentbot health and installation state.'
		'Install skills, render outputs, run Doctor, and link agentbot.'
		'Run the repo-first update and reconcile source-owned skills.'
		'Configure the optional shared GitHub API token.'
		'Scaffold AGENTS.md and CLAUDE.md in a target repository.'
		'Show this authoritative command reference.'
		'Validate skills, rendered outputs, links, and configuration.'
		'Open the sibling Dotfiles installer when available.'
	)

	available=$((cols - 8))
	if ((available < command_w + behavior_w + 1)); then
		command_w=15
		behavior_w=9
	fi
	description_w=$((available - command_w - behavior_w))
	((description_w < 1)) && description_w=1

	printf '\n  %s%s=== Command Lib ===%s\e[K\n' "$C_BOLD" "$C_ORANGE" "$C_RESET"
	printf '  %sAgentbot › Command Lib%s\e[K\n\e[K\n' "$C_DIM" "$C_RESET"
	printf '  %s%-*s | %-*s | %-*s%s\n' \
		"$C_BOLD" "$command_w" command "$behavior_w" behavior "$description_w" description "$C_RESET"
	command_rule="$(printf '%*s' "$command_w" '')"; command_rule="${command_rule// /-}"
	behavior_rule="$(printf '%*s' "$behavior_w" '')"; behavior_rule="${behavior_rule// /-}"
	description_rule="$(printf '%*s' "$description_w" '')"; description_rule="${description_rule// /-}"
	printf '  %s-+-%s-+-%s\n' "$command_rule" "$behavior_rule" "$description_rule"

	for i in "${!commands[@]}"; do
		command="${commands[$i]}"
		behavior="${behaviors[$i]}"
		description="${descriptions[$i]}"
		command_fit="$(_agentbot_command_fit "$command" "$command_w")"
		behavior_fit="$(_agentbot_command_fit "$behavior" "$behavior_w")"
		description_fit="$(_agentbot_command_fit "$description" "$description_w")"
		printf '  %-*s | ' "$command_w" "$command_fit"
		_agentbot_command_cell "$behavior_fit" "$behavior_w" "$behavior"
		printf ' | %-*s\n' "$description_w" "$description_fit"
	done
}
