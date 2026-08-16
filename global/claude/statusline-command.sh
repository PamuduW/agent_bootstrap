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
FG_GIT=$'\033[38;2;230;205;190m'     # warm light tan text

FG_MODEL=$'\033[38;2;217;119;87m'     # Claude orange
FG_DIRECTORY=$'\033[38;2;255;250;247m' # near-white
FG_CONTEXT=$'\033[38;2;230;205;190m'  # warm light tan
FG_LIMIT=$'\033[38;2;230;205;190m'    # warm light tan
FG_SEPARATOR=$'\033[38;2;120;104;96m' # dim warm gray

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
  formatted=$(date -d "@$epoch" '+%b %-d %H:%M' 2>/dev/null) || \
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
IFS='/' read -ra parts <<< "$dir_display"
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

append_segment() {
  local value="$1"
  local color="$2"

  [[ -n "$value" ]] || return 0
  if [[ -n "${statusline-}" ]]; then
    statusline+=" ${FG_SEPARATOR}·${RESET}"
  fi
  statusline+=" ${color}${value}${RESET}"
}

statusline=""
append_segment "$model_display" "$FG_MODEL"
append_segment "$dir_display" "$FG_DIRECTORY"
append_segment "$git_segment" "$FG_GIT"
append_segment "$context_display" "$FG_CONTEXT"
append_segment "$(rate_limit_segment '5h' "$five_hour_used" "$five_hour_reset")" "$FG_LIMIT"
append_segment "$(rate_limit_segment '7d' "$seven_day_used" "$seven_day_reset")" "$FG_LIMIT"

if [[ -z "$statusline" ]]; then
  statusline="Claude Code"
fi
printf '%s\n' "$statusline"
