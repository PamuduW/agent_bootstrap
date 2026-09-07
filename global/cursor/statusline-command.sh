#!/bin/bash
# Managed by Agentbot. Edit global/cursor/statusline-command.sh, then run ./install.sh global.
# Cursor CLI statusLine.
#
# Cursor's contract is aligned with Claude Code's but is not identical, and the
# differences are the whole reason this is a separate script rather than the
# Claude one pointed at a second config:
#
#   * Width arrives as `render_width_chars` in the payload. Claude's script
#     reads COLUMNS, which is not set for this command and would silently
#     produce a statusline sized for an 80-column guess.
#   * There are no rate-limit fields. Claude's script renders two rate-limit
#     segments that would always be empty here.
#   * Cursor adds `vim.mode` and `worktree.name`, which Claude has no equivalent
#     for and which are worth showing when present.

input=$(cat)

if ! command -v jq >/dev/null 2>&1; then
	printf '%s\n' "jq not found - statusline disabled (install jq to restore it)"
	exit 0
fi

# Guard git calls with a timeout: this runs on every conversation update, and a
# hung filesystem must not stall rendering. Cursor kills the process at
# timeoutMs anyway, which would leave the previous line frozen on screen.
GIT_TIMEOUT=()
if command -v timeout >/dev/null 2>&1; then
	GIT_TIMEOUT=(timeout 1)
fi

# One field per line, not @tsv read with IFS. A display name like "Composer 1"
# contains a space, so whitespace splitting shifts every later field -- and tab
# is itself IFS whitespace, so consecutive tabs collapse and absent fields
# (vim and worktree are absent most of the time) shift the rest left. mapfile
# keeps empty fields in place.
mapfile -t _fields < <(
	printf '%s' "$input" | jq -r '
    [
      (.workspace.current_dir // .cwd // ""),
      (.model.display_name // ""),
      (.context_window.used_percentage // ""),
      (.vim.mode // ""),
      (.worktree.name // ""),
      (.render_width_chars // 0)
    ] | .[] | tostring'
)
cwd="${_fields[0]-}"
model_name="${_fields[1]-}"
context_used="${_fields[2]-}"
vim_mode="${_fields[3]-}"
worktree="${_fields[4]-}"
width="${_fields[5]-0}"

# The same palette, separator, segment order and wording as the Claude
# statusline, so both agents read identically. Only the fields Cursor actually
# supplies differ.
RESET=$'\033[0m'
FG_MODEL=$'\033[38;2;217;119;87m'      # Claude orange
FG_DIRECTORY=$'\033[38;2;255;250;247m' # near-white
FG_GIT=$'\033[38;2;230;205;190m'       # warm light tan
FG_CONTEXT=$'\033[38;2;230;205;190m'   # warm light tan
FG_SEPARATOR=$'\033[38;2;120;104;96m'  # dim warm gray

segments=()

if [[ -n "$model_name" ]]; then
	segments+=("${FG_MODEL}${model_name}${RESET}")
fi

if [[ -n "$cwd" ]]; then
	segments+=("${FG_DIRECTORY}${cwd/#$HOME/\~}${RESET}")
fi

if [[ -n "$cwd" && -d "$cwd" ]]; then
	branch="$("${GIT_TIMEOUT[@]}" git -C "$cwd" rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
	if [[ -n "$branch" && "$branch" != HEAD ]]; then
		# " *" for a dirty worktree, the same marker the Claude statusline uses.
		# --no-optional-locks so rendering never blocks a concurrent git command.
		dirty=""
		if [[ -n "$("${GIT_TIMEOUT[@]}" git -C "$cwd" --no-optional-locks status --porcelain 2>/dev/null)" ]]; then
			dirty=" *"
		fi
		segments+=("${FG_GIT}${branch}${dirty}${RESET}")
	fi
fi

if [[ -n "$context_used" && "$context_used" != null ]]; then
	segments+=("${FG_CONTEXT}Context ${context_used%%.*}% used${RESET}")
fi

# Cursor-only, and only when present. A worktree changes where edits land, and
# vim mode changes what a keystroke does; both are worth the space when the
# payload carries them, and Claude has no equivalent to mirror.
if [[ -n "$worktree" ]]; then
	segments+=("${FG_GIT}wt:${worktree}${RESET}")
fi

if [[ -n "$vim_mode" ]]; then
	segments+=("${FG_MODEL}${vim_mode}${RESET}")
fi

if ((${#segments[@]} == 0)); then
	printf 'Cursor\n'
	exit 0
fi

line=""
for segment in "${segments[@]}"; do
	if [[ -n "$line" ]]; then
		line+=" ${FG_SEPARATOR}·${RESET} "
	fi
	line+="$segment"
done
# Claude's line opens with a space; match it so the two sit at the same inset.
line=" $line"

# Trim to the width Cursor reports rather than guessing. Measure without ANSI
# escapes, since those occupy no columns.
if [[ "$width" =~ ^[0-9]+$ ]] && ((width > 0)); then
	plain="$(printf '%s' "$line" | sed $'s/\033\\[[0-9;]*m//g')"
	if ((${#plain} > width)); then
		printf '%s\n' "${plain:0:width-1}…"
		exit 0
	fi
fi

printf '%s\n' "$line"
