#!/bin/bash
# Managed by Agentbot. Edit global/claude/statusline-command.sh, then run ./install.sh global.
# Claude Code statusLine
# Mirrors the powerline segment style of ~/.config/starship.toml
# (directory / git branch+status / accent) and adds
# Claude Code session info (model, output style, context usage bar).

input=$(cat)

if ! command -v jq >/dev/null 2>&1; then
	printf '%s\n' "jq not found - statusline disabled (install jq to restore it)"
	exit 0
fi

# Guard git calls with a timeout so a hung/slow filesystem (network mount,
# stale lock) can't stall statusline rendering, since this script runs on
# every render.
GIT_TIMEOUT=()
if command -v timeout >/dev/null 2>&1; then
	GIT_TIMEOUT=(timeout 1)
fi

# Optional Boost savings segment. Boost ships its own status-line component,
# but it rewrites this script in place; Agentbot owns this file, so we call
# `boost status-line` ourselves instead and keep ownership. It reads the same
# payload Claude gives us on stdin and prints nothing when there is nothing to
# report, which is the common case until a noisy command actually gets
# filtered. Costs a process spawn per render -- set AGENTBOT_STATUSLINE_BOOST=0
# to skip it.
BOOST_CMD=""
if [[ "${AGENTBOT_STATUSLINE_BOOST:-1}" != "0" ]]; then
	if command -v boost >/dev/null 2>&1; then
		BOOST_CMD="$(command -v boost)"
	elif [[ -x "$HOME/.local/bin/boost" ]]; then
		BOOST_CMD="$HOME/.local/bin/boost"
	fi
fi

# ---- colors: Claude brand orange accent theme (truecolor 24-bit) ----
# NOTE: these must contain a REAL ESC byte (not the literal 4-char string
# "\033"), because the assembled segments are emitted via `printf '%s' "$var"`
# to keep any literal "%" in the data safe. printf '%s' does NOT interpret
# backslash escapes, so ANSI-C quoting ($'...') is used here to bake the
# actual ESC byte into each variable at assignment time.
#
# Primary accent: Claude coral/clay orange #D97757 (217;119;87).
# Segments use a warm Claude-inspired text palette with dim separators.
RESET=$'\033[0m'
FG_GIT=$'\033[38;2;230;205;190m' # warm light tan text

FG_MODEL=$'\033[38;2;217;119;87m'      # Claude orange
FG_DIRECTORY=$'\033[38;2;255;250;247m' # near-white
FG_CONTEXT=$'\033[38;2;230;205;190m'   # warm light tan
FG_LIMIT=$'\033[38;2;230;205;190m'     # warm light tan
FG_BOOST=$'\033[38;2;143;176;122m'     # muted sage green, savings
FG_SEPARATOR=$'\033[38;2;120;104;96m'  # dim warm gray

