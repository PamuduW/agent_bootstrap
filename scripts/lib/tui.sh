#!/usr/bin/env bash
# shellcheck shell=bash

# shellcheck disable=SC2034  # palette globals are consumed by sourced menu modules
tui_init_colors() {
	if [[ -n "${NO_COLOR:-}" ]]; then
		C_RESET=''; C_BOLD=''; C_DIM=''; C_WHITE=''; C_GREEN=''; C_YELLOW=''; C_CYAN=''; C_ORANGE=''; C_RED=''
		return 0
	fi
	C_RESET=$'\e[0m'; C_BOLD=$'\e[1m'; C_DIM=$'\e[2m'; C_WHITE=$'\e[37m'
	C_GREEN=$'\e[32m'; C_YELLOW=$'\e[33m'; C_CYAN=$'\e[36m'
	C_ORANGE=$'\e[38;5;208m'; C_RED=$'\e[31m'
}

tui_init_colors

tui_cols() {
	local cols="${AGENTBOT_MENU_COLS:-}"
	if [[ -z "$cols" && ( -t 0 || -t 1 ) ]]; then
		cols="$(stty size </dev/tty 2>/dev/null || true)"
		cols="${cols##* }"
	fi
	[[ "$cols" =~ ^[0-9]+$ ]] || cols=80
	((cols < 20)) && cols=20
	printf '%s\n' "$cols"
}

