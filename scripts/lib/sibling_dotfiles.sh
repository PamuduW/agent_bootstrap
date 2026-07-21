#!/usr/bin/env bash
# shellcheck shell=bash

sibling_dotfiles_home() {
	if [[ -n "${DOTFILES_HOME:-}" ]]; then
		printf '%s\n' "$DOTFILES_HOME"
	else
		printf '%s\n' "$(dirname "$AGENTBOT_HOME")/dotfiles"
	fi
}

sibling_dotfiles_repo_url() {
	printf '%s\n' "${DOTFILES_REPO_URL:-git@github.com:PamuduW/dotfiles.git}"
}

sibling_dotfiles_origin_allowed() {
	local origin="$1" rewrite_rules="${2:-}"
	local key target prefix matched_prefix='' matched_target='' resolved

	case "$origin" in
	*://*@*) return 1 ;;
	git@github.com:PamuduW/dotfiles.git|https://github.com/PamuduW/dotfiles.git)
		return 0
		;;
	esac

	while IFS=$' \t' read -r key target; do
		[[ "$key" == url.*.insteadof ]] || continue
		prefix="${key#url.}"
		prefix="${prefix%.insteadof}"
		[[ -n "$prefix" ]] || continue
		case "$origin" in
			"$prefix"*)
				if ((${#prefix} > ${#matched_prefix})); then
					matched_prefix="$prefix"
					matched_target="$target"
				fi
				;;
		esac
	done <<<"$rewrite_rules"

	[[ -n "$matched_prefix" ]] || return 1
	resolved="${matched_target}${origin#"$matched_prefix"}"
	case "$resolved" in
	git@github.com:PamuduW/dotfiles.git|https://github.com/PamuduW/dotfiles.git)
		return 0
		;;
	*) return 1 ;;
	esac
}

sibling_dotfiles_validate() {
	local home="$1" origin
	[[ -x "$home/install.sh" ]] || {
		printf 'Dotfiles installer is missing: %s/install.sh\n' "$home" >&2
		return 1
	}
	origin="$(git -C "$home" remote get-url origin 2>/dev/null)" || {
		printf 'Dotfiles origin is unavailable: %s\n' "$home" >&2
		return 1
	}
	if ! sibling_dotfiles_origin_allowed "$origin"; then
		local rewrite_rules
		rewrite_rules="$(git config --global --get-regexp '^url\..*\.insteadof$' 2>/dev/null || true)"
		sibling_dotfiles_origin_allowed "$origin" "$rewrite_rules" || {
			printf 'Dotfiles origin is not allowlisted: %s\n' "$origin" >&2
			return 1
		}
	fi
}

sibling_dotfiles_confirm() {
	local answer=''
	if [[ -n "${SIBLING_DOTFILES_CONFIRM:-}" ]]; then
		[[ "$SIBLING_DOTFILES_CONFIRM" == yes ]]
		return
	fi
	printf '  Clone Dotfiles from %s to %s? [y/N]: ' "$(sibling_dotfiles_repo_url)" "$(sibling_dotfiles_home)" >/dev/tty
	IFS= read -r answer </dev/tty || answer=n
	case "$answer" in y|Y|yes|YES) return 0 ;; esac
	return 1
}

sibling_dotfiles_launch() {
	local home url
	home="$(sibling_dotfiles_home)"
	url="$(sibling_dotfiles_repo_url)"
	if [[ ! -e "$home/install.sh" ]]; then
		printf 'Dotfiles is not cloned at %s.\n' "$home"
		sibling_dotfiles_confirm || {
			printf 'Dotfiles launch cancelled.\n'
			return 0
		}
		git clone "$url" "$home" || {
			printf 'Dotfiles clone failed.\n' >&2
			return 1
		}
	fi
	sibling_dotfiles_validate "$home" || return 1
	(
		cd "$home" || exit 1
		SETUP_CALLER=agentbot ./install.sh
	)
}