# ---- gather Claude Code session data ----
# A single jq call (instead of nine) to cut process-fork overhead, since this
# script runs on every statusline render.
FIELD_SEP=$'\x1f'
if ! parsed="$(
	printf '%s' "$input" | jq -r --arg sep "$FIELD_SEP" '
    [
      (.workspace.current_dir // .cwd // ""),
      (.model.display_name // ""),
      (.output_style.name // ""),
      (.context_window.used_percentage // ""),
      (.context_window.remaining_percentage // ""),
      (.effort.level // ""),
      (.thinking.enabled // false),
      (.rate_limits.five_hour.used_percentage // ""),
      (.rate_limits.five_hour.resets_at // ""),
      (.rate_limits.seven_day.used_percentage // ""),
      (.rate_limits.seven_day.resets_at // "")
    ]
    | map(tostring)
    | join($sep)
  ' 2>/dev/null
)"; then
	printf '%s\n' 'Claude Code'
	exit 0
fi

IFS="$FIELD_SEP" read -r \
	cwd model style used_pct remaining_pct effort_level thinking_enabled \
	five_hour_used five_hour_reset \
	seven_day_used seven_day_reset <<<"$parsed"
[[ "$used_pct" =~ ^[0-9]+([.][0-9]+)?$ ]] || used_pct=""
[[ "$remaining_pct" =~ ^[0-9]+([.][0-9]+)?$ ]] || remaining_pct=""
[[ "$five_hour_used" =~ ^[0-9]+([.][0-9]+)?$ ]] || five_hour_used=""
[[ "$five_hour_reset" =~ ^[0-9]+$ ]] || five_hour_reset=""
[[ "$seven_day_used" =~ ^[0-9]+([.][0-9]+)?$ ]] || seven_day_used=""
[[ "$seven_day_reset" =~ ^[0-9]+$ ]] || seven_day_reset=""

# The model display_name sometimes bakes in a trailing bracket like
# "Opus 4.8 (1M context)". Split that off so we can re-append it AFTER the
# reasoning-level word (e.g. "Opus 4.8 medium (1M context)").
model_bracket=""
model_base="$model"
if [[ "$model" =~ ^(.*)\ (\([^\)]*\))$ ]]; then
	model_base="${BASH_REMATCH[1]}"
	model_bracket="${BASH_REMATCH[2]}"
fi

format_reset_time() {
	local epoch="$1"
	local formatted=""

	[[ "$epoch" =~ ^[0-9]+$ ]] || return 0
	formatted=$(date -d "@$epoch" '+%b %-d %H:%M' 2>/dev/null) ||
		formatted=$(date -u -r "$epoch" '+%b %-d %H:%M' 2>/dev/null) || true
	printf '%s' "$formatted"
}

format_remaining_percentage() {
	awk -v used="$1" 'BEGIN {
    remaining = 100 - used
    if (remaining < 0) remaining = 0
    if (remaining > 100) remaining = 100
    printf "%.0f", remaining
  }'
}

rate_limit_segment() {
	local label="$1"
	local used="$2"
	local reset="$3"
	local remaining
	local reset_display

	[[ -n "$used" ]] || return 0
	remaining=$(format_remaining_percentage "$used")
	printf '%s %s%% left' "$label" "$remaining"
	if [[ -n "$reset" ]]; then
		reset_display=$(format_reset_time "$reset")
		[[ -n "$reset_display" ]] && printf ' (reset %s)' "$reset_display"
	fi
}

# ---- directory segment (truncate to last 3 path components, like starship) ----
dir_display="$cwd"
if [[ "$cwd" == "$HOME" ]]; then
	dir_display="~"
elif [[ "$cwd" == "$HOME/"* ]]; then
	dir_display="~${cwd#"$HOME"}"
fi
IFS='/' read -ra parts <<<"$dir_display"
count=${#parts[@]}
if [ "$count" -gt 3 ]; then
	dir_display="…/$(printf '/%s' "${parts[@]: -3}" | cut -c2-)"
fi

# ---- git branch + status segment ----
git_segment=""
if "${GIT_TIMEOUT[@]}" git -C "$cwd" --no-optional-locks rev-parse --is-inside-work-tree >/dev/null 2>&1; then
	branch=$("${GIT_TIMEOUT[@]}" git -C "$cwd" --no-optional-locks symbolic-ref --short -q HEAD 2>/dev/null || "${GIT_TIMEOUT[@]}" git -C "$cwd" --no-optional-locks rev-parse --short HEAD 2>/dev/null)
	if [ -n "$branch" ]; then
		dirty=""
		if [ -n "$("${GIT_TIMEOUT[@]}" git -C "$cwd" --no-optional-locks status --porcelain 2>/dev/null)" ]; then
			dirty=" *"
		fi
		git_segment="${branch}${dirty}"
	fi
fi

# ---- build ordered output ----
# Keep the statusline compact and readable: model, directory, git, context,
# then the optional subscription windows.
model_display="$model_base"
# Capitalize the effort level for display, except "xhigh" which stays lowercase.
if [ -n "$effort_level" ] && [ "$effort_level" != "null" ]; then
	case "$effort_level" in
	low) effort_display="Low" ;;
	medium) effort_display="Medium" ;;
	high) effort_display="High" ;;
	xhigh) effort_display="xhigh" ;;
	max) effort_display="Max" ;;
	*) effort_display="$effort_level" ;;
	esac
	model_display="${model_display} ${effort_display}"
elif [ "$thinking_enabled" = "true" ]; then
	model_display="${model_display} Thinking"
fi
if [ -n "$model_bracket" ]; then
	model_display="${model_display} ${model_bracket}"
fi
if [ -n "$style" ] && [ "$style" != "default" ]; then
	model_display="${model_display} (${style})"
fi

if [ -n "$used_pct" ]; then
	context_display="Context $(printf '%.0f%%' "$used_pct") used"
elif [ -n "$remaining_pct" ]; then
	context_display="Context $(printf '%.0f%%' "$remaining_pct") left"
else
	context_display=""
fi

boost_segment() {
	local raw

	[[ -n "$BOOST_CMD" ]] || return 0
	# Fail open: a missing, slow, or unhappy Boost must never break or stall the
	# statusline. Its own colors are stripped so the segment matches this palette.
	raw="$(printf '%s' "$input" | "${GIT_TIMEOUT[@]}" "$BOOST_CMD" status-line 2>/dev/null || true)"
	raw="${raw%%$'\n'*}"
	raw="$(printf '%s' "$raw" | sed $'s/\033\\[[0-9;]*m//g')"
	# Trim surrounding whitespace without a subshell.
	raw="${raw#"${raw%%[![:space:]]*}"}"
	raw="${raw%"${raw##*[![:space:]]}"}"
	printf '%s' "$raw"
}

SEGMENT_VALUES=()
SEGMENT_COMPACT_VALUES=()
SEGMENT_COLORS=()
SEGMENT_KEYS=()

append_segment() {
	local value="$1"
	local compact_value="$2"
	local color="$3"
	local key="$4"

	[[ -n "$value" ]] || return 0
	SEGMENT_VALUES+=("$value")
	SEGMENT_COMPACT_VALUES+=("$compact_value")
	SEGMENT_COLORS+=("$color")
	SEGMENT_KEYS+=("$key")
}

segment_range_width() {
	local start="$1"
	local end="$2"
	local -n values="$3"
	local width=1
	local index

	for ((index = start; index < end; index++)); do
		((index > start)) && ((width += 3))
		((width += ${#values[index]}))
	done
	printf '%s' "$width"
}

render_segment_range() {
	local start="$1"
	local end="$2"
	local -n values="$3"
	local line=""
	local index

	for ((index = start; index < end; index++)); do
		if [[ -n "$line" ]]; then
			line+=" ${FG_SEPARATOR}·${RESET}"
		fi
		line+=" ${SEGMENT_COLORS[index]}${values[index]}${RESET}"
	done
	printf '%s' "$line"
}

best_split() {
	local -n values="$1"
	local count="${#values[@]}"
	local split
	local left_width
	local right_width
	local widest
	local best=1
	local best_width=2147483647

	for ((split = 1; split < count; split++)); do
		left_width=$(segment_range_width 0 "$split" "$1")
		right_width=$(segment_range_width "$split" "$count" "$1")
		widest=$left_width
		((right_width > widest)) && widest=$right_width
		if ((widest < best_width)); then
			best="$split"
			best_width="$widest"
		fi
	done
	printf '%s' "$best"
}

truncate_right() {
	local value="$1"
	local cap="$2"

	if ((${#value} <= cap)); then
		printf '%s' "$value"
	elif ((cap <= 1)); then
		printf '…'
	else
		printf '%s…' "${value:0:cap-1}"
	fi
}

truncate_left() {
	local value="$1"
	local cap="$2"

	if ((${#value} <= cap)); then
		printf '%s' "$value"
	elif ((cap <= 1)); then
		printf '…'
	else
		printf '…%s' "${value: -cap+1}"
	fi
}

render_statusline() {
	local count="${#SEGMENT_VALUES[@]}"
	local columns="${COLUMNS-}"
	local full_width
	local split
	local left_width
	local right_width
	local per_line
	local value_cap
	local index
	local value
	local -a compact_values=()

	if ((count == 0)); then
		printf '%s\n' 'Claude Code'
		return 0
	fi

	full_width=$(segment_range_width 0 "$count" SEGMENT_VALUES)
	if [[ ! "$columns" =~ ^[1-9][0-9]*$ ]] || ((full_width <= columns)); then
		render_segment_range 0 "$count" SEGMENT_VALUES
		printf '\n'
		return 0
	fi

	if ((count > 1)); then
		split=$(best_split SEGMENT_VALUES)
		left_width=$(segment_range_width 0 "$split" SEGMENT_VALUES)
		right_width=$(segment_range_width "$split" "$count" SEGMENT_VALUES)
		if ((left_width <= columns && right_width <= columns)); then
			render_segment_range 0 "$split" SEGMENT_VALUES
			printf '\n'
			render_segment_range "$split" "$count" SEGMENT_VALUES
			printf '\n'
			return 0
		fi
	fi

	per_line=$(((count + 1) / 2))
	value_cap=$(((columns - 1 - 3 * (per_line - 1)) / per_line))
	((value_cap < 4)) && value_cap=4
	for ((index = 0; index < count; index++)); do
		value="${SEGMENT_COMPACT_VALUES[index]}"
		if [[ "${SEGMENT_KEYS[index]}" == "directory" ]]; then
			compact_values+=("$(truncate_left "$value" "$value_cap")")
		else
			compact_values+=("$(truncate_right "$value" "$value_cap")")
		fi
	done

	if ((count == 1)); then
		render_segment_range 0 1 compact_values
		printf '\n'
		return 0
	fi

	split=$(best_split compact_values)
	render_segment_range 0 "$split" compact_values
	printf '\n'
	render_segment_range "$split" "$count" compact_values
	printf '\n'
}

context_compact=""
if [[ -n "$used_pct" ]]; then
	context_compact="Ctx $(printf '%.0f%%' "$used_pct")"
elif [[ -n "$remaining_pct" ]]; then
	context_compact="Ctx $(printf '%.0f%%' "$remaining_pct") left"
fi

five_hour_segment="$(rate_limit_segment '5h' "$five_hour_used" "$five_hour_reset")"
seven_day_segment="$(rate_limit_segment '7d' "$seven_day_used" "$seven_day_reset")"
boost_display="$(boost_segment)"

append_segment "$model_display" "$model_display" "$FG_MODEL" model
append_segment "$dir_display" "$dir_display" "$FG_DIRECTORY" directory
append_segment "$git_segment" "$git_segment" "$FG_GIT" git
append_segment "$context_display" "$context_compact" "$FG_CONTEXT" context
append_segment "$boost_display" "$boost_display" "$FG_BOOST" boost
append_segment "$five_hour_segment" "5h $(format_remaining_percentage "$five_hour_used")%" "$FG_LIMIT" five_hour
append_segment "$seven_day_segment" "7d $(format_remaining_percentage "$seven_day_used")%" "$FG_LIMIT" seven_day

render_statusline
