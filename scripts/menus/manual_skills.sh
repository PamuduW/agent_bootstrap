#!/usr/bin/env bash
# shellcheck shell=bash
# shellcheck disable=SC2034  # MENU_CB globals are consumed by menu_checkbox_run.

_agentbot_load_manual_skill_names() {
	local listing name rc=0
	listing="$(mktemp "${TMPDIR:-/tmp}/agentbot-manual-skills.XXXXXX")" || return 1
	agentbot_run_backend skills remove-manual --names0 >"$listing" || rc=$?
	if ((rc != 0)); then
		rm -f -- "$listing"
		return "$rc"
	fi
	AGENTBOT_MANUAL_SKILLS=()
	while IFS= read -r -d '' name; do
		AGENTBOT_MANUAL_SKILLS+=("$name")
	done <"$listing"
	rm -f -- "$listing"
}

agentbot_menu_manual_skills() {
	local index selected_label rc=0
	local -a selected=()
	declare -g -a AGENTBOT_MANUAL_SKILLS=()

	_agentbot_load_manual_skill_names || return $?
	if ((${#AGENTBOT_MANUAL_SKILLS[@]} == 0)); then
		printf 'No removable manual skills found.\n'
		return 0
	fi

	declare -g -a MENU_CB_LABELS=() MENU_CB_STATUS=() MENU_CB_CHECKED=()
	for index in "${!AGENTBOT_MANUAL_SKILLS[@]}"; do
		MENU_CB_LABELS[index]="${AGENTBOT_MANUAL_SKILLS[index]}"
		MENU_CB_STATUS[index]='manual'
		MENU_CB_CHECKED[index]=0
	done
	MENU_CB_TITLE='Remove Manual Skills'
	MENU_CB_BREADCRUMB='Agentbot › Remove Manual Skills'
	MENU_CB_HINT='Up/Down navigate   Space toggle   a all   n none   Enter confirm   q back'
	MENU_CB_COMPACT=true
	unset MENU_CB_TOGGLE_FN MENU_CB_ALL_FN MENU_CB_NONE_FN MENU_CB_DESC_FN
	menu_checkbox_run || return 0

	for index in "${!AGENTBOT_MANUAL_SKILLS[@]}"; do
		if [[ "${MENU_CB_CHECKED[index]}" -eq 1 ]]; then
			selected+=("${AGENTBOT_MANUAL_SKILLS[index]}")
		fi
	done
	if ((${#selected[@]} == 0)); then
		printf 'No manual skills selected.\n'
		return 0
	fi

	selected_label="${selected[0]}"
	for ((index = 1; index < ${#selected[@]}; index++)); do
		selected_label+=", ${selected[index]}"
	done
	tui_confirm \
		"Permanently remove ${#selected[@]} manual skills (${selected_label})?" || return 0
	tui_run_to_output agentbot_run_backend skills remove-manual "${selected[@]}" --yes || rc=$?
	((rc == 0)) || return "$rc"
	tui_run_to_output agentbot_run_backend skills install
}
