#!/usr/bin/env bash
# shellcheck shell=bash
# shellcheck disable=SC2034

agentbot_menu_graphify_confirm() {
	local answer=''
	printf '%sSet up or refresh Graphify Agent Skills for the enabled assistants?%s [y/N]: ' "$C_YELLOW" "$C_RESET" >/dev/tty
	IFS= read -r answer </dev/tty || answer=n
	case "$answer" in
	y|Y|yes|YES) return 0 ;;
	*) return 1 ;;
	esac
}

agentbot_menu_graphify_cli_available() {
	command -v graphify >/dev/null 2>&1
}

agentbot_menu_graphify_commands() {
	local cols
	cols="$(agentbot_menu_cols)"
	agentbot_menu_print_header 'Graphify Commands' 'Agentbot › Graphify › Commands' "$cols"

	printf '  %s%sAssistant skill commands%s\e[K\n' "$C_BOLD" "$C_YELLOW" "$C_RESET"
	printf '  %sClaude/Cursor: /graphify .%s\e[K\n' "$C_CYAN" "$C_RESET"
	printf '  %sCodex: %s%s\e[K\n' "$C_CYAN" "\$graphify ." "$C_RESET"
	printf '  %s/graphify ./docs --update%s\e[K\n' "$C_CYAN" "$C_RESET"
	printf '  %s/graphify . --cluster-only%s\e[K\n' "$C_CYAN" "$C_RESET"
	printf '  %s/graphify . --cluster-only --resolution 1.5%s\e[K\n' "$C_CYAN" "$C_RESET"
	printf '  %s/graphify . --cluster-only --exclude-hubs 99%s\e[K\n' "$C_CYAN" "$C_RESET"
	printf '  %s/graphify . --no-viz%s\e[K\n' "$C_CYAN" "$C_RESET"
	printf '  %s/graphify . --wiki%s\e[K\n' "$C_CYAN" "$C_RESET"
	printf '  %s/graphify query "what connects auth to the database?"%s\e[K\n' "$C_CYAN" "$C_RESET"
	printf '  %s/graphify path "UserService" "DatabasePool"%s\e[K\n' "$C_CYAN" "$C_RESET"
	printf '  %s/graphify explain "RateLimiter"%s\e[K\n' "$C_CYAN" "$C_RESET"
	printf '  %s/graphify add https://arxiv.org/abs/1706.03762%s\e[K\n' "$C_CYAN" "$C_RESET"
	printf '  %s/graphify add <youtube-url>%s\e[K\n' "$C_CYAN" "$C_RESET"
	printf '  %sUse %s instead of /graphify in Codex.%s\e[K\n' "$C_DIM" "\$graphify" "$C_RESET"

	printf '\e[K\n'
	printf '  %s%sShell CLI commands%s\e[K\n' "$C_BOLD" "$C_YELLOW" "$C_RESET"
	printf '  %sgraphify extract .%s\e[K\n' "$C_CYAN" "$C_RESET"
	printf '  %sgraphify update .%s\e[K\n' "$C_CYAN" "$C_RESET"
	printf '  %sgraphify cluster-only . --resolution 1.5%s\e[K\n' "$C_CYAN" "$C_RESET"
	printf '  %sgraphify query "what connects auth to the database?"%s\e[K\n' "$C_CYAN" "$C_RESET"
	printf '  %sgraphify path "UserService" "DatabasePool"%s\e[K\n' "$C_CYAN" "$C_RESET"
	printf '  %sgraphify explain "RateLimiter"%s\e[K\n' "$C_CYAN" "$C_RESET"
	printf '  %sgraphify export callflow-html%s\e[K\n' "$C_CYAN" "$C_RESET"
	printf '  %sgraphify hook install%s\e[K\n' "$C_CYAN" "$C_RESET"
	printf '  %sgraphify merge-graphs a.json b.json --out merged.json%s\e[K\n' "$C_CYAN" "$C_RESET"
	printf '  %sgraphify prs%s\e[K\n' "$C_CYAN" "$C_RESET"
	printf '  %sgraphify prs 42%s\e[K\n' "$C_CYAN" "$C_RESET"
	printf '  %sgraphify prs --triage%s\e[K\n' "$C_CYAN" "$C_RESET"
	printf '  %sgraphify prs --conflicts%s\e[K\n' "$C_CYAN" "$C_RESET"

	printf '\e[K\n'
	printf '  %s%sExplicit platform setup (manual only)%s\e[K\n' "$C_BOLD" "$C_YELLOW" "$C_RESET"
	printf '  %sgraphify claude install%s\e[K\n' "$C_CYAN" "$C_RESET"
	printf '  %sgraphify agents install%s\e[K\n' "$C_CYAN" "$C_RESET"
	printf '  %sgraphify codex install%s\e[K\n' "$C_CYAN" "$C_RESET"
	printf '  %sgraphify cursor install%s\e[K\n' "$C_CYAN" "$C_RESET"
	printf '\e[K\n'
	printf '  %s%sAgentbot setup boundary%s\e[K\n' "$C_BOLD" "$C_YELLOW" "$C_RESET"
	printf '  %sagentbot graphify setup%s\e[K\n' "$C_CYAN" "$C_RESET"
	printf '  %sRuns only: graphify install --platform agents%s\e[K\n' "$C_DIM" "$C_RESET"
	printf '  %sAgentbot does not run graphify claude install or graphify agents install.%s\e[K\n' "$C_DIM" "$C_RESET"
	printf '  %sThose platform-specific always-use commands are explicit actions.%s\e[K\n' "$C_DIM" "$C_RESET"
	printf '  %sThey can mutate project files or hooks, so Agentbot leaves them opt-in.%s\e[K\n' "$C_DIM" "$C_RESET"
}

