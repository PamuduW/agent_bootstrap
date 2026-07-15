#!/usr/bin/env bash
# shellcheck shell=bash

agentbot_token_config_menu() {
	local action token current='not configured' answer=''
	local file
	file="$(github_token_file)"
	while true; do
		ui_clear
		current='not configured'
		token=''
		github_token_read token
		if [[ -n "$token" ]]; then
			current="$(github_token_fingerprint "$token")"
		elif [[ -e "$file" || -L "$file" ]]; then
			current='saved state is invalid or unsafe'
		fi
		printf '\n  === GitHub Token Config ===\n'
		printf '  Agentbot › GitHub Token Config\n\n'
		printf '  Current: %s\n' "$current"
		printf '  Saved outside this repository: %s\n\n' "$file"
		printf '  Optional: raises public-repository API rate limits.\n'
		printf '  No repository scopes are needed for this workflow.\n\n'
		printf '  [s] Save or replace   [r] Reveal once   [d] Remove   [q] Back\n'
		printf '  Select action: '
		IFS= read -r action </dev/tty || action=q
		case "$action" in
		s|S)
			printf '  Input is visible on screen and may be seen by others.\n  GitHub token (q cancels): '
			IFS= read -r token </dev/tty || token=q
			if [[ "$token" != q && "$token" != Q && -n "$token" ]] && github_token_is_valid "$token"; then
				printf '  Proposed: %s\n  Save this token? [y/N]: ' "$(github_token_fingerprint "$token")"
				IFS= read -r answer </dev/tty || answer=n
				case "$answer" in y|Y|yes|YES) github_token_write "$token" && printf '  GitHub token saved.\n' ;; esac
			else
				printf '  Invalid token; nothing was saved.\n'
			fi
			;;
		r|R)
			if [[ -n "$token" ]]; then
				printf '  WARNING: the full token will be printed once on this terminal.\n  Reveal the full token once? [y/N]: '
				IFS= read -r answer </dev/tty || answer=n
				case "$answer" in y|Y|yes|YES) printf '  %s\n  Press Enter to continue: ' "$token"; IFS= read -r answer </dev/tty || true ;; esac
			else
				printf '  No valid saved token is available to reveal.\n'
			fi
			;;
		d|D)
			if [[ -e "$file" || -L "$file" ]]; then
				printf '  Remove the saved token? [y/N]: '
				IFS= read -r answer </dev/tty || answer=n
				case "$answer" in y|Y|yes|YES) github_token_remove && printf '  Saved token removed.\n' ;; esac
			else
				printf '  No saved token file exists.\n'
			fi
			;;
		q|Q) return 0 ;;
		*) printf '  Invalid choice.\n' ;;
		esac
	done
}

agentbot_menu_token() {
	agentbot_token_config_menu
}
