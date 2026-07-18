#!/usr/bin/env bash
# shellcheck shell=bash

agentbot_menu_init_colors() {
	if [[ -n "${NO_COLOR:-}" ]]; then
		C_RESET=''; C_BOLD=''; C_DIM=''; C_GREEN=''; C_YELLOW=''; C_CYAN=''; C_ORANGE=''; C_RED=''
		return 0
	fi
	C_RESET=$'\e[0m'; C_BOLD=$'\e[1m'; C_DIM=$'\e[2m'
	C_GREEN=$'\e[32m'; C_YELLOW=$'\e[33m'; C_CYAN=$'\e[36m'
	C_ORANGE=$'\e[38;5;208m'; C_RED=$'\e[31m'
}

agentbot_menu_init_colors

ui_clear() {
	if [[ -t 0 ]]; then
		tput clear 2>/dev/null || printf '\033[2J\033[H' >/dev/tty
	fi
}

ui_pause() {
	local ignored=''
	if [[ -t 0 || -e /dev/tty ]]; then
		printf '\n' >/dev/tty
		printf 'Press %sEnter%s to continue: ' "$C_CYAN" "$C_RESET" >/dev/tty
		# shellcheck disable=SC2034
		IFS= read -r ignored </dev/tty || true
	fi
}

agentbot_menu_color_input_hint() {
	local hint="$1"
	local cyan="${C_CYAN:-}" reset="${C_RESET:-}" dim="${C_DIM:-}"
	local key_start="${reset}${cyan}" key_end="${reset}${dim}"
	hint="${hint//Up\/Down/${key_start}Up\/Down${key_end}}"
	hint="${hint//Enter confirm/${key_start}Enter${key_end} confirm}"
	hint="${hint//   q back/   ${key_start}q${key_end} back}"
	printf '%s' "$hint"
}

agentbot_menu_print_header() {
	local title="$1" breadcrumb="${2:-}" cols="${3:-80}"
	printf '  %s%s%s\e[K\n' "$C_BOLD$C_ORANGE" "$(agentbot_menu_fit "=== ${title} ===" "$cols")" "$C_RESET"
	if [[ -n "$breadcrumb" ]]; then
		printf '  %s%s%s\e[K\n' "$C_DIM" "$(agentbot_menu_fit "$breadcrumb" "$cols")" "$C_RESET"
	fi
	printf '\e[K\n'
}

agentbot_menu_cols() {
	local cols="${AGENTBOT_MENU_COLS:-}"
	if [[ -z "$cols" && ( -t 0 || -t 1 ) ]]; then
		cols="$(stty size </dev/tty 2>/dev/null || true)"
		cols="${cols##* }"
	fi
	[[ "$cols" =~ ^[0-9]+$ ]] || cols=80
	((cols < 20)) && cols=20
	printf '%s\n' "$cols"
}

agentbot_menu_fit() {
	local text="$1" cols="$2" max
	max=$((cols - 1))
	((max < 1)) && max=1
	if ((${#text} > max)); then
		if ((max > 3)); then printf '%s...' "${text:0:max-3}"; else printf '%s' "${text:0:max}"; fi
	else
		printf '%s' "$text"
	fi
}

agentbot_menu_desc_lines() {
	local cursor="$1" lines=0 line
	local desc="${MENU_SIMPLE_DESCS[$cursor]:-}"
	while IFS= read -r line; do
		lines=$((lines + 1))
	done <<<"$desc"
	printf '%s\n' "$lines"
}

agentbot_menu_lines() {
	local cursor="${1:-0}" desc_lines
	desc_lines="$(agentbot_menu_desc_lines "$cursor")"
	# Title, breadcrumb+spacer, hint+spacer, items, footer spacer, description.
	printf '%s\n' $((1 + 2 + 2 + ${#MENU_SIMPLE_LABELS[@]} + 1 + desc_lines))
}

agentbot_menu_redraw_up() {
	printf '\033[%dA' "$1"
}

agentbot_menu_draw() {
	local cursor="$1" cols="${2:-80}" i prefix row desc
	local title="${MENU_SIMPLE_TITLE:-Agentbot}" breadcrumb="${MENU_SIMPLE_BREADCRUMB:-Agentbot}"

	printf '  %s%s%s\e[K\n' "$C_BOLD$C_ORANGE" "$(agentbot_menu_fit "=== ${title} ===" "$cols")" "$C_RESET"
	printf '  %s%s%s\e[K\n\e[K\n' "$C_DIM" "$(agentbot_menu_fit "$breadcrumb" "$cols")" "$C_RESET"
	printf '  %s%s%s\e[K\n\e[K\n' "$C_DIM" "$(agentbot_menu_color_input_hint "$(agentbot_menu_fit 'Up/Down navigate   Enter confirm   q back' "$cols")")" "$C_RESET"

	for i in "${!MENU_SIMPLE_LABELS[@]}"; do
		prefix=' '
		[[ "$i" -eq "$cursor" ]] && prefix='>'
		row="${prefix} $((i + 1)). ${MENU_SIMPLE_LABELS[$i]}"
		if [[ "$i" -eq "$cursor" ]]; then
			printf '  %s%s%s\e[K\n' "$C_BOLD" "$(agentbot_menu_fit "$row" "$cols")" "$C_RESET"
		else
			printf '  %s\e[K\n' "$(agentbot_menu_fit "$row" "$cols")"
		fi
	done

	printf '\e[K\n'
	desc="${MENU_SIMPLE_DESCS[$cursor]:-}"
	while IFS= read -r line; do
		printf '  %s%s%s\e[K\n' "$C_DIM" "$(agentbot_menu_fit "$line" "$cols")" "$C_RESET"
	done <<<"$desc"
}

menu_simple_run() {
	local cursor=0 cols key seq next menu_lines next_lines
	cols="$(agentbot_menu_cols)"
	menu_lines="$(agentbot_menu_lines "$cursor")"
	ui_clear
	agentbot_menu_draw "$cursor" "$cols" >/dev/tty
	while true; do
		IFS= read -rsn1 key </dev/tty || { MENU_SIMPLE_RESULT=''; return 1; }
		case "$key" in
		$'\e')
			seq=''
			while IFS= read -rsn1 -t 0.01 next </dev/tty; do seq+="$next"; done
			case "$seq" in '[A'|'OA') ((cursor > 0)) && cursor=$((cursor - 1)) ;; '[B'|'OB') ((cursor + 1 < ${#MENU_SIMPLE_LABELS[@]})) && cursor=$((cursor + 1)) ;; esac
			;;
		q|Q|$'\003') MENU_SIMPLE_RESULT=''; return 1 ;;
		'')
			# shellcheck disable=SC2034
			MENU_SIMPLE_RESULT="${MENU_SIMPLE_KEYS[$cursor]}"
			return 0
			;;
		esac
		next_lines="$(agentbot_menu_lines "$cursor")"
		if [[ "$next_lines" == "$menu_lines" ]]; then
			agentbot_menu_redraw_up "$menu_lines" >/dev/tty
		else
			ui_clear
		fi
		menu_lines="$next_lines"
		agentbot_menu_draw "$cursor" "$cols" >/dev/tty
	done
}