agentbot_menu_graphify_dispatch() {
	local choice="$1" rc=0
	case "$choice" in
	status) agentbot_run_backend graphify status || rc=$? ;;
	commands) agentbot_menu_graphify_commands || rc=$? ;;
	setup)
		local status_output=''
		status_output="$(agentbot_run_backend graphify status 2>&1)" || rc=$?
		printf '%s\n' "$status_output"
		if ((rc != 0)); then
			return "$rc"
		fi
		if ! agentbot_menu_graphify_cli_available; then
			printf '%sGraphify CLI is not installed. Select Graphify CLI in Dotfiles first, then retry.%s\n' "$C_YELLOW" "$C_RESET"
			return 0
		fi
		if agentbot_menu_graphify_confirm; then
			agentbot_run_backend graphify setup || rc=$?
		else
			printf '%sGraphify setup cancelled.%s\n' "$C_DIM" "$C_RESET"
		fi
		;;
	*) printf 'Unknown Graphify action: %s\n' "$choice" >&2; rc=2 ;;
	esac
	if ((rc != 0)); then
		printf '%sAction failed (exit %d).%s\n' "$C_RED" "$rc" "$C_RESET" >&2
	fi
	return "$rc"
}

agentbot_menu_graphify() {
	local choice rc

	MENU_SIMPLE_TITLE='Graphify'
	MENU_SIMPLE_BREADCRUMB='Agentbot › Graphify'
	MENU_SIMPLE_LABELS=(
		'Check status'
		'Commands'
		'Set up Agent Skills'
	)
	MENU_SIMPLE_KEYS=(status commands setup)
	MENU_SIMPLE_DESCS=(
		$'Read the Graphify CLI, skill, and assistant-link state.\nNo files or external commands are changed.'
		$'Show assistant skill and shell CLI commands from Graphify\'s official reference.\nRead-only; this action only prints guidance.'
		$'Run Graphify\'s generic Agent Skills installer after confirmation.\nThe CLI must already be installed through Dotfiles.'
	)

	while true; do
		if ! menu_simple_run; then
			MENU_SIMPLE_TITLE='Agentbot'
			MENU_SIMPLE_BREADCRUMB='Agentbot'
			return 0
		fi
		choice="${MENU_SIMPLE_RESULT:-}"
		ui_clear
		rc=0
		agentbot_menu_graphify_dispatch "$choice" || rc=$?
		ui_pause
	done
}
