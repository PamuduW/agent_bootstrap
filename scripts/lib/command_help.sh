#!/usr/bin/env bash
# shellcheck shell=bash
# Width-safe, read-only renderer for the Agentbot command catalog.

_agentbot_help_init_colors() {
	if [[ -n "${NO_COLOR:-}" ]]; then
		AH_RESET=''; AH_BOLD=''; AH_DIM=''; AH_GREEN=''; AH_YELLOW=''; AH_CYAN=''; AH_ORANGE=''
		return 0
	fi
	if [[ -v C_RESET ]]; then
		AH_RESET="${C_RESET:-}"; AH_BOLD="${C_BOLD:-}"; AH_DIM="${C_DIM:-}"
		AH_GREEN="${C_GREEN:-}"; AH_YELLOW="${C_YELLOW:-}"; AH_CYAN="${C_CYAN:-}"; AH_ORANGE="${C_ORANGE:-}"
		return 0
	fi
	if [[ -t 1 || -t 0 || -n "${FORCE_COLOR:-}" ]]; then
		AH_RESET=$'\033[0m'; AH_BOLD=$'\033[1m'; AH_DIM=$'\033[2m'
		AH_GREEN=$'\033[32m'; AH_YELLOW=$'\033[33m'; AH_CYAN=$'\033[36m'; AH_ORANGE=$'\033[38;5;208m'
	else
		AH_RESET=''; AH_BOLD=''; AH_DIM=''; AH_GREEN=''; AH_YELLOW=''; AH_CYAN=''; AH_ORANGE=''
	fi
}

