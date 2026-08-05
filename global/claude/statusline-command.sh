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
# Other segment backgrounds are warm-tinted dark browns (instead of the
# previous cool blue/slate) so the whole bar reads as one cohesive palette.
RESET=$'\033[0m'
FG_LIGHT=$'\033[38;2;255;250;247m'   # near-white text on the orange bg
BG_DIR=$'\033[48;2;217;119;87m'      # #D97757 Claude orange
FG_GIT=$'\033[38;2;230;205;190m'     # warm light tan text
BG_GIT=$'\033[48;2;61;45;38m'        # warm dark brown (#3D2D26)
FG_INFO=$'\033[38;2;230;205;190m'    # warm light tan text
BG_INFO=$'\033[48;2;46;36;32m'       # warm darker brown (#2E2420)

FG_BAR_FULL=$'\033[38;2;217;119;87m' # Claude orange, filled portion
FG_BAR_EMPTY=$'\033[38;2;120;104;96m' # dim warm gray, unfilled portion

SEP_DIR_TO_GIT=$'\033[38;2;217;119;87m\033[48;2;61;45;38m'
SEP_GIT_TO_INFO=$'\033[38;2;61;45;38m\033[48;2;46;36;32m'
SEP_END=$'\033[38;2;46;36;32m'

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
      (.context_window.total_input_tokens // ""),
      (.context_window.context_window_size // ""),
      (.effort.level // ""),
      (.thinking.enabled // false)
    ]
    | map(tostring)
    | join($sep)
  ' 2>/dev/null
)"; then
  printf '%s\n' 'Claude Code'
  exit 0
fi

IFS="$FIELD_SEP" read -r cwd model style used_pct used_tokens total_tokens effort_level thinking_enabled <<<"$parsed"
[[ "$used_pct" =~ ^[0-9]+([.][0-9]+)?$ ]] || used_pct=""
[[ "$used_tokens" =~ ^[0-9]+$ ]] || used_tokens=""
[[ "$total_tokens" =~ ^[0-9]+$ ]] || total_tokens=""

# The model display_name sometimes bakes in a trailing bracket like
# "Opus 4.8 (1M context)". Split that off so we can re-append it AFTER the
# reasoning-level word (e.g. "Opus 4.8 medium (1M context)").
model_bracket=""
model_base="$model"
if [[ "$model" =~ ^(.*)\ (\([^\)]*\))$ ]]; then
  model_base="${BASH_REMATCH[1]}"
  model_bracket="${BASH_REMATCH[2]}"
fi

# ---- format large numbers with k/m abbreviations (e.g. 25500 -> 25.5k, 1000000 -> 1m) ----
format_tokens() {
  awk -v n="$1" 'BEGIN{
    if (n >= 1000000) { printf "%.1fm", n/1000000; exit }
    if (n >= 1000) {
      k = n/1000;
      # k rounds to 1000.0 at 1 decimal (e.g. n=999999) -> bump to the m unit
      # instead of printing "1000k".
      if (k >= 999.95) printf "%.1fm", n/1000000;
      else printf "%.1fk", k;
      exit
    }
    printf "%d", n;
  }' | sed -E 's/\.0([km])$/\1/'
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
    git_segment=" ${branch}${dirty} "
  fi
fi

# ---- context usage progress bar (braille/dotted style) ----
# Compact form to avoid line-width truncation, e.g.: ⣿⣶⣤⣀⠄ 30.4k/1m 3%
# NOTE: bar_width is kept small (6) and the bar string is built/printed as raw
# characters only -- no character-count/padding logic is applied to it, so the
# fact that braille glyphs and ANSI color codes are multi-byte does not risk
# misaligning anything here.
bar_display=""
if [ -n "$used_pct" ] && [ "$used_pct" != "null" ]; then
  bar_width=6
  # transitional levels from "almost full" to "almost empty"
  levels=("⣷" "⣶" "⣦" "⣤" "⣄" "⣀" "⠆" "⠂")
  empty_char="⠄"
  full_char="⣿"

  filled=$(awk -v p="$used_pct" -v w="$bar_width" 'BEGIN{v=p/100*w; if(v<0)v=0; if(v>w)v=w; printf "%d", int(v)}')
  # idx counts DOWN as the partial cell fills (f: 0=empty..1=full), since
  # levels[] is ordered from "almost full" (0) to "almost empty" (7).
  frac_idx=$(awk -v p="$used_pct" -v w="$bar_width" 'BEGIN{v=p/100*w; if(v<0)v=0; if(v>w)v=w; f=v-int(v); idx=7-int(f*8); if(idx<0)idx=0; if(idx>7)idx=7; printf "%d", idx}')

  filled_part=""
  for ((i=0; i<filled; i++)); do filled_part+="$full_char"; done

  used_slots=$filled
  if [ "$filled" -lt "$bar_width" ]; then
    filled_part+="${levels[$frac_idx]}"
    used_slots=$((filled + 1))
  fi

  empty_part=""
  for ((i=used_slots; i<bar_width; i++)); do empty_part+="$empty_char"; done

  pct_display=$(printf '%.0f%%' "$used_pct")

  tokens_display=""
  if [ -n "$used_tokens" ] && [ "$used_tokens" != "null" ] && [ -n "$total_tokens" ] && [ "$total_tokens" != "null" ]; then
    tokens_display="$(format_tokens "$used_tokens")/$(format_tokens "$total_tokens") "
  fi

  # percentage wrapped in parentheses for a cleaner look, e.g. "30.4k/1m (3%)".
  # pct_display (and thus this whole bar_display string) contains a literal
  # "%" -- it is only ever concatenated here and later emitted via
  # `printf '%s' "$info_segment"` as a DATA argument, never as a format
  # string, so the "%" is guaranteed to display correctly.
  bar_display="${FG_BAR_FULL}${filled_part}${FG_BAR_EMPTY}${empty_part} ${FG_GIT}${tokens_display}(${pct_display})"
fi

# ---- build output ----
# IMPORTANT: every piece of text below may contain a literal "%" (percentages,
# color/reset escape codes, etc). Any such string MUST be passed as a DATA
# argument to printf (e.g. printf '%s' "$x"), never interpolated into the
# FORMAT-STRING position -- otherwise printf treats stray "%" sequences as
# conversion specifiers and silently eats them (this was the cause of the
# missing "%" after the context-usage number).
printf '%s' "${FG_LIGHT}${BG_DIR} ${dir_display} ${RESET}"

if [ -n "$git_segment" ]; then
  printf '%s' "${SEP_DIR_TO_GIT}${RESET}"
  printf '%s' "${FG_GIT}${BG_GIT} ${git_segment}${RESET}"
  printf '%s' "${SEP_GIT_TO_INFO}${RESET}"
else
  printf '%s' "${SEP_DIR_TO_GIT}${RESET}"
fi

# order: base model name -> reasoning/thinking level -> context-size bracket
# capitalize the effort level for display, except "xhigh" which stays lowercase
info_segment="${FG_INFO}${BG_INFO} ${model_base}"
if [ -n "$effort_level" ] && [ "$effort_level" != "null" ]; then
  case "$effort_level" in
    low) effort_display="Low" ;;
    medium) effort_display="Medium" ;;
    high) effort_display="High" ;;
    xhigh) effort_display="xhigh" ;;
    max) effort_display="Max" ;;
    *) effort_display="$effort_level" ;;
  esac
  info_segment="${info_segment} ${effort_display}"
elif [ "$thinking_enabled" = "true" ]; then
  info_segment="${info_segment} Thinking"
fi
if [ -n "$model_bracket" ]; then
  info_segment="${info_segment} ${model_bracket}"
fi
if [ -n "$style" ] && [ "$style" != "default" ]; then
  info_segment="${info_segment} (${style})"
fi
if [ -n "$bar_display" ]; then
  info_segment="${info_segment} ${bar_display}${FG_INFO}"
fi
info_segment="${info_segment} ${RESET}"
printf '%s' "$info_segment"

printf '%s\n' "${SEP_END}${RESET}"
