#!/usr/bin/env bash
# shellcheck shell=bash

agentbot_menu_graphify_lib() {
	local cols
	cols="$(agentbot_menu_cols)"
	agentbot_menu_print_header 'Graphify Lib' 'Agentbot › Graphify Lib' "$cols"

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
	printf '  %s%sAgentbot lifecycle boundary%s\e[K\n' "$C_BOLD" "$C_YELLOW" "$C_RESET"
	printf '  %sAgentbot Install and Update run only: graphify install --platform agents%s\e[K\n' "$C_DIM" "$C_RESET"
	printf '  %sThis happens only when the optional Graphify CLI is already installed.%s\e[K\n' "$C_DIM" "$C_RESET"
	printf '  %sDotfiles owns CLI installation; project graphs and platform installers remain manual.%s\e[K\n' "$C_DIM" "$C_RESET"
	printf '  %sDirect agentbot graphify status|setup commands remain available for inspection or repair.%s\e[K\n' "$C_DIM" "$C_RESET"
}