tui_fit() {
	local text="$1" width="$2"
	((width < 1)) && width=1
	if ((${#text} > width)); then
		if ((width > 3)); then printf '%s...' "${text:0:width-3}"; else printf '%s' "${text:0:width}"; fi
	else
		printf '%s' "$text"
	fi
}

tui_clear() {
	if [[ -t 0 ]]; then
		tput clear 2>/dev/null || printf '\033[2J\033[H' >/dev/tty
	fi
}

tui_header() {
	local title="$1" breadcrumb="${2:-}" cols="${3:-$(tui_cols)}"
	printf '  %s%s%s%s\e[K\n' "$C_BOLD" "$C_ORANGE" "$(tui_fit "=== ${title} ===" "$((cols - 2))")" "$C_RESET"
	if [[ -n "$breadcrumb" ]]; then
		printf '  %s%s%s\e[K\n' "$C_DIM" "$(tui_fit "$breadcrumb" "$((cols - 2))")" "$C_RESET"
	fi
	printf '\e[K\n'
}

tui_section() {
	local label="$1" cols="${2:-$(tui_cols)}"
	printf '  %s%s%s%s\e[K\n' "$C_BOLD" "$C_YELLOW" "$(tui_fit "$label" "$((cols - 2))")" "$C_RESET"
}

tui_shortcuts() {
	local key label first=true
	(($# > 0 && $# % 2 == 0)) || return 2
	while (($#)); do
		key="$1"; label="$2"; shift 2
		[[ "$first" == true ]] || printf '   '
		printf '%s%s%s %s' "$C_CYAN" "$key" "$C_RESET" "$label"
		first=false
	done
}

tui_color_input_hint() {
	local hint="$1" cyan="${C_CYAN:-}" reset="${C_RESET:-}" dim="${C_DIM:-}"
	local key_start="${reset}${cyan}" key_end="${reset}${dim}"
	hint="${hint//Up\/Down/${key_start}Up\/Down${key_end}}"
	hint="${hint//Enter confirm/${key_start}Enter${key_end} confirm}"
	hint="${hint//   q back/   ${key_start}q${key_end} back}"
	printf '%s' "$hint"
}

tui_confirm() {
	local prompt="$1" answer='' input="${AGENTBOT_TUI_INPUT:-/dev/tty}" output="${AGENTBOT_TUI_OUTPUT:-/dev/tty}"
	if [[ -n "${AGENTBOT_TUI_IN_FD:-}" && -n "${AGENTBOT_TUI_OUT_FD:-}" ]]; then
		printf '%s [y/N]: ' "$prompt" >&"$AGENTBOT_TUI_OUT_FD"
		IFS= read -r answer <&"$AGENTBOT_TUI_IN_FD" || true
	else
		printf '%s [y/N]: ' "$prompt" >"$output"
		IFS= read -r answer <"$input" || true
	fi
	case "$answer" in y|Y|yes|YES) return 0 ;; *) return 1 ;; esac
}

tui_pause() {
	local ignored='' input="${AGENTBOT_TUI_INPUT:-/dev/tty}" output="${AGENTBOT_TUI_OUTPUT:-/dev/tty}"
	if [[ -n "${AGENTBOT_TUI_IN_FD:-}" && -n "${AGENTBOT_TUI_OUT_FD:-}" ]]; then
		printf '\nPress %sEnter%s to continue: ' "$C_CYAN" "$C_RESET" >&"$AGENTBOT_TUI_OUT_FD"
		IFS= read -r ignored <&"$AGENTBOT_TUI_IN_FD" || true
	else
		printf '\n' >"$output"
		printf 'Press %sEnter%s to continue: ' "$C_CYAN" "$C_RESET" >>"$output"
		IFS= read -r ignored <"$input" || true
	fi
}

tui_wait_back() {
	local ignored='' input="${AGENTBOT_TUI_INPUT:-/dev/tty}" output="${AGENTBOT_TUI_OUTPUT:-/dev/tty}"
	printf '\n' >"$output"
	printf '%sq%s or %sEnter%s to return: ' "$C_CYAN" "$C_RESET" "$C_CYAN" "$C_RESET" >>"$output"
	IFS= read -r ignored <"$input" || true
}

tui_table_widths() {
	local cols="$1" available
	available=$((cols - 11))
	((available < 4)) && available=4
	TUI_TABLE_W1=$((available * 20 / 100))
	TUI_TABLE_W2=$((available * 28 / 100))
	TUI_TABLE_W3=$((available * 27 / 100))
	TUI_TABLE_W4=$((available - TUI_TABLE_W1 - TUI_TABLE_W2 - TUI_TABLE_W3))
	((TUI_TABLE_W1 < 1)) && TUI_TABLE_W1=1
	((TUI_TABLE_W2 < 1)) && TUI_TABLE_W2=1
	((TUI_TABLE_W3 < 1)) && TUI_TABLE_W3=1
	((TUI_TABLE_W4 < 1)) && TUI_TABLE_W4=1
}

tui_table_cell() {
	local text="$1" width="$2" color="${3:-}" fit padding
	fit="$(tui_fit "$text" "$width")"
	printf '%s%s%s' "$color" "$fit" "${color:+$C_RESET}"
	padding=$((width - ${#fit}))
	((padding > 0)) && printf '%*s' "$padding" ''
	return 0
}

tui_table_rule() {
	local width="$1" rule
	printf -v rule '%*s' "$width" ''
	printf '%s' "${rule// /-}"
}

tui_table_header() {
	local cols="$1" h1="$2" h2="$3" h3="$4" h4="$5"
	tui_table_widths "$cols"
	printf '  %s%s' "$C_BOLD" "$C_WHITE"
	tui_table_cell "$h1" "$TUI_TABLE_W1"
	printf ' | '; tui_table_cell "$h2" "$TUI_TABLE_W2"
	printf ' | '; tui_table_cell "$h3" "$TUI_TABLE_W3"
	printf ' | '; tui_table_cell "$h4" "$TUI_TABLE_W4"
	printf '%s\n' "$C_RESET"
	printf '  %s%s-+-%s-+-%s-+-%s%s\n' "$C_DIM" \
		"$(tui_table_rule "$TUI_TABLE_W1")" "$(tui_table_rule "$TUI_TABLE_W2")" \
		"$(tui_table_rule "$TUI_TABLE_W3")" "$(tui_table_rule "$TUI_TABLE_W4")" "$C_RESET"
}

tui_table_row() {
	local cols="$1" t1="$2" t2="$3" t3="$4" t4="$5" color3="${6:-}" color4="${7:-}"
	tui_table_widths "$cols"
	printf '  '; tui_table_cell "$t1" "$TUI_TABLE_W1"
	printf ' | '; tui_table_cell "$t2" "$TUI_TABLE_W2"
	printf ' | '; tui_table_cell "$t3" "$TUI_TABLE_W3" "$color3"
	printf ' | '; tui_table_cell "$t4" "$TUI_TABLE_W4" "$color4"
	printf '\n'
}

tui_menu_desc_lines() {
	local cursor="$1" lines=0 line desc
	desc="${MENU_SIMPLE_DESCS[$cursor]:-}"
	while IFS= read -r line; do lines=$((lines + 1)); done <<<"$desc"
	printf '%s\n' "$lines"
}

tui_menu_lines() {
	local cursor="${1:-0}" desc_lines
	desc_lines="$(tui_menu_desc_lines "$cursor")"
	printf '%s\n' $((1 + 2 + 2 + ${#MENU_SIMPLE_LABELS[@]} + 1 + desc_lines))
}

tui_redraw_up() { printf '\033[%dA' "$1"; }

tui_menu_draw() {
	local cursor="$1" cols="${2:-80}" i prefix row desc
	local title="${MENU_SIMPLE_TITLE:-Agentbot}" breadcrumb="${MENU_SIMPLE_BREADCRUMB:-Agentbot}"
	tui_header "$title" "$breadcrumb" "$cols"
	printf '  %s%s%s\e[K\n\e[K\n' "$C_DIM" "$(tui_color_input_hint "$(tui_fit 'Up/Down navigate   Enter confirm   q back' "$((cols - 2))")")" "$C_RESET"
	for i in "${!MENU_SIMPLE_LABELS[@]}"; do
		prefix=' '; [[ "$i" -eq "$cursor" ]] && prefix='>'
		row="${prefix} $((i + 1)). ${MENU_SIMPLE_LABELS[$i]}"
		if [[ "$i" -eq "$cursor" ]]; then
			printf '  %s%s%s\e[K\n' "$C_BOLD" "$(tui_fit "$row" "$((cols - 2))")" "$C_RESET"
		else
			printf '  %s\e[K\n' "$(tui_fit "$row" "$((cols - 2))")"
		fi
	done
	printf '\e[K\n'
	desc="${MENU_SIMPLE_DESCS[$cursor]:-}"
	while IFS= read -r line; do printf '  %s%s%s\e[K\n' "$C_DIM" "$(tui_fit "$line" "$((cols - 2))")" "$C_RESET"; done <<<"$desc"
}

menu_simple_run() {
	local cursor=0 cols key seq next menu_lines next_lines
	cols="$(tui_cols)"; menu_lines="$(tui_menu_lines "$cursor")"
	tui_clear; tui_menu_draw "$cursor" "$cols" >/dev/tty
	while true; do
		IFS= read -rsn1 key </dev/tty || { MENU_SIMPLE_RESULT=''; return 1; }
		case "$key" in
		$'\e')
			seq=''; while IFS= read -rsn1 -t 0.01 next </dev/tty; do seq+="$next"; done
			case "$seq" in '[A'|'OA') ((cursor > 0)) && cursor=$((cursor - 1)) ;; '[B'|'OB') ((cursor + 1 < ${#MENU_SIMPLE_LABELS[@]})) && cursor=$((cursor + 1)) ;; esac
			;;
		q|Q|$'\003') MENU_SIMPLE_RESULT=''; return 1 ;;
		'') MENU_SIMPLE_RESULT="${MENU_SIMPLE_KEYS[$cursor]}"; return 0 ;;
		esac
		next_lines="$(tui_menu_lines "$cursor")"
		if [[ "$next_lines" == "$menu_lines" ]]; then tui_redraw_up "$menu_lines" >/dev/tty; else tui_clear; fi
		menu_lines="$next_lines"; tui_menu_draw "$cursor" "$cols" >/dev/tty
	done
}
