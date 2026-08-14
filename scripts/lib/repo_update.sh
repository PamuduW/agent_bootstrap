# shellcheck shell=bash

REPO_UPDATE_STATE=stopped
REPO_UPDATE_AHEAD=0
REPO_UPDATE_BEHIND=0
REPO_UPDATE_DIRTY=0
REPO_UPDATE_CHANGES=''
REPO_UPDATE_UPSTREAM=''

_repo_update_set_result() {
  local outcome_name="$1" reason_name="$2" outcome_value="$3" reason_value="$4"
  printf -v "$outcome_name" '%s' "$outcome_value"
  printf -v "$reason_name" '%s' "$reason_value"
}

_repo_update_origin_allowed() {
  local origin="$1" rewrite_rules="${2:-}" repository="${3:-agent_bootstrap}"
  local key target prefix matched_prefix='' matched_target='' resolved

  case "$origin" in
    *://*@*) return 1 ;;
    git@github.com:PamuduW/agent_bootstrap.git|https://github.com/PamuduW/agent_bootstrap.git)
      [[ "$repository" == agent_bootstrap ]] && return 0
      ;;
    git@github.com:PamuduW/dotfiles.git|https://github.com/PamuduW/dotfiles.git)
      [[ "$repository" == dotfiles ]] && return 0
      ;;
  esac

  while IFS=$' \t' read -r key target; do
    [[ "$key" == url.*.insteadof ]] || continue
    prefix="${key#url.}"
    prefix="${prefix%.insteadof}"
    [[ -n "$prefix" ]] || continue
    case "$origin" in
      "$prefix"*)
        if (( ${#prefix} > ${#matched_prefix} )); then
          matched_prefix="$prefix"
          matched_target="$target"
        fi
        ;;
    esac
  done <<<"$rewrite_rules"

  [[ -n "$matched_prefix" ]] || return 1
  resolved="${matched_target}${origin#"$matched_prefix"}"
  case "$resolved" in
    git@github.com:PamuduW/agent_bootstrap.git|https://github.com/PamuduW/agent_bootstrap.git)
      [[ "$repository" == agent_bootstrap ]] && return 0
      ;;
    git@github.com:PamuduW/dotfiles.git|https://github.com/PamuduW/dotfiles.git)
      [[ "$repository" == dotfiles ]] && return 0
      ;;
  esac
  return 1
}

_repo_update_read_changes() {
  local repo="$1" status_output

  status_output="$(git -C "$repo" status --short --untracked-files=all 2>/dev/null)" || return 1
  REPO_UPDATE_CHANGES="$status_output"
  if [[ -n "$status_output" ]]; then
    REPO_UPDATE_DIRTY=1
  else
    REPO_UPDATE_DIRTY=0
  fi
}

repo_update_classify_history() {
  local repo="$1" state_name="$2" reason_name="$3"
  local counts ahead behind classified_state classified_reason

  REPO_UPDATE_AHEAD=0
  REPO_UPDATE_BEHIND=0

  if ! counts="$(git -C "$repo" rev-list --left-right --count 'HEAD...@{upstream}' 2>/dev/null)"; then
    classified_state=stopped classified_reason=invalid-counts
  elif [[ "$counts" =~ ^([0-9]+)[[:space:]]+([0-9]+)$ ]]; then
    ahead="${BASH_REMATCH[1]}" behind="${BASH_REMATCH[2]}"
    REPO_UPDATE_AHEAD="$ahead"
    REPO_UPDATE_BEHIND="$behind"
    if ((ahead > 0 && behind > 0)); then classified_state=diverged
    elif ((ahead > 0)); then classified_state=ahead
    elif ((behind > 0)); then classified_state=behind
    else classified_state=current
    fi
    classified_reason="$classified_state"
  else
    classified_state=stopped classified_reason=invalid-counts
  fi

  printf -v "$state_name" '%s' "$classified_state"
  printf -v "$reason_name" '%s' "$classified_reason"
  REPO_UPDATE_STATE="$classified_state"
}

repo_update_run() {
  local repo="$1" decision_fn="$2" outcome_name="$3" reason_name="$4" repository="${5:-agent_bootstrap}"
  local worktree bare origin branch upstream state reason rewrite_rules

  _repo_update_set_result "$outcome_name" "$reason_name" stopped invalid-repository
  REPO_UPDATE_STATE=stopped
  REPO_UPDATE_AHEAD=0
  REPO_UPDATE_BEHIND=0
  REPO_UPDATE_DIRTY=0
  REPO_UPDATE_CHANGES=''
  REPO_UPDATE_UPSTREAM=''
  [[ -d "$repo" ]] || return 0
  worktree="$(git -C "$repo" rev-parse --is-inside-work-tree 2>/dev/null)" || return 0
  [[ "$worktree" == true ]] || return 0
  bare="$(git -C "$repo" rev-parse --is-bare-repository 2>/dev/null)" || return 0
  [[ "$bare" == false ]] || return 0

  origin="$(git -C "$repo" remote get-url origin 2>/dev/null)" || {
    _repo_update_set_result "$outcome_name" "$reason_name" stopped invalid-origin
    return 0
  }
  if ! _repo_update_origin_allowed "$origin" '' "$repository"; then
    rewrite_rules="$(git config --global --get-regexp '^url\..*\.insteadof$' 2>/dev/null || true)"
    _repo_update_origin_allowed "$origin" "$rewrite_rules" "$repository" || {
      _repo_update_set_result "$outcome_name" "$reason_name" stopped invalid-origin
      return 0
    }
  fi

  branch="$(git -C "$repo" symbolic-ref --quiet --short HEAD 2>/dev/null)" || {
    _repo_update_set_result "$outcome_name" "$reason_name" stopped detached
    return 0
  }
  [[ -n "$branch" ]] || {
    _repo_update_set_result "$outcome_name" "$reason_name" stopped detached
    return 0
  }
  upstream="$(git -C "$repo" rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>/dev/null)" || {
    _repo_update_set_result "$outcome_name" "$reason_name" stopped no-upstream
    return 0
  }
  [[ -n "$upstream" ]] || {
    _repo_update_set_result "$outcome_name" "$reason_name" stopped no-upstream
    return 0
  }
  REPO_UPDATE_UPSTREAM="$upstream"
  if ! _repo_update_read_changes "$repo"; then
    _repo_update_set_result "$outcome_name" "$reason_name" stopped status-failed
    return 0
  fi
  if ! git -C "$repo" fetch --prune; then
    _repo_update_set_result "$outcome_name" "$reason_name" stopped fetch-failed
    return 0
  fi

  repo_update_classify_history "$repo" state reason
  if [[ "$state" == stopped ]]; then
    _repo_update_set_result "$outcome_name" "$reason_name" stopped "$reason"
    return 0
  fi
  if ((REPO_UPDATE_DIRTY)); then
    _repo_update_set_result "$outcome_name" "$reason_name" stopped dirty
    return 0
  fi
  case "$state" in
    current) _repo_update_set_result "$outcome_name" "$reason_name" current current ;;
    ahead)
      if "$decision_fn" continue-ahead; then
        _repo_update_set_result "$outcome_name" "$reason_name" ahead-approved ahead
      else
        _repo_update_set_result "$outcome_name" "$reason_name" stopped ahead-declined
      fi
      ;;
    behind)
      if ! "$decision_fn" pull-behind; then
        _repo_update_set_result "$outcome_name" "$reason_name" stopped behind-declined
      elif git -C "$repo" pull --ff-only; then
        _repo_update_set_result "$outcome_name" "$reason_name" relaunch-required pulled
      else
        _repo_update_set_result "$outcome_name" "$reason_name" stopped pull-failed
      fi
      ;;
    diverged)
      _repo_update_set_result "$outcome_name" "$reason_name" stopped "$reason"
      ;;
    *) _repo_update_set_result "$outcome_name" "$reason_name" stopped invalid-counts ;;
  esac
}

repo_update_invoke_relaunch() {
  local relaunch_fn="$1"
  shift
  [[ "$(type -t "$relaunch_fn" 2>/dev/null)" == function ]] || return 1
  "$relaunch_fn" "$@"
}