_agentbot_help_fit() {
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

_agentbot_help_wrap_words() {
	local text="$1" width="$2"
	local paragraph word line=''
	local chunk
	((width < 1)) && width=1

	while IFS= read -r paragraph || [[ -n "$paragraph" ]]; do
		if [[ -z "$paragraph" ]]; then
			[[ -n "$line" ]] && { printf '%s\n' "$line"; line=''; }
			printf '\n'
			continue
		fi
		for word in $paragraph; do
			if [[ -n "$line" && ${#line} -lt $width && $(( ${#line} + 1 + ${#word} )) -le $width ]]; then
				line+=" $word"
				continue
			fi
			if [[ -n "$line" ]]; then
				printf '%s\n' "$line"
				line=''
			fi
			while ((${#word} > width)); do
				chunk="${word:0:width}"
				printf '%s\n' "$chunk"
				word="${word:width}"
			done
			line="$word"
		done
	done <<<"$text"
	[[ -n "$line" ]] && printf '%s\n' "$line"
}

_agentbot_help_print_field() {
	local label="$1" value="$2" cols="$3"
	local prefix_width=$((2 + ${#label} + 2)) continuation line
	local continuation
	local -a lines=()
	mapfile -t lines < <(_agentbot_help_wrap_words "$value" "$((cols - prefix_width))")
	((${#lines[@]} > 0)) || lines=('')
	printf '  %s%s%s: %s\n' "$AH_BOLD" "$label" "$AH_RESET" "${lines[0]}"
	continuation="$(printf '%*s' "$prefix_width" '')"
	for line in "${lines[@]:1}"; do
		printf '%s%s\n' "$continuation" "$line"
	done
}

_agentbot_help_print_token_field() {
	local token="$1" value="$2" cols="$3"
	local prefix_width=$((2 + ${#token} + 2)) continuation line
	local continuation
	local -a lines=()
	mapfile -t lines < <(_agentbot_help_wrap_words "$value" "$((cols - prefix_width))")
	((${#lines[@]} > 0)) || lines=('')
	printf '  %s%s%s: %s\n' "$AH_CYAN" "$token" "$AH_RESET" "${lines[0]}"
	continuation="$(printf '%*s' "$prefix_width" '')"
	for line in "${lines[@]:1}"; do
		printf '%s%s\n' "$continuation" "$line"
	done
}

_agentbot_help_print_section() {
	printf '\n  %s%s%s\n' "$AH_BOLD$AH_YELLOW" "$1" "$AH_RESET"
}

_agentbot_help_print_behavior() {
	local behavior="$1"
	case "$behavior" in
	mutating) printf '%s%s%s' "$AH_YELLOW" "$behavior" "$AH_RESET" ;;
	read-only) printf '%s%s%s' "$AH_GREEN" "$behavior" "$AH_RESET" ;;
	*) printf '%s' "$behavior" ;;
	esac
}

_agentbot_help_print_index() {
	local cols="$1" command_w=20 behavior_w=10 available description_w
	local command behavior description command_fit behavior_fit description_fit
	local command_rule behavior_rule description_rule
	local i

	available=$((cols - 8))
	((available < 1)) && available=1
	if ((available < command_w + behavior_w + 1)); then
		command_w=15
		behavior_w=9
	fi
	if ((available < command_w + behavior_w + 1)); then
		command_w=$((available / 2))
		behavior_w=$((available / 4))
		((command_w < 1)) && command_w=1
		((behavior_w < 1)) && behavior_w=1
	fi
	description_w=$((available - command_w - behavior_w))
	((description_w < 1)) && description_w=1

	printf '  %s%-*s | %-*s | %-*s%s\n' \
		"$AH_BOLD" "$command_w" "$(_agentbot_help_fit command "$command_w")" \
		"$behavior_w" "$(_agentbot_help_fit behavior "$behavior_w")" \
		"$description_w" "$(_agentbot_help_fit description "$description_w")" "$AH_RESET"
	command_rule="$(printf '%*s' "$command_w" '')"; command_rule="${command_rule// /-}"
	behavior_rule="$(printf '%*s' "$behavior_w" '')"; behavior_rule="${behavior_rule// /-}"
	description_rule="$(printf '%*s' "$description_w" '')"; description_rule="${description_rule// /-}"
	printf '  %s-+-%s-+-%s\n' "$command_rule" "$behavior_rule" "$description_rule"

	for i in "${!AGENTBOT_COMMAND_KEYS[@]}"; do
		command="${AGENTBOT_COMMAND_KEYS[$i]}"
		behavior="${AGENTBOT_COMMAND_CLASS[$command]}"
		description="${AGENTBOT_COMMAND_SUMMARY[$command]}"
		command_fit="$(_agentbot_help_fit "$command" "$command_w")"
		behavior_fit="$(_agentbot_help_fit "$behavior" "$behavior_w")"
		description_fit="$(_agentbot_help_fit "$description" "$description_w")"
		printf '  %-*s | ' "$command_w" "$command_fit"
		printf '%s' "$(_agentbot_help_print_behavior "$behavior_fit")"
		if ((behavior_w > ${#behavior_fit})); then
			printf '%*s' "$((behavior_w - ${#behavior_fit}))" ''
		fi
		printf ' | %-*s\n' "$description_w" "$description_fit"
	done
}

_agentbot_help_print_option_block() {
	local rows="$1" cols="$2"
	local option description default
	while IFS='|' read -r option description default; do
		[[ -n "$option" ]] || continue
		_agentbot_help_print_token_field "$option" "$description (default: $default)" "$cols"
	done <<<"$rows"
}

_agentbot_help_print_command_block() {
	local key="$1" cols="$2"

	printf '\n  %sCommand: %s%s\n' "$AH_BOLD$AH_ORANGE" "$key" "$AH_RESET"
	_agentbot_help_print_field 'Usage' "${AGENTBOT_COMMAND_USAGE[$key]}" "$cols"
	_agentbot_help_print_field 'Entry point' "${AGENTBOT_COMMAND_ENTRYPOINT[$key]}" "$cols"
	_agentbot_help_print_field 'Purpose' "${AGENTBOT_COMMAND_SUMMARY[$key]}" "$cols"
	printf '  %sOptions%s\n' "$AH_BOLD" "$AH_RESET"
	_agentbot_help_print_option_block "${AGENTBOT_COMMAND_OPTIONS[$key]}" "$cols"
	_agentbot_help_print_field 'Defaults' "${AGENTBOT_COMMAND_DEFAULTS[$key]}" "$cols"
	_agentbot_help_print_field 'Effects' "${AGENTBOT_COMMAND_EFFECTS[$key]}" "$cols"
	_agentbot_help_print_field 'Example' "${AGENTBOT_COMMAND_EXAMPLES[$key]}" "$cols"
	_agentbot_help_print_field 'Related' "${AGENTBOT_COMMAND_RELATED[$key]}" "$cols"
}

_agentbot_help_print_backend_block() {
	local key="$1" cols="$2"

	printf '\n  %sBackend command: %s%s\n' "$AH_BOLD$AH_ORANGE" "$key" "$AH_RESET"
	_agentbot_help_print_field 'Usage' "${AGENTBOT_BACKEND_USAGE[$key]}" "$cols"
	_agentbot_help_print_field 'Purpose' "${AGENTBOT_BACKEND_SUMMARY[$key]}" "$cols"
	printf '  %sOptions%s\n' "$AH_BOLD" "$AH_RESET"
	_agentbot_help_print_option_block "${AGENTBOT_BACKEND_OPTIONS[$key]}" "$cols"
}

_agentbot_help_render_body() {
	local cols="$1" key

	_agentbot_help_print_section 'Command index'
	_agentbot_help_print_index "$cols"
	_agentbot_help_print_section 'Agentbot commands'
	for key in "${AGENTBOT_COMMAND_KEYS[@]}"; do
		_agentbot_help_print_command_block "$key" "$cols"
	done
	_agentbot_help_print_section 'Bootstrap backend commands'
	for key in "${AGENTBOT_BACKEND_COMMAND_KEYS[@]}"; do
		_agentbot_help_print_backend_block "$key" "$cols"
	done
	_agentbot_help_print_section 'Configuration and environment'
	for key in "${AGENTBOT_CONFIG_KEYS[@]}"; do
		_agentbot_help_print_token_field "$key" \
			"${AGENTBOT_CONFIG_DESCRIPTION[$key]} Default: ${AGENTBOT_CONFIG_DEFAULT[$key]} Location: ${AGENTBOT_CONFIG_LOCATION[$key]}" "$cols"
	done
	_agentbot_help_print_section 'System surfaces'
	for key in "${AGENTBOT_SURFACE_KEYS[@]}"; do
		_agentbot_help_print_token_field "$key" \
			"${AGENTBOT_SURFACE_DESCRIPTION[$key]} Location: ${AGENTBOT_SURFACE_LOCATION[$key]}" "$cols"
	done
	_agentbot_help_print_section 'Integrations'
	_agentbot_help_print_field 'Agent surfaces' 'Canonical sources are rendered into global Codex and Claude locations plus selected repository-local AGENTS, Claude, Copilot, and Cursor files.' "$cols"
}

agentbot_command_help_render_menu() {
	local cols="${1:-80}"
	_agentbot_help_init_colors
	agentbot_command_catalog_validate || return 1
	printf '\n  %s%s=== Command Lib ===%s\n' "$AH_BOLD$AH_ORANGE" '' "$AH_RESET"
	printf '  %sAgentbot › Command Lib%s\n\n' "$AH_DIM" "$AH_RESET"
	_agentbot_help_render_body "$cols"
}

agentbot_command_help_render_plain() {
	local cols="${1:-100}"
	_agentbot_help_init_colors
	agentbot_command_catalog_validate || return 1
	printf 'Usage: agentbot <command> [options]\n\n'
	_agentbot_help_render_body "$cols"
	printf '\nSet up the current directory with: agentbot boot\n'
}
