#!/usr/bin/env bash
set -euo pipefail

# ┌─────────────────────────────────────────────────────────────────────┐
# │  agent_bootstrap — interactive plugin manager                       │
# │                                                                     │
# │  Usage:                                                             │
# │    ./install.sh                    Interactive mode (TUI menu)      │
# │    ./install.sh --global           Deploy globally (CI-friendly)    │
# │    ./install.sh --workspace PATH   Deploy to one workspace          │
# │    ./install.sh --all DIR          Deploy to all repos under DIR    │
# │    ./install.sh --status           Show installation status         │
# │    ./install.sh --uninstall        Remove all installed configs     │
# └─────────────────────────────────────────────────────────────────────┘

BOOTSTRAP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANIFEST="$BOOTSTRAP_DIR/manifest.json"
CURSOR_PLUGIN_CACHE="${HOME}/.cursor/plugins/cache/cursor-public"
CODEX_SKILLS_DIR="${HOME}/.codex/skills"
CURSOR_NATIVE_DIR="${HOME}/.cursor/skills-cursor"
INSTALLED_LOG="$BOOTSTRAP_DIR/.installed"
LOCAL_CONFIG="$BOOTSTRAP_DIR/.local-config"
MCP_REPO="$BOOTSTRAP_DIR/mcp/mcp.json"
DRY_RUN=false
FORCE=false

# ---------------------------------------------------------------------------
# Logging — write a parallel log file (no pipe/tee to avoid TUI buffering)
# ---------------------------------------------------------------------------
LOG_DIR="$BOOTSTRAP_DIR/log"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/$(date '+%Y-%m-%d_%H-%M-%S')_install.log"
_log() { printf '[%s] %s\n' "$(date '+%H:%M:%S')" "$*" >> "$LOG_FILE"; }

# ---------------------------------------------------------------------------
# Colors & output
# ---------------------------------------------------------------------------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; DIM='\033[2m'
REVERSE='\033[7m'; NC='\033[0m'

info()   { printf "${CYAN}[info]${NC}  %s\n" "$*"; _log "INFO  $*"; }
ok()     { printf "${GREEN}[ok]${NC}    %s\n" "$*"; _log "OK    $*"; }
skip()   { printf "${YELLOW}[skip]${NC}  %s\n" "$*"; _log "SKIP  $*"; }
warn()   { printf "${YELLOW}[warn]${NC}  %s\n" "$*"; _log "WARN  $*"; }
err()    { printf "${RED}[err]${NC}   %s\n" "$*" >&2; _log "ERR   $*"; }
header() { printf "\n${BOLD}── %s${NC}\n" "$*"; _log "── $*"; }

# ---------------------------------------------------------------------------
# Prerequisites
# ---------------------------------------------------------------------------
if ! command -v jq &>/dev/null; then
  err "jq is required. Install with: sudo apt install jq"
  exit 1
fi

if [[ ! -f "$MANIFEST" ]]; then
  echo '{"version":2,"last_sync":"","sources":{"cursor-plugins":{"base_path":"~/.cursor/plugins/cache/cursor-public","plugins":{}},"codex-skills":{"base_path":"~/.codex/skills","skills":{}},"cursor-native-skills":{"base_path":"~/.cursor/skills-cursor","skills":{}}}}' | jq . > "$MANIFEST"
fi

trap 'err "Error on line $LINENO (exit $?). See log: $LOG_FILE"' ERR

# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------
run() {
  if $DRY_RUN; then printf "${YELLOW}[dry]${NC}   %s\n" "$*"; else "$@"; fi
}

log_installed() {
  $DRY_RUN && return 0
  grep -qxF "$1" "$INSTALLED_LOG" 2>/dev/null || echo "$1" >> "$INSTALLED_LOG"
}

symlink_file() {
  local src="$1" dst="$2"
  if [[ -L "$dst" ]]; then
    local current
    current=$(readlink -f "$dst" 2>/dev/null || true)
    if [[ "$current" == "$(readlink -f "$src")" ]]; then
      return 0
    fi
    run rm "$dst"
  elif [[ -e "$dst" ]]; then
    skip "Exists (not symlink): $dst"
    return 0
  fi
  run ln -s "$src" "$dst"
  if ! $DRY_RUN; then
    log_installed "symlink:$dst"
  fi
}

_KNOWN_PLUGINS_CACHE=""
get_plugin_for_asset() {
  local asset_name="$1"
  if [[ -z "$_KNOWN_PLUGINS_CACHE" ]]; then
    if [[ ${#PLUGIN_NAMES[@]} -gt 0 ]]; then
      _KNOWN_PLUGINS_CACHE=$(printf "%s\n" "${PLUGIN_NAMES[@]}")
    else
      _KNOWN_PLUGINS_CACHE=$(jq -r '.sources["cursor-plugins"].plugins | keys[]' "$MANIFEST" 2>/dev/null || true)
      _KNOWN_PLUGINS_CACHE+=$'\ncursor-native'
    fi
  fi
  local best="" best_len=0
  while IFS= read -r pname; do
    [[ -z "$pname" ]] && continue
    if [[ "$asset_name" == "${pname}-"* ]] && [[ ${#pname} -gt $best_len ]]; then
      best="$pname"
      best_len=${#pname}
    fi
  done <<< "$_KNOWN_PLUGINS_CACHE"
  echo "$best"
}

update_manifest_timestamp() {
  local today; today=$(date +%Y-%m-%d)
  local tmp; tmp=$(mktemp)
  jq --arg date "$today" '.last_sync = $date' "$MANIFEST" > "$tmp"
  mv "$tmp" "$MANIFEST"
}

# ---------------------------------------------------------------------------
# Manifest helpers
# ---------------------------------------------------------------------------
manifest_plugin_hash() {
  jq -r ".sources[\"cursor-plugins\"].plugins[\"$1\"].hash // empty" "$MANIFEST"
}

manifest_plugin_synced_epoch() {
  local raw
  raw=$(jq -r ".sources[\"cursor-plugins\"].plugins[\"$1\"].synced_at // \"0\"" "$MANIFEST")
  if [[ "$raw" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
    date -d "$raw" +%s 2>/dev/null || echo 0
  else
    echo "${raw:-0}"
  fi
}

_cache_is_newer() {
  local name="$1"
  local cache_hash="${PLUGIN_CACHE_HASH[$name]:-}"
  [[ -z "$cache_hash" ]] && return 1
  local cache_dir="$CURSOR_PLUGIN_CACHE/$name/$cache_hash"
  local cache_mtime
  cache_mtime=$(stat -c %Y "$cache_dir" 2>/dev/null || echo 0)
  local synced_epoch
  synced_epoch=$(manifest_plugin_synced_epoch "$name")
  [[ $cache_mtime -gt $synced_epoch ]]
}

manifest_plugin_mcp_servers() {
  jq -r ".sources[\"cursor-plugins\"].plugins[\"$1\"].mcp_servers // [] | join(\",\")" "$MANIFEST" 2>/dev/null
}

manifest_set_plugin() {
  local name="$1" hash="$2" date="$3"
  local skills="${4:-0}" rules="${5:-0}" agents="${6:-0}" commands="${7:-0}" hooks="${8:-0}" mcp="${9:-0}"
  local mcp_servers_json="${10:-[]}"

  local tmp; tmp=$(mktemp)
  jq --arg name "$name" \
     --arg hash "$hash" \
     --arg date "$date" \
     --argjson sk "$skills" \
     --argjson ru "$rules" \
     --argjson ag "$agents" \
     --argjson cm "$commands" \
     --argjson hk "$hooks" \
     --argjson mc "$mcp" \
     --argjson ms "$mcp_servers_json" \
     '.sources["cursor-plugins"].plugins[$name] = {
        hash: $hash, synced_at: $date,
        skills: $sk, rules: $ru, agents: $ag,
        commands: $cm, hooks: $hk, mcp: $mc,
        mcp_servers: $ms
      }' "$MANIFEST" > "$tmp"
  mv "$tmp" "$MANIFEST"
}

manifest_remove_plugin() {
  local name="$1"
  local tmp; tmp=$(mktemp)
  jq --arg name "$name" 'del(.sources["cursor-plugins"].plugins[$name])' "$MANIFEST" > "$tmp"
  mv "$tmp" "$MANIFEST"
}

# ---------------------------------------------------------------------------
# MCP helpers
# ---------------------------------------------------------------------------
get_mcp_keys_from_cache() {
  local plugin_name="$1"
  local hash
  hash=$(ls "$CURSOR_PLUGIN_CACHE/$plugin_name/" 2>/dev/null | head -1)
  [[ -z "$hash" ]] && echo "[]" && return 0

  local base="$CURSOR_PLUGIN_CACHE/$plugin_name/$hash"
  local mcp_file=""
  [[ -f "$base/.mcp.json" ]] && mcp_file="$base/.mcp.json"
  [[ -f "$base/mcp.json" ]] && mcp_file="$base/mcp.json"
  [[ -z "$mcp_file" ]] && echo "[]" && return 0

  local keys
  keys=$(jq -r 'if .mcpServers then .mcpServers | keys[] else keys[] end' "$mcp_file" 2>/dev/null || true)
  if [[ -z "$keys" ]]; then
    echo "[]"
  else
    echo "$keys" | jq -R . | jq -s .
  fi
}

add_plugin_mcp_to_repo() {
  local plugin_name="$1" hash="$2"
  local base="$CURSOR_PLUGIN_CACHE/$plugin_name/$hash"
  local mcp_file=""
  [[ -f "$base/.mcp.json" ]] && mcp_file="$base/.mcp.json"
  [[ -f "$base/mcp.json" ]] && mcp_file="$base/mcp.json"
  [[ -z "$mcp_file" ]] && return 0
  [[ ! -f "$MCP_REPO" ]] && echo '{"mcpServers":{}}' > "$MCP_REPO"

  local has_wrapper
  has_wrapper=$(jq 'has("mcpServers")' "$mcp_file" 2>/dev/null || echo "false")

  local tmp; tmp=$(mktemp)
  if [[ "$has_wrapper" == "true" ]]; then
    jq -s '.[0] * { mcpServers: (.[0].mcpServers + .[1].mcpServers) }' "$MCP_REPO" "$mcp_file" > "$tmp"
  else
    jq -s '.[0] * { mcpServers: (.[0].mcpServers + .[1]) }' "$MCP_REPO" "$mcp_file" > "$tmp"
  fi
  mv "$tmp" "$MCP_REPO"
}

remove_plugin_mcp_from_repo() {
  local keys="$1"
  [[ -z "$keys" ]] && return 0
  [[ ! -f "$MCP_REPO" ]] && return 0

  IFS=',' read -ra key_arr <<< "$keys"
  local filter='.'
  for key in "${key_arr[@]}"; do
    [[ -z "$key" ]] && continue
    filter+=" | del(.mcpServers[\"$key\"])"
  done
  local tmp; tmp=$(mktemp)
  jq "$filter" "$MCP_REPO" > "$tmp"
  mv "$tmp" "$MCP_REPO"
}

sync_target_mcp() {
  local target="$1"
  [[ -d "$(dirname "$target")" ]] || return 0

  if [[ ! -f "$target" ]]; then
    echo '{"mcpServers":{}}' > "$target"
  fi

  if ! jq empty "$target" 2>/dev/null; then
    warn "Invalid JSON in $target, resetting"
    echo '{"mcpServers":{}}' > "$target"
  fi

  local all_keys=()
  for name in "${PLUGIN_NAMES[@]}"; do
    local keys="${PLUGIN_MCP_KEYS[$name]:-}"
    [[ -z "$keys" ]] && continue
    IFS=',' read -ra ks <<< "$keys"
    for k in "${ks[@]}"; do
      [[ -n "$k" ]] && all_keys+=("$k")
    done
  done

  local filter='.'
  for key in "${all_keys[@]}"; do
    filter+=" | del(.mcpServers[\"$key\"])"
  done
  local tmp; tmp=$(mktemp)
  if ! jq "$filter" "$target" > "$tmp" 2>/dev/null; then
    warn "jq filter failed on $target, resetting"
    echo '{"mcpServers":{}}' > "$tmp"
  fi

  for name in "${PLUGIN_NAMES[@]}"; do
    [[ "${PLUGIN_LOCAL_SEL[$name]:-0}" != "1" ]] && continue
    local keys="${PLUGIN_MCP_KEYS[$name]:-}"
    [[ -z "$keys" ]] && continue
    IFS=',' read -ra ks <<< "$keys"
    for key in "${ks[@]}"; do
      [[ -z "$key" ]] && continue
      if [[ "$key" == "jfrog" ]]; then
        if [[ -n "${JFROG_PLATFORM_URL:-}" ]]; then
          local tmp2; tmp2=$(mktemp)
          jq --arg url "https://${JFROG_PLATFORM_URL}/mcp" \
             '.mcpServers.jfrog = { url: $url }' "$tmp" > "$tmp2" && mv "$tmp2" "$tmp"
        fi
        continue
      fi
      local server_config
      server_config=$(jq ".mcpServers[\"$key\"]" "$MCP_REPO" 2>/dev/null || echo "null")
      if [[ "$server_config" != "null" ]] && [[ -n "$server_config" ]]; then
        local tmp2; tmp2=$(mktemp)
        jq --arg key "$key" --argjson val "$server_config" \
           '.mcpServers[$key] = $val' "$tmp" > "$tmp2" && mv "$tmp2" "$tmp"
      fi
    done
  done

  mv "$tmp" "$target"
}

# ---------------------------------------------------------------------------
# Manifest v2 migration — add mcp_servers arrays
# ---------------------------------------------------------------------------
migrate_manifest_v2() {
  local version
  version=$(jq -r '.version // 1' "$MANIFEST")
  [[ "$version" -ge 2 ]] && return 0

  info "Migrating manifest to v2 (adding MCP server tracking)..."

  for plugin_name in $(jq -r '.sources["cursor-plugins"].plugins | keys[]' "$MANIFEST" 2>/dev/null); do
    local mcp_count
    mcp_count=$(jq -r ".sources[\"cursor-plugins\"].plugins[\"$plugin_name\"].mcp // 0" "$MANIFEST")
    local mcp_servers="[]"
    if [[ "$mcp_count" -gt 0 ]]; then
      mcp_servers=$(get_mcp_keys_from_cache "$plugin_name")
    fi
    local tmp; tmp=$(mktemp)
    jq --arg name "$plugin_name" --argjson ms "$mcp_servers" \
       '.sources["cursor-plugins"].plugins[$name].mcp_servers = $ms' "$MANIFEST" > "$tmp"
    mv "$tmp" "$MANIFEST"
  done

  # Fix any missing MCP imports (e.g., notion-workspace with non-standard format)
  for plugin_name in $(jq -r '.sources["cursor-plugins"].plugins | keys[]' "$MANIFEST" 2>/dev/null); do
    local mcp_keys
    mcp_keys=$(jq -r ".sources[\"cursor-plugins\"].plugins[\"$plugin_name\"].mcp_servers // [] | .[]" "$MANIFEST" 2>/dev/null)
    for key in $mcp_keys; do
      [[ -z "$key" ]] && continue
      [[ "$key" == "jfrog" ]] && continue
      if ! jq -e ".mcpServers[\"$key\"]" "$MCP_REPO" &>/dev/null 2>&1; then
        local hash
        hash=$(ls "$CURSOR_PLUGIN_CACHE/$plugin_name/" 2>/dev/null | head -1)
        if [[ -n "$hash" ]]; then
          add_plugin_mcp_to_repo "$plugin_name" "$hash"
          ok "  Imported missing MCP server '$key' from $plugin_name"
        fi
      fi
    done
  done

  local tmp; tmp=$(mktemp)
  jq '.version = 2' "$MANIFEST" > "$tmp"
  mv "$tmp" "$MANIFEST"
  ok "Manifest migrated to v2"
}

# ---------------------------------------------------------------------------
# Plugin registry
# ---------------------------------------------------------------------------
declare -a PLUGIN_NAMES=()
declare -A PLUGIN_IN_REPO=()
declare -A PLUGIN_IN_LOCAL=()
declare -A PLUGIN_IN_CACHE=()
declare -A PLUGIN_REPO_SEL=()
declare -A PLUGIN_LOCAL_SEL=()
declare -A PLUGIN_SKILLS=()
declare -A PLUGIN_RULES=()
declare -A PLUGIN_AGENTS=()
declare -A PLUGIN_COMMANDS=()
declare -A PLUGIN_HOOKS=()
declare -A PLUGIN_MCP_KEYS=()
declare -A PLUGIN_CACHE_HASH=()
declare -A PLUGIN_SOURCE=()

_plugin_exists() {
  local name="$1"
  for n in "${PLUGIN_NAMES[@]:-}"; do
    [[ "$n" == "$name" ]] && return 0
  done
  return 1
}

_add_plugin() {
  _plugin_exists "$1" || PLUGIN_NAMES+=("$1")
}

_count_repo_assets() {
  local plugin="$1"
  local skills=0 rules=0 agents=0 commands=0 hooks=0
  for d in "$BOOTSTRAP_DIR"/skills/${plugin}-*/; do
    [[ -f "$d/SKILL.md" ]] 2>/dev/null && skills=$((skills + 1))
  done
  for f in "$BOOTSTRAP_DIR"/rules/${plugin}-*.mdc; do
    [[ -f "$f" ]] 2>/dev/null && rules=$((rules + 1))
  done
  for f in "$BOOTSTRAP_DIR"/agents/${plugin}-*.md; do
    [[ -f "$f" ]] 2>/dev/null && agents=$((agents + 1))
  done
  for f in "$BOOTSTRAP_DIR"/commands/${plugin}-*.md; do
    [[ -f "$f" ]] 2>/dev/null && commands=$((commands + 1))
  done
  [[ -d "$BOOTSTRAP_DIR/hooks/$plugin" ]] && hooks=1
  PLUGIN_SKILLS["$plugin"]=$skills
  PLUGIN_RULES["$plugin"]=$rules
  PLUGIN_AGENTS["$plugin"]=$agents
  PLUGIN_COMMANDS["$plugin"]=$commands
  PLUGIN_HOOKS["$plugin"]=$hooks
}

_plugin_has_repo_state() {
  local plugin="$1"
  local asset_total=0
  asset_total=$((asset_total + ${PLUGIN_SKILLS[$plugin]:-0}))
  asset_total=$((asset_total + ${PLUGIN_RULES[$plugin]:-0}))
  asset_total=$((asset_total + ${PLUGIN_AGENTS[$plugin]:-0}))
  asset_total=$((asset_total + ${PLUGIN_COMMANDS[$plugin]:-0}))
  asset_total=$((asset_total + ${PLUGIN_HOOKS[$plugin]:-0}))
  if [[ $asset_total -gt 0 ]]; then
    return 0
  fi

  local mcp_keys="${PLUGIN_MCP_KEYS[$plugin]:-}"
  [[ -z "$mcp_keys" || ! -f "$MCP_REPO" ]] && return 1

  local key
  local key_arr=()
  IFS=',' read -ra key_arr <<< "$mcp_keys"
  for key in "${key_arr[@]}"; do
    [[ -z "$key" ]] && continue
    if jq -e --arg key "$key" '.mcpServers[$key]' "$MCP_REPO" >/dev/null 2>&1; then
      return 0
    fi
  done

  return 1
}

# ---------------------------------------------------------------------------
# Plugin discovery
# ---------------------------------------------------------------------------
discover_plugins() {
  PLUGIN_NAMES=()
  PLUGIN_IN_REPO=()
  PLUGIN_IN_LOCAL=()
  PLUGIN_IN_CACHE=()
  PLUGIN_REPO_SEL=()
  PLUGIN_LOCAL_SEL=()
  PLUGIN_SKILLS=()
  PLUGIN_RULES=()
  PLUGIN_AGENTS=()
  PLUGIN_COMMANDS=()
  PLUGIN_HOOKS=()
  PLUGIN_MCP_KEYS=()
  PLUGIN_CACHE_HASH=()
  PLUGIN_SOURCE=()
  _KNOWN_PLUGINS_CACHE=""

  # 1. From manifest — cursor plugins
  for plugin_name in $(jq -r '.sources["cursor-plugins"].plugins | keys[]' "$MANIFEST" 2>/dev/null); do
    local mcp_keys
    mcp_keys=$(jq -r ".sources[\"cursor-plugins\"].plugins[\"$plugin_name\"].mcp_servers // [] | join(\",\")" "$MANIFEST" 2>/dev/null)
    PLUGIN_MCP_KEYS["$plugin_name"]="$mcp_keys"
    _count_repo_assets "$plugin_name"
    if ! _plugin_has_repo_state "$plugin_name"; then
      continue
    fi
    _add_plugin "$plugin_name"
    PLUGIN_IN_REPO["$plugin_name"]=1
    PLUGIN_SOURCE["$plugin_name"]="cursor-plugin"
  done

  # 2. cursor-native skills
  local native_count=0
  for skill_name in $(jq -r '.sources["cursor-native-skills"].skills | keys[]' "$MANIFEST" 2>/dev/null); do
    native_count=$((native_count + 1))
  done
  if [[ $native_count -gt 0 ]] || [[ -d "$CURSOR_NATIVE_DIR" ]]; then
    _add_plugin "cursor-native"
    PLUGIN_SOURCE["cursor-native"]="cursor-native"
    PLUGIN_IN_REPO["cursor-native"]=1
    PLUGIN_MCP_KEYS["cursor-native"]=""
    _count_repo_assets "cursor-native"
    PLUGIN_IN_LOCAL["cursor-native"]=1
    PLUGIN_IN_CACHE["cursor-native"]=1
  fi

  # 3. From Cursor plugin cache (discover new plugins not in manifest)
  if [[ -d "$CURSOR_PLUGIN_CACHE" ]]; then
    for plugin_dir in "$CURSOR_PLUGIN_CACHE"/*/; do
      [[ -d "$plugin_dir" ]] || continue
      local plugin_name
      plugin_name=$(basename "$plugin_dir")
      local hash
      hash=$(ls "$plugin_dir" 2>/dev/null | head -1)
      [[ -z "$hash" ]] && continue

      _add_plugin "$plugin_name"
      PLUGIN_IN_CACHE["$plugin_name"]=1
      PLUGIN_CACHE_HASH["$plugin_name"]="$hash"

      if [[ "${PLUGIN_IN_REPO[$plugin_name]:-0}" == "0" ]]; then
        PLUGIN_IN_REPO["$plugin_name"]=0
        PLUGIN_SOURCE["$plugin_name"]="cursor-plugin"
        local base="$CURSOR_PLUGIN_CACHE/$plugin_name/$hash"
        local sk=0 ru=0 ag=0 cm=0 hk=0
        [[ -d "$base/skills" ]] && sk=$(ls "$base/skills/" 2>/dev/null | wc -l)
        [[ -d "$base/rules" ]] && ru=$(ls "$base/rules/" 2>/dev/null | wc -l)
        [[ -d "$base/agents" ]] && ag=$(ls "$base/agents/" 2>/dev/null | wc -l)
        [[ -d "$base/commands" ]] && cm=$(ls "$base/commands/" 2>/dev/null | wc -l)
        [[ -d "$base/hooks" ]] && hk=1 || hk=0
        PLUGIN_SKILLS["$plugin_name"]=$sk
        PLUGIN_RULES["$plugin_name"]=$ru
        PLUGIN_AGENTS["$plugin_name"]=$ag
        PLUGIN_COMMANDS["$plugin_name"]=$cm
        PLUGIN_HOOKS["$plugin_name"]=$hk

        local mcp_keys
        mcp_keys=$(get_mcp_keys_from_cache "$plugin_name" | jq -r 'join(",")' 2>/dev/null || true)
        PLUGIN_MCP_KEYS["$plugin_name"]="${mcp_keys:-}"
      fi
    done
  fi

  # 4. Detect local state (simple: if in repo, assume deployed unless overridden)
  for name in "${PLUGIN_NAMES[@]}"; do
    [[ "${PLUGIN_SOURCE[$name]:-}" == "cursor-native" ]] && continue
    PLUGIN_IN_LOCAL["$name"]="${PLUGIN_IN_REPO[$name]:-0}"
  done

  # 5. Sort alphabetically
  IFS=$'\n' PLUGIN_NAMES=($(sort <<<"${PLUGIN_NAMES[*]}")); unset IFS

  # 6. Initialize selections from current state
  for name in "${PLUGIN_NAMES[@]}"; do
    PLUGIN_REPO_SEL["$name"]="${PLUGIN_IN_REPO[$name]:-0}"
    PLUGIN_LOCAL_SEL["$name"]="${PLUGIN_IN_LOCAL[$name]:-0}"
  done

  # 7. Override local selections from saved config
  load_local_config
  prune_unselected_plugins

  # Invalidate plugin name cache
  _KNOWN_PLUGINS_CACHE=""
}

# ---------------------------------------------------------------------------
# Local config persistence
# ---------------------------------------------------------------------------
save_local_config() {
  : > "$LOCAL_CONFIG"
  for name in "${PLUGIN_NAMES[@]}"; do
    echo "${name}=${PLUGIN_LOCAL_SEL[$name]:-0}" >> "$LOCAL_CONFIG"
  done
}

load_local_config() {
  [[ -f "$LOCAL_CONFIG" ]] || return 0
  while IFS='=' read -r pname pval; do
    [[ -z "$pname" || "$pname" == \#* ]] && continue
    if _plugin_exists "$pname"; then
      PLUGIN_LOCAL_SEL["$pname"]="$pval"
    fi
  done < "$LOCAL_CONFIG"
}

prune_unselected_plugins() {
  local kept=()
  local name
  for name in "${PLUGIN_NAMES[@]}"; do
    if [[ "${PLUGIN_REPO_SEL[$name]:-0}" == "1" ]] || [[ "${PLUGIN_LOCAL_SEL[$name]:-0}" == "1" ]]; then
      kept+=("$name")
    fi
  done
  PLUGIN_NAMES=("${kept[@]}")
}

is_plugin_locally_enabled() {
  local plugin="$1"
  [[ "${PLUGIN_LOCAL_SEL[$plugin]:-1}" == "1" ]]
}

# ---------------------------------------------------------------------------
# Repo sync — pull a plugin from cache into the bootstrap repo
# ---------------------------------------------------------------------------
pull_plugin_to_repo() {
  local plugin_name="$1" hash="$2"
  local src="$CURSOR_PLUGIN_CACHE/$plugin_name/$hash"

  if [[ ! -d "$src" ]]; then
    err "Plugin source not found: $src"
    return 1
  fi

  info "Exporting: $plugin_name"

  # Skills
  if [[ -d "$src/skills" ]]; then
    for skill_dir in "$src/skills"/*/; do
      [[ -d "$skill_dir" ]] || continue
      local skill_name; skill_name=$(basename "$skill_dir")
      local dst="$BOOTSTRAP_DIR/skills/${plugin_name}-${skill_name}"
      [[ -d "$dst" ]] && rm -rf "$dst"
      cp -r "$skill_dir" "$dst"
      ok "  skill: ${plugin_name}-${skill_name}"
    done
  fi

  # Rules
  if [[ -d "$src/rules" ]]; then
    for rule in "$src/rules"/*.mdc; do
      [[ -f "$rule" ]] || continue
      cp "$rule" "$BOOTSTRAP_DIR/rules/${plugin_name}-$(basename "$rule")"
      ok "  rule: ${plugin_name}-$(basename "$rule")"
    done
  fi

  # Agents
  if [[ -d "$src/agents" ]]; then
    for agent in "$src/agents"/*.md; do
      [[ -f "$agent" ]] || continue
      cp "$agent" "$BOOTSTRAP_DIR/agents/${plugin_name}-$(basename "$agent")"
      ok "  agent: ${plugin_name}-$(basename "$agent")"
    done
  fi

  # Commands
  if [[ -d "$src/commands" ]]; then
    for cmd_file in "$src/commands"/*.md; do
      [[ -f "$cmd_file" ]] || continue
      cp "$cmd_file" "$BOOTSTRAP_DIR/commands/${plugin_name}-$(basename "$cmd_file")"
      ok "  command: ${plugin_name}-$(basename "$cmd_file")"
    done
  fi

  # Hooks
  if [[ -d "$src/hooks" ]]; then
    local hook_dst="$BOOTSTRAP_DIR/hooks/$plugin_name"
    rm -rf "$hook_dst"
    cp -r "$src/hooks" "$hook_dst"
    [[ -d "$src/lib" ]] && cp -r "$src/lib" "$hook_dst/lib"
    ok "  hooks: $plugin_name"
  fi

  # MCP
  add_plugin_mcp_to_repo "$plugin_name" "$hash"

  # Manifest
  local skills_count rules_count agents_count commands_count hooks_count mcp_count
  skills_count=0;  [[ -d "$src/skills" ]]  && skills_count=$(ls "$src/skills/" 2>/dev/null | wc -l)
  rules_count=0;   [[ -d "$src/rules" ]]   && rules_count=$(ls "$src/rules/" 2>/dev/null | wc -l)
  agents_count=0;  [[ -d "$src/agents" ]]  && agents_count=$(ls "$src/agents/" 2>/dev/null | wc -l)
  commands_count=0;[[ -d "$src/commands" ]] && commands_count=$(ls "$src/commands/" 2>/dev/null | wc -l)
  hooks_count=0;   [[ -d "$src/hooks" ]]   && hooks_count=1
  mcp_count=0
  local mcp_file=""
  [[ -f "$src/.mcp.json" ]] && mcp_file="$src/.mcp.json"
  [[ -f "$src/mcp.json" ]] && mcp_file="$src/mcp.json"
  [[ -n "$mcp_file" ]] && mcp_count=1

  local mcp_servers_json
  mcp_servers_json=$(get_mcp_keys_from_cache "$plugin_name")
  local now_epoch; now_epoch=$(date +%s)

  manifest_set_plugin "$plugin_name" "$hash" "$now_epoch" \
    "$skills_count" "$rules_count" "$agents_count" "$commands_count" \
    "$hooks_count" "$mcp_count" "$mcp_servers_json"

  # Update counts in registry
  _count_repo_assets "$plugin_name"
  PLUGIN_IN_REPO["$plugin_name"]=1
  PLUGIN_MCP_KEYS["$plugin_name"]=$(echo "$mcp_servers_json" | jq -r 'join(",")' 2>/dev/null || true)
  _KNOWN_PLUGINS_CACHE=""
}

# ---------------------------------------------------------------------------
# Repo sync — remove a plugin from the bootstrap repo
# ---------------------------------------------------------------------------
remove_plugin_from_repo() {
  local plugin="$1"
  info "Removing from repo: $plugin"

  for d in "$BOOTSTRAP_DIR"/skills/${plugin}-*/; do
    [[ -d "$d" ]] && rm -rf "$d" && ok "  Deleted skills/$(basename "$d")"
  done
  for f in "$BOOTSTRAP_DIR"/rules/${plugin}-*.mdc; do
    [[ -f "$f" ]] && rm "$f" && ok "  Deleted rules/$(basename "$f")"
  done
  for f in "$BOOTSTRAP_DIR"/agents/${plugin}-*.md; do
    [[ -f "$f" ]] && rm "$f" && ok "  Deleted agents/$(basename "$f")"
  done
  for f in "$BOOTSTRAP_DIR"/commands/${plugin}-*.md; do
    [[ -f "$f" ]] && rm "$f" && ok "  Deleted commands/$(basename "$f")"
  done
  if [[ -d "$BOOTSTRAP_DIR/hooks/$plugin" ]]; then
    rm -rf "$BOOTSTRAP_DIR/hooks/$plugin"
    ok "  Deleted hooks/$plugin"
  fi

  remove_plugin_mcp_from_repo "${PLUGIN_MCP_KEYS[$plugin]:-}"
  manifest_remove_plugin "$plugin"
  PLUGIN_IN_REPO["$plugin"]=0
  _KNOWN_PLUGINS_CACHE=""
  ok "Removed $plugin from repo"
}

# ---------------------------------------------------------------------------
# Local deploy — sync Codex skill symlinks
# ---------------------------------------------------------------------------
sync_codex_skills() {
  [[ -d "$HOME/.codex" ]] || return 0
  mkdir -p "$CODEX_SKILLS_DIR"

  # Remove symlinks for disabled plugins
  for skill_link in "$CODEX_SKILLS_DIR"/*/; do
    local link_path="${skill_link%/}"
    [[ -L "$link_path" ]] || continue
    local target
    target=$(readlink -f "$link_path" 2>/dev/null || true)
    [[ "$target" == "$BOOTSTRAP_DIR"* ]] || continue
    local skill_name; skill_name=$(basename "$link_path")
    local plugin; plugin=$(get_plugin_for_asset "$skill_name")
    [[ -z "$plugin" ]] && continue
    if [[ "${PLUGIN_LOCAL_SEL[$plugin]:-0}" != "1" ]]; then
      rm "$link_path"
    fi
  done

  # Add symlinks for enabled plugins
  for name in "${PLUGIN_NAMES[@]}"; do
    [[ "${PLUGIN_LOCAL_SEL[$name]:-0}" != "1" ]] && continue
    for skill_dir in "$BOOTSTRAP_DIR"/skills/${name}-*/; do
      [[ -f "$skill_dir/SKILL.md" ]] 2>/dev/null || continue
      local skill_name; skill_name=$(basename "$skill_dir")
      local dst="$CODEX_SKILLS_DIR/$skill_name"
      symlink_file "$skill_dir" "$dst"
    done
  done
}

# ---------------------------------------------------------------------------
# Generated files
# ---------------------------------------------------------------------------
generate_skills_rule() {
  local target_dir="$1"
  local rule_file="$target_dir/.cursor/rules/bootstrap-skills.mdc"
  $DRY_RUN && { printf "${YELLOW}[dry]${NC}   Generate %s\n" "$rule_file"; return; }

  mkdir -p "$target_dir/.cursor/rules"
  cat > "$rule_file" << 'HEADER'
---
description: Agent capabilities provided by agent_bootstrap
alwaysApply: true
---
HEADER

  {
    echo "You have access to additional skills from the agent bootstrap repo."
    echo "To use a skill, read its SKILL.md file and follow the instructions within."
    echo ""
    echo "## Available Skills"
    echo ""
  } >> "$rule_file"

  for skill_dir in "$BOOTSTRAP_DIR"/skills/*/; do
    [[ -f "$skill_dir/SKILL.md" ]] || continue
    local name; name=$(basename "$skill_dir")
    local plugin; plugin=$(get_plugin_for_asset "$name")
    if [[ -n "$plugin" ]] && ! is_plugin_locally_enabled "$plugin"; then
      continue
    fi
    local desc=""
    desc=$(head -20 "$skill_dir/SKILL.md" | grep -i "^description:" | head -1 | sed 's/^description:\s*//' || true)
    if [[ -z "$desc" ]]; then
      desc=$(head -5 "$skill_dir/SKILL.md" | grep "^#" | head -1 | sed 's/^#\+\s*//' || true)
    fi
    echo "- **$name**: \`${skill_dir}SKILL.md\`${desc:+ — $desc}" >> "$rule_file"
  done

  {
    echo ""
    echo "## Available Commands (prompt templates)"
    echo ""
  } >> "$rule_file"
  for cmd_file in "$BOOTSTRAP_DIR"/commands/*.md; do
    [[ -f "$cmd_file" ]] || continue
    local cname; cname=$(basename "$cmd_file" .md)
    local plugin; plugin=$(get_plugin_for_asset "$cname")
    if [[ -n "$plugin" ]] && ! is_plugin_locally_enabled "$plugin"; then
      continue
    fi
    echo "- $(basename "$cmd_file" .md): \`$cmd_file\`" >> "$rule_file"
  done

  {
    echo ""
    echo "## Available Agents (subagent definitions)"
    echo ""
  } >> "$rule_file"
  for agent_file in "$BOOTSTRAP_DIR"/agents/*.md; do
    [[ -f "$agent_file" ]] || continue
    local aname; aname=$(basename "$agent_file" .md)
    local plugin; plugin=$(get_plugin_for_asset "$aname")
    if [[ -n "$plugin" ]] && ! is_plugin_locally_enabled "$plugin"; then
      continue
    fi
    echo "- $(basename "$agent_file" .md): \`$agent_file\`" >> "$rule_file"
  done

  local mcp_servers=""
  if [[ -f "$MCP_REPO" ]]; then
    local enabled_keys=()
    for name in "${PLUGIN_NAMES[@]}"; do
      [[ "${PLUGIN_LOCAL_SEL[$name]:-0}" != "1" ]] && continue
      local keys="${PLUGIN_MCP_KEYS[$name]:-}"
      [[ -z "$keys" ]] && continue
      IFS=',' read -ra ks <<< "$keys"
      enabled_keys+=("${ks[@]}")
    done
    if [[ ${#enabled_keys[@]} -gt 0 ]]; then
      mcp_servers=$(IFS=', '; echo "${enabled_keys[*]}")
    fi
  fi
  if [[ -n "$mcp_servers" ]]; then
    {
      echo ""
      echo "## MCP Servers"
      echo ""
      echo "Configured MCP servers: $mcp_servers"
      echo "See \`$BOOTSTRAP_DIR/mcp/mcp-inventory.md\` for details."
    } >> "$rule_file"
  fi

  log_installed "generated:$rule_file"
  ok "Generated $rule_file"
}

generate_claude_md() {
  local target_file="$1"
  $DRY_RUN && { printf "${YELLOW}[dry]${NC}   Generate %s\n" "$target_file"; return; }

  mkdir -p "$(dirname "$target_file")"
  cat > "$target_file" << 'HEADER'
# Agent Bootstrap — Available Capabilities

You have access to additional skills, commands, and agents from the agent bootstrap repo.
To use a skill, read its SKILL.md file and follow the instructions within.
To use a command, read the .md file and follow the prompt template.

HEADER

  {
    echo "## Skills"
    echo ""
  } >> "$target_file"
  for skill_dir in "$BOOTSTRAP_DIR"/skills/*/; do
    [[ -f "$skill_dir/SKILL.md" ]] || continue
    local name; name=$(basename "$skill_dir")
    local plugin; plugin=$(get_plugin_for_asset "$name")
    if [[ -n "$plugin" ]] && ! is_plugin_locally_enabled "$plugin"; then
      continue
    fi
    local desc=""
    desc=$(head -20 "$skill_dir/SKILL.md" | grep -i "^description:" | head -1 | sed 's/^description:\s*//' || true)
    [[ -z "$desc" ]] && desc=$(head -5 "$skill_dir/SKILL.md" | grep "^#" | head -1 | sed 's/^#\+\s*//' || true)
    echo "- **$name**: \`${skill_dir}SKILL.md\`${desc:+ — $desc}" >> "$target_file"
  done

  {
    echo ""
    echo "## Commands (prompt templates)"
    echo ""
  } >> "$target_file"
  for cmd_file in "$BOOTSTRAP_DIR"/commands/*.md; do
    [[ -f "$cmd_file" ]] || continue
    local cname; cname=$(basename "$cmd_file" .md)
    local plugin; plugin=$(get_plugin_for_asset "$cname")
    if [[ -n "$plugin" ]] && ! is_plugin_locally_enabled "$plugin"; then continue; fi
    echo "- $(basename "$cmd_file" .md): \`$cmd_file\`" >> "$target_file"
  done

  {
    echo ""
    echo "## Agents (subagent definitions)"
    echo ""
  } >> "$target_file"
  for agent_file in "$BOOTSTRAP_DIR"/agents/*.md; do
    [[ -f "$agent_file" ]] || continue
    local aname; aname=$(basename "$agent_file" .md)
    local plugin; plugin=$(get_plugin_for_asset "$aname")
    if [[ -n "$plugin" ]] && ! is_plugin_locally_enabled "$plugin"; then continue; fi
    echo "- $(basename "$agent_file" .md): \`$agent_file\`" >> "$target_file"
  done

  local mcp_servers=""
  local enabled_keys=()
  for name in "${PLUGIN_NAMES[@]}"; do
    [[ "${PLUGIN_LOCAL_SEL[$name]:-0}" != "1" ]] && continue
    local keys="${PLUGIN_MCP_KEYS[$name]:-}"
    [[ -z "$keys" ]] && continue
    IFS=',' read -ra ks <<< "$keys"
    enabled_keys+=("${ks[@]}")
  done
  if [[ ${#enabled_keys[@]} -gt 0 ]]; then
    mcp_servers=$(IFS=', '; echo "${enabled_keys[*]}")
  fi
  if [[ -n "$mcp_servers" ]]; then
    {
      echo ""
      echo "## MCP Servers"
      echo ""
      echo "Configured servers: $mcp_servers"
      echo "See \`$BOOTSTRAP_DIR/mcp/mcp-inventory.md\` for details."
    } >> "$target_file"
  fi

  log_installed "generated:$target_file"
  ok "Generated $target_file"
}

generate_codex_agents_md() {
  local target_file="$1"
  $DRY_RUN && { printf "${YELLOW}[dry]${NC}   Generate %s\n" "$target_file"; return; }

  cat > "$target_file" << 'HEADER'
# Global Agent Working Agreement

## Default behavior
- I plan first. Before opening files, I list up to 3 files I need and why.
- I use rg for discovery and open only the smallest relevant file sections.
- I avoid pasting whole files. I quote only the necessary lines.
- I keep diffs minimal and reversible. One focused change at a time.
- I keep command output small (tail/sed ranges). I avoid huge logs.

## Safety
- I ask before destructive commands (rm, git reset --hard, mass delete).
- I ask before installing packages or changing system configuration.

## Definition of done
- I provide a minimal diff and the exact verify commands (tests/lint/build), then I stop.

HEADER

  {
    echo "## Available Skills"
    echo ""
    echo "Skills are available at \`~/.codex/skills/\`. Read any SKILL.md to learn and follow a workflow."
    echo ""
  } >> "$target_file"
  for skill_dir in "$BOOTSTRAP_DIR"/skills/*/; do
    [[ -f "$skill_dir/SKILL.md" ]] || continue
    local name; name=$(basename "$skill_dir")
    local plugin; plugin=$(get_plugin_for_asset "$name")
    if [[ -n "$plugin" ]] && ! is_plugin_locally_enabled "$plugin"; then continue; fi
    local desc=""
    desc=$(head -20 "$skill_dir/SKILL.md" | grep -i "^description:" | head -1 | sed 's/^description:\s*//' || true)
    [[ -z "$desc" ]] && desc=$(head -5 "$skill_dir/SKILL.md" | grep "^#" | head -1 | sed 's/^#\+\s*//' || true)
    echo "- **$name**${desc:+: $desc}" >> "$target_file"
  done

  {
    echo ""
    echo "## Available Commands"
    echo ""
    echo "Prompt templates at \`$BOOTSTRAP_DIR/commands/\`. Read any .md file to execute the workflow."
    echo ""
  } >> "$target_file"
  for cmd_file in "$BOOTSTRAP_DIR"/commands/*.md; do
    [[ -f "$cmd_file" ]] || continue
    local cname; cname=$(basename "$cmd_file" .md)
    local plugin; plugin=$(get_plugin_for_asset "$cname")
    if [[ -n "$plugin" ]] && ! is_plugin_locally_enabled "$plugin"; then continue; fi
    echo "- $(basename "$cmd_file" .md): \`$cmd_file\`" >> "$target_file"
  done

  {
    echo ""
    echo "## Available Agents"
    echo ""
    echo "Subagent definitions at \`$BOOTSTRAP_DIR/agents/\`."
    echo ""
  } >> "$target_file"
  for agent_file in "$BOOTSTRAP_DIR"/agents/*.md; do
    [[ -f "$agent_file" ]] || continue
    local aname; aname=$(basename "$agent_file" .md)
    local plugin; plugin=$(get_plugin_for_asset "$aname")
    if [[ -n "$plugin" ]] && ! is_plugin_locally_enabled "$plugin"; then continue; fi
    echo "- $(basename "$agent_file" .md): \`$agent_file\`" >> "$target_file"
  done

  local enabled_keys=()
  for name in "${PLUGIN_NAMES[@]}"; do
    [[ "${PLUGIN_LOCAL_SEL[$name]:-0}" != "1" ]] && continue
    local keys="${PLUGIN_MCP_KEYS[$name]:-}"
    [[ -z "$keys" ]] && continue
    IFS=',' read -ra ks <<< "$keys"
    enabled_keys+=("${ks[@]}")
  done
  if [[ ${#enabled_keys[@]} -gt 0 ]]; then
    local mcp_servers
    mcp_servers=$(IFS=', '; echo "${enabled_keys[*]}")
    {
      echo ""
      echo "## MCP Servers"
      echo ""
      echo "Configured servers: $mcp_servers"
      echo "See \`$BOOTSTRAP_DIR/mcp/mcp-inventory.md\` for details."
    } >> "$target_file"
  fi

  log_installed "file:$target_file"
  ok "Generated $target_file"
}

# ---------------------------------------------------------------------------
# TUI — Plugin menu (adapted from dotfiles interactive pattern)
# ---------------------------------------------------------------------------
_DESC_LINES=2

_plugin_description() {
  local name="$1"
  local sk="${PLUGIN_SKILLS[$name]:-0}" ru="${PLUGIN_RULES[$name]:-0}"
  local ag="${PLUGIN_AGENTS[$name]:-0}" cm="${PLUGIN_COMMANDS[$name]:-0}"
  local hk="${PLUGIN_HOOKS[$name]:-0}" mk="${PLUGIN_MCP_KEYS[$name]:-}"
  local parts=()
  [[ $sk -gt 0 ]] && parts+=("${sk} skill(s)")
  [[ $ru -gt 0 ]] && parts+=("${ru} rule(s)")
  [[ $ag -gt 0 ]] && parts+=("${ag} agent(s)")
  [[ $cm -gt 0 ]] && parts+=("${cm} command(s)")
  [[ $hk -gt 0 ]] && parts+=("hooks")
  if [[ -n "$mk" ]]; then
    local mc=0
    IFS=',' read -ra _tmp <<< "$mk"
    mc=${#_tmp[@]}
    parts+=("${mc} MCP (${mk})")
  fi
  if [[ ${#parts[@]} -gt 0 ]]; then
    echo "${parts[*]}"
  else
    echo "No assets"
  fi
  local src_label="cache"
  [[ "${PLUGIN_IN_REPO[$name]:-0}" == "1" ]] && src_label="in repo"
  [[ "${PLUGIN_SOURCE[$name]:-}" == "cursor-native" ]] && src_label="built-in"
  echo "Source: ${src_label}"
}

_draw_plugin_menu() {
  local cur=$1 col=$2 status=$3
  local count=${#PLUGIN_NAMES[@]}

  printf "\n  \e[1m=== Plugin Manager ===\e[0m\n"
  printf "  ↑/↓ navigate   Space toggle   Tab switch column   a all   n none   Enter confirm   q back\n\n"
  printf "  ${DIM}     Repo Local  Plugin${NC}\n"

  for i in "${!PLUGIN_NAMES[@]}"; do
    local name="${PLUGIN_NAMES[$i]}"
    local repo_mark="x"; [[ "${PLUGIN_REPO_SEL[$name]}" == "0" ]] && repo_mark=" "
    local local_mark="x"; [[ "${PLUGIN_LOCAL_SEL[$name]}" == "0" ]] && local_mark=" "
    [[ "${PLUGIN_SOURCE[$name]:-}" == "cursor-native" ]] && local_mark="*"

    local prefix="  "
    if [[ $i -eq $cur ]]; then
      local repo_col="[${repo_mark}]" local_col="[${local_mark}]"
      if [[ "$col" == "repo" ]]; then
        repo_col="${REVERSE}[${repo_mark}]${NC}${BOLD}"
      else
        local_col="${REVERSE}[${local_mark}]${NC}${BOLD}"
      fi
      printf "  ${BOLD}> %2d. ${repo_col} ${local_col}  %-24s${NC}\e[K\n" "$((i + 1))" "$name"
    else
      printf "    %2d. [%s] [%s]  %s\e[K\n" "$((i + 1))" "$repo_mark" "$local_mark" "$name"
    fi
  done

  if [[ -n "$status" ]]; then
    printf "\n  \e[33m%s\e[0m\e[K\n" "$status"
  else
    printf "\n\e[K\n"
  fi

  local active_name="${PLUGIN_NAMES[$cur]}"
  local col_label="Repo"; [[ "$col" == "local" ]] && col_label="Local"
  local desc_lines=()
  mapfile -t desc_lines < <(_plugin_description "$active_name")
  printf "  \e[36mColumn: [%s]  |  %s\e[0m\e[K\n" "$col_label" "${desc_lines[0]:-}"
  local j
  for j in $(seq 1 $((_DESC_LINES - 1))); do
    if [[ $j -lt ${#desc_lines[@]} ]]; then
      printf "  \e[36m%s\e[0m\e[K\n" "              ${desc_lines[$j]}"
    else
      printf "\e[K\n"
    fi
  done
}

plugin_menu() {
  local count=${#PLUGIN_NAMES[@]}
  [[ $count -eq 0 ]] && { warn "No plugins found"; return; }

  local cursor=0
  local active_col="repo"
  local status_msg=""
  local menu_lines=$((count + 7 + _DESC_LINES))

  tput civis 2>/dev/null || true
  _draw_plugin_menu 0 "$active_col" ""

  while true; do
    local key seq
    IFS= read -rsn1 key < /dev/tty

    case "$key" in
      $'\e')
        IFS= read -rsn2 -t 0.1 seq < /dev/tty || true
        case "${seq:-}" in
          '[A') [[ $cursor -gt 0 ]] && cursor=$((cursor - 1)); status_msg="" ;;
          '[B') [[ $cursor -lt $((count - 1)) ]] && cursor=$((cursor + 1)); status_msg="" ;;
        esac
        ;;
      $'\t')
        [[ "$active_col" == "repo" ]] && active_col="local" || active_col="repo"
        status_msg="Switched to ${active_col} column"
        ;;
      ' ')
        local name="${PLUGIN_NAMES[$cursor]}"
        if [[ "$active_col" == "repo" ]]; then
          if [[ "${PLUGIN_REPO_SEL[$name]}" == "1" ]]; then
            PLUGIN_REPO_SEL["$name"]=0
            status_msg="Disabled $name in repo"
          else
            PLUGIN_REPO_SEL["$name"]=1
            status_msg="Enabled $name in repo"
          fi
        else
          if [[ "${PLUGIN_SOURCE[$name]:-}" == "cursor-native" ]]; then
            status_msg="cursor-native is always local (built-in)"
          elif [[ "${PLUGIN_LOCAL_SEL[$name]}" == "1" ]]; then
            PLUGIN_LOCAL_SEL["$name"]=0
            status_msg="Disabled $name locally"
          else
            PLUGIN_LOCAL_SEL["$name"]=1
            status_msg="Enabled $name locally"
          fi
        fi
        ;;
      '')
        break
        ;;
      q|Q)
        tput cnorm 2>/dev/null || true
        return 1
        ;;
      a|A)
        for n in "${PLUGIN_NAMES[@]}"; do
          if [[ "$active_col" == "repo" ]]; then
            PLUGIN_REPO_SEL["$n"]=1
          else
            [[ "${PLUGIN_SOURCE[$n]:-}" == "cursor-native" ]] && continue
            PLUGIN_LOCAL_SEL["$n"]=1
          fi
        done
        status_msg="All enabled in $active_col"
        ;;
      n|N)
        for n in "${PLUGIN_NAMES[@]}"; do
          if [[ "$active_col" == "repo" ]]; then
            PLUGIN_REPO_SEL["$n"]=0
          else
            [[ "${PLUGIN_SOURCE[$n]:-}" == "cursor-native" ]] && continue
            PLUGIN_LOCAL_SEL["$n"]=0
          fi
        done
        status_msg="All disabled in $active_col"
        ;;
      *)
        continue
        ;;
    esac

    printf "\e[%dA" "$menu_lines"
    _draw_plugin_menu "$cursor" "$active_col" "$status_msg"
  done

  tput cnorm 2>/dev/null || true
}

# ---------------------------------------------------------------------------
# Confirmation & change computation
# ---------------------------------------------------------------------------
declare -a CHANGES_REPO_ADD=()
declare -a CHANGES_REPO_REMOVE=()
declare -a CHANGES_LOCAL_ADD=()
declare -a CHANGES_LOCAL_REMOVE=()

compute_changes() {
  CHANGES_REPO_ADD=()
  CHANGES_REPO_REMOVE=()
  CHANGES_LOCAL_ADD=()
  CHANGES_LOCAL_REMOVE=()

  for name in "${PLUGIN_NAMES[@]}"; do
    local was_repo="${PLUGIN_IN_REPO[$name]:-0}"
    local was_local="${PLUGIN_IN_LOCAL[$name]:-0}"
    local want_repo="${PLUGIN_REPO_SEL[$name]:-0}"
    local want_local="${PLUGIN_LOCAL_SEL[$name]:-0}"

    [[ "$want_repo" == "1" && "$was_repo" == "0" ]] && CHANGES_REPO_ADD+=("$name")
    [[ "$want_repo" == "0" && "$was_repo" == "1" ]] && CHANGES_REPO_REMOVE+=("$name")
    [[ "$want_local" == "1" && "$was_local" == "0" ]] && CHANGES_LOCAL_ADD+=("$name")
    [[ "$want_local" == "0" && "$was_local" == "1" ]] && CHANGES_LOCAL_REMOVE+=("$name")
  done
}

show_confirmation() {
  echo ""
  printf "  ${BOLD}=== Confirm Changes ===${NC}\n"
  echo ""

  local total=$((${#CHANGES_REPO_ADD[@]} + ${#CHANGES_REPO_REMOVE[@]} + ${#CHANGES_LOCAL_ADD[@]} + ${#CHANGES_LOCAL_REMOVE[@]}))

  if [[ ${#CHANGES_REPO_ADD[@]} -gt 0 ]]; then
    printf "  ${GREEN}Add to repo:${NC}      "
    printf "%s " "${CHANGES_REPO_ADD[@]}"
    echo ""
  fi
  if [[ ${#CHANGES_REPO_REMOVE[@]} -gt 0 ]]; then
    printf "  ${RED}Remove from repo:${NC} "
    printf "%s " "${CHANGES_REPO_REMOVE[@]}"
    echo ""
  fi
  if [[ ${#CHANGES_LOCAL_ADD[@]} -gt 0 ]]; then
    printf "  ${GREEN}Deploy locally:${NC}   "
    printf "%s " "${CHANGES_LOCAL_ADD[@]}"
    echo ""
  fi
  if [[ ${#CHANGES_LOCAL_REMOVE[@]} -gt 0 ]]; then
    printf "  ${RED}Remove locally:${NC}   "
    printf "%s " "${CHANGES_LOCAL_REMOVE[@]}"
    echo ""
  fi

  # Check for hash updates — distinguish cache-newer vs repo-newer
  local cache_updates=()
  local repo_newer=()
  for name in "${PLUGIN_NAMES[@]}"; do
    [[ "${PLUGIN_REPO_SEL[$name]:-0}" != "1" ]] && continue
    [[ "${PLUGIN_IN_REPO[$name]:-0}" != "1" ]] && continue
    local manifest_hash; manifest_hash=$(manifest_plugin_hash "$name")
    local cache_hash="${PLUGIN_CACHE_HASH[$name]:-}"
    if [[ -n "$cache_hash" ]] && [[ -n "$manifest_hash" ]] && [[ "$cache_hash" != "$manifest_hash" ]]; then
      if _cache_is_newer "$name"; then
        cache_updates+=("$name")
      else
        repo_newer+=("$name")
      fi
    fi
  done
  if [[ ${#cache_updates[@]} -gt 0 ]]; then
    printf "  ${YELLOW}Update from cache:${NC} "
    printf "%s " "${cache_updates[@]}"
    echo ""
    total=$((total + ${#cache_updates[@]}))
  fi
  if [[ ${#repo_newer[@]} -gt 0 ]]; then
    printf "  ${DIM}Repo is newer:${NC}    "
    printf "%s " "${repo_newer[@]}"
    printf "${DIM}(keeping repo version)${NC}\n"
  fi

  if [[ $total -eq 0 ]]; then
    echo "  No changes detected. Config files will be regenerated."
  fi
  echo ""
}

confirm_loop() {
  while true; do
    compute_changes
    show_confirmation
    read -rp "  [c]onfirm  [e]dit  [q]uit: " answer < /dev/tty
    case "$answer" in
      c|C) return 0 ;;
      e|E) plugin_menu ;;
      q|Q) echo "  Aborted."; return 1 ;;
      *)   echo "    Invalid choice." ;;
    esac
  done
}

# ---------------------------------------------------------------------------
# Execute sync
# ---------------------------------------------------------------------------
execute_sync() {
  local did_repo_change=false

  # 1. Pull new plugins into repo
  for name in "${CHANGES_REPO_ADD[@]:-}"; do
    [[ -z "$name" ]] && continue
    local hash="${PLUGIN_CACHE_HASH[$name]:-}"
    if [[ -z "$hash" ]]; then
      warn "No cache entry for $name — cannot pull into repo"
      continue
    fi
    header "Adding to repo: $name"
    pull_plugin_to_repo "$name" "$hash"
    did_repo_change=true
  done

  # 2. Remove plugins from repo
  for name in "${CHANGES_REPO_REMOVE[@]:-}"; do
    [[ -z "$name" ]] && continue
    header "Removing from repo: $name"
    remove_plugin_from_repo "$name"
    did_repo_change=true
  done

  # 3. Update plugins where cache is genuinely newer than repo
  for name in "${PLUGIN_NAMES[@]}"; do
    [[ "${PLUGIN_REPO_SEL[$name]:-0}" != "1" ]] && continue
    [[ "${PLUGIN_IN_REPO[$name]:-0}" != "1" ]] && continue
    local manifest_hash; manifest_hash=$(manifest_plugin_hash "$name")
    local cache_hash="${PLUGIN_CACHE_HASH[$name]:-}"
    if [[ -n "$cache_hash" ]] && [[ -n "$manifest_hash" ]] && [[ "$cache_hash" != "$manifest_hash" ]]; then
      if _cache_is_newer "$name"; then
        header "Updating plugin: $name (cache is newer)"
        pull_plugin_to_repo "$name" "$cache_hash"
        did_repo_change=true
      else
        skip "Keeping repo version of $name (repo is newer than local cache)"
      fi
    fi
  done

  # 4. Save local config
  save_local_config

  # 5. Sync global configs
  header "Syncing global configs"

  if [[ -d "$HOME/.cursor" ]]; then
    sync_target_mcp "$HOME/.cursor/mcp.json"
    ok "Cursor MCP synced"
  fi
  if [[ -d "$HOME/.claude" ]]; then
    sync_target_mcp "$HOME/.claude/mcp.json"
    ok "Claude Code MCP synced"
  fi
  if [[ -d "$HOME/.codex" ]]; then
    sync_codex_skills
    ok "Codex skills synced"
    generate_codex_agents_md "$HOME/.codex/AGENTS.md"
  fi
  if [[ -d "$HOME/.claude" ]]; then
    generate_claude_md "$HOME/.claude/CLAUDE.md"
  fi

  # 6. Shell profile
  local profile="$HOME/.bashrc"
  local marker="# agent_bootstrap"
  if ! grep -qF "$marker" "$profile" 2>/dev/null; then
    echo "" >> "$profile"
    echo "export AGENT_BOOTSTRAP_HOME=\"$BOOTSTRAP_DIR\" $marker" >> "$profile"
    log_installed "profile-line:$profile"
    ok "Added AGENT_BOOTSTRAP_HOME to $profile"
  fi

  # 7. Refresh tracked workspaces
  refresh_workspaces

  # 8. Update manifest timestamp
  update_manifest_timestamp

  echo ""
  ok "Sync complete."

  # 9. Offer git push if repo changed
  if $did_repo_change; then
    offer_git_push
  fi
}

# ---------------------------------------------------------------------------
# Refresh tracked workspaces
# ---------------------------------------------------------------------------
refresh_workspaces() {
  [[ -f "$INSTALLED_LOG" ]] || return 0

  local workspaces=()
  while IFS= read -r line; do
    case "$line" in
      generated:*rules/bootstrap-skills.mdc)
        local ws_path="${line#generated:}"
        ws_path="${ws_path%/.cursor/rules/bootstrap-skills.mdc}"
        [[ -d "$ws_path" ]] && workspaces+=("$ws_path")
        ;;
    esac
  done < "$INSTALLED_LOG"

  if [[ ${#workspaces[@]} -gt 0 ]]; then
    header "Refreshing workspaces"
    for ws in "${workspaces[@]}"; do
      cmd_workspace "$ws" 2>/dev/null || true
      ok "Refreshed: $ws"
    done
  fi
}

# ---------------------------------------------------------------------------
# Git operations
# ---------------------------------------------------------------------------
offer_git_push() {
  echo ""
  header "Repo changes detected"
  cd "$BOOTSTRAP_DIR"
  git --no-pager diff --stat 2>/dev/null || true
  echo ""

  local msg_parts=()
  [[ ${#CHANGES_REPO_ADD[@]} -gt 0 ]] && msg_parts+=("add ${CHANGES_REPO_ADD[*]}")
  [[ ${#CHANGES_REPO_REMOVE[@]} -gt 0 ]] && msg_parts+=("remove ${CHANGES_REPO_REMOVE[*]}")
  local has_updates=false
  for name in "${PLUGIN_NAMES[@]}"; do
    [[ "${PLUGIN_REPO_SEL[$name]:-0}" != "1" ]] && continue
    local mh; mh=$(manifest_plugin_hash "$name")
    local ch="${PLUGIN_CACHE_HASH[$name]:-}"
    if [[ -n "$ch" ]] && [[ -n "$mh" ]] && [[ "$ch" != "$mh" ]]; then
      has_updates=true; break
    fi
  done
  $has_updates && msg_parts+=("update plugins")
  [[ ${#msg_parts[@]} -eq 0 ]] && msg_parts+=("sync plugins")

  local commit_msg="sync: $(IFS=', '; echo "${msg_parts[*]}")"
  info "Commit message: $commit_msg"
  echo ""

  read -rp "  [c]ommit + push  [s]kip: " answer < /dev/tty
  case "$answer" in
    c|C)
      git add -A
      git commit -m "$commit_msg" || true
      git push || warn "Push failed — you may need to push manually"
      ok "Changes committed and pushed"
      ;;
    *)
      info "Skipped. Commit manually when ready."
      ;;
  esac
}

# ---------------------------------------------------------------------------
# Status command
# ---------------------------------------------------------------------------
cmd_status() {
  header "Agent Bootstrap Status"

  echo ""
  info "Bootstrap home: $BOOTSTRAP_DIR"
  local skill_count rule_count agent_count cmd_count
  skill_count=$(find "$BOOTSTRAP_DIR/skills" -name SKILL.md 2>/dev/null | wc -l)
  rule_count=$(find "$BOOTSTRAP_DIR/rules" -name '*.mdc' 2>/dev/null | wc -l)
  agent_count=$(find "$BOOTSTRAP_DIR/agents" -name '*.md' 2>/dev/null | wc -l)
  cmd_count=$(find "$BOOTSTRAP_DIR/commands" -name '*.md' 2>/dev/null | wc -l)
  info "Skills: $skill_count  Rules: $rule_count  Agents: $agent_count  Commands: $cmd_count"

  echo ""
  header "Global installations"

  if [[ -f "$HOME/.cursor/mcp.json" ]]; then
    local servers
    servers=$(jq -r '.mcpServers | keys | join(", ")' "$HOME/.cursor/mcp.json" 2>/dev/null || echo "(parse error)")
    ok "Cursor MCP: $servers"
  else
    warn "Cursor MCP: not configured"
  fi

  if [[ -d "$HOME/.codex" ]]; then
    local codex_skills=0
    for s in "$HOME/.codex/skills"/*/; do
      local s_path="${s%/}"
      [[ -L "$s_path" ]] || continue
      local link_target; link_target=$(readlink -f "$s_path" 2>/dev/null || true)
      [[ "$link_target" == "$BOOTSTRAP_DIR"* ]] && codex_skills=$((codex_skills + 1))
    done
    ok "Codex skills linked: $codex_skills"
    [[ -f "$HOME/.codex/AGENTS.md" ]] && ok "Codex AGENTS.md: present" || warn "Codex AGENTS.md: missing"
  else
    warn "Codex: not installed"
  fi

  if [[ -d "$HOME/.claude" ]]; then
    [[ -f "$HOME/.claude/mcp.json" ]] && ok "Claude Code MCP: configured" || warn "Claude Code MCP: not configured"
    [[ -f "$HOME/.claude/CLAUDE.md" ]] && ok "Claude Code CLAUDE.md: present" || warn "Claude Code CLAUDE.md: missing"
  else
    info "Claude Code: not installed"
  fi

  if grep -qF "AGENT_BOOTSTRAP_HOME" "$HOME/.bashrc" 2>/dev/null; then
    ok "AGENT_BOOTSTRAP_HOME: set in .bashrc"
  else
    warn "AGENT_BOOTSTRAP_HOME: not in .bashrc"
  fi

  if [[ -f "$LOCAL_CONFIG" ]]; then
    local enabled=0 disabled=0
    while IFS='=' read -r pname pval; do
      [[ -z "$pname" || "$pname" == \#* ]] && continue
      [[ "$pval" == "1" ]] && enabled=$((enabled + 1)) || disabled=$((disabled + 1))
    done < "$LOCAL_CONFIG"
    ok "Local config: $enabled enabled, $disabled disabled"
  else
    info "Local config: not set (all plugins deployed)"
  fi

  echo ""
  header "Workspace installations"

  local ws_count=0
  if [[ -f "$INSTALLED_LOG" ]]; then
    while IFS= read -r line; do
      case "$line" in
        generated:*rules/bootstrap-skills.mdc)
          local ws_path="${line#generated:}"
          ws_path="${ws_path%/.cursor/rules/bootstrap-skills.mdc}"
          ok "Workspace: $ws_path"
          ws_count=$((ws_count + 1))
          ;;
      esac
    done < "$INSTALLED_LOG"
  fi
  if [[ $ws_count -eq 0 ]]; then
    info "No workspaces configured yet"
  fi
}

# ---------------------------------------------------------------------------
# Backward-compatible commands: global, workspace, all, uninstall
# ---------------------------------------------------------------------------
cmd_global() {
  migrate_manifest_v2
  discover_plugins

  if [[ ! -f "$LOCAL_CONFIG" ]]; then
    for name in "${PLUGIN_NAMES[@]}"; do
      PLUGIN_LOCAL_SEL["$name"]=1
    done
  fi

  header "Global setup"

  if [[ -d "$HOME/.cursor" ]]; then
    header "Cursor: MCP servers"
    sync_target_mcp "$HOME/.cursor/mcp.json"
    ok "Cursor MCP configured"
  else
    skip "~/.cursor not found"
  fi

  if [[ -d "$HOME/.codex" ]]; then
    header "Codex: global AGENTS.md"
    if [[ -f "$HOME/.codex/AGENTS.md" ]] && ! $FORCE; then
      skip "~/.codex/AGENTS.md already exists (use --force to overwrite)"
    else
      generate_codex_agents_md "$HOME/.codex/AGENTS.md"
    fi
    header "Codex: skills"
    sync_codex_skills
    ok "Codex skills synced"
  else
    skip "~/.codex not found"
  fi

  if [[ -d "$HOME/.claude" ]]; then
    header "Claude Code: MCP servers"
    sync_target_mcp "$HOME/.claude/mcp.json"
    header "Claude Code: global CLAUDE.md"
    if [[ -f "$HOME/.claude/CLAUDE.md" ]] && ! $FORCE; then
      skip "~/.claude/CLAUDE.md already exists (use --force to overwrite)"
    else
      generate_claude_md "$HOME/.claude/CLAUDE.md"
    fi
  else
    skip "~/.claude not found"
  fi

  header "Shell profile"
  local profile="$HOME/.bashrc"
  local marker="# agent_bootstrap"
  local export_line="export AGENT_BOOTSTRAP_HOME=\"$BOOTSTRAP_DIR\" $marker"
  if grep -qF "$marker" "$profile" 2>/dev/null; then
    skip "AGENT_BOOTSTRAP_HOME already in $profile"
  else
    if $DRY_RUN; then
      printf "${YELLOW}[dry]${NC}   Append to %s\n" "$profile"
    else
      echo "" >> "$profile"
      echo "$export_line" >> "$profile"
      log_installed "profile-line:$profile"
      ok "Added AGENT_BOOTSTRAP_HOME to $profile"
    fi
  fi

  echo ""
  ok "Global setup complete. Run 'source ~/.bashrc' to load env vars."
}

cmd_workspace() {
  local target="$1"
  target="$(cd "$target" 2>/dev/null && pwd)" || { err "Directory not found: $1"; return 1; }
  [[ "$target" == "$BOOTSTRAP_DIR" ]] && { skip "Skipping bootstrap repo itself"; return 0; }

  header "Workspace: $target"

  # Rules (selective by plugin)
  info "Symlinking rules"
  run mkdir -p "$target/.cursor/rules"
  for rule in "$BOOTSTRAP_DIR"/rules/*.mdc; do
    [[ -f "$rule" ]] || continue
    local rule_base; rule_base=$(basename "$rule" .mdc)
    local plugin; plugin=$(get_plugin_for_asset "$rule_base")
    local dst="$target/.cursor/rules/$(basename "$rule")"

    if [[ -n "$plugin" ]] && ! is_plugin_locally_enabled "$plugin"; then
      [[ -L "$dst" ]] && rm "$dst"
      continue
    fi
    symlink_file "$rule" "$dst"
  done

  # Skills rule (generated catalog)
  generate_skills_rule "$target"

  # MCP (selective)
  info "Setting up workspace MCP"
  run mkdir -p "$target/.cursor"
  sync_target_mcp "$target/.cursor/mcp.json"

  # CLAUDE.md (primary generated file)
  local claude_md="$target/CLAUDE.md"
  if [[ -f "$claude_md" ]] && [[ ! -L "$claude_md" ]] && ! $FORCE; then
    skip "$claude_md already exists (use --force to overwrite)"
  else
    [[ -L "$claude_md" ]] && rm "$claude_md"
    generate_claude_md "$claude_md"
  fi

  # AGENTS.md -> CLAUDE.md symlink
  local agents_md="$target/AGENTS.md"
  if [[ -e "$agents_md" ]] && [[ ! -L "$agents_md" ]] && ! $FORCE; then
    skip "$agents_md exists as a real file, skipping symlink"
  else
    [[ -L "$agents_md" ]] && rm "$agents_md"
    [[ -e "$agents_md" ]] && $FORCE && rm "$agents_md"
    if [[ ! -e "$agents_md" ]]; then
      ln -sf CLAUDE.md "$agents_md"
      log_installed "symlink:$agents_md"
    fi
  fi

  # .gitignore
  local gitignore="$target/.gitignore"
  local entries=(".cursor/" "CLAUDE.md" "AGENTS.md")
  if [[ -f "$gitignore" ]]; then
    for entry in "${entries[@]}"; do
      local bare="${entry%/}"
      if ! grep -qxF "$entry" "$gitignore" 2>/dev/null && ! grep -qxF "$bare" "$gitignore" 2>/dev/null; then
        $DRY_RUN && printf "${YELLOW}[dry]${NC}   Append '%s' to %s\n" "$entry" "$gitignore" && continue
        echo "$entry" >> "$gitignore"
      fi
    done
  else
    if $DRY_RUN; then
      printf "${YELLOW}[dry]${NC}   Create %s\n" "$gitignore"
    else
      printf '%s\n' "${entries[@]}" > "$gitignore"
      ok "Created $gitignore"
    fi
  fi

  echo ""
  ok "Workspace $target setup complete."
}

cmd_all() {
  local parent="$1"
  parent="$(cd "$parent" 2>/dev/null && pwd)" || { err "Directory not found: $1"; return 1; }

  header "Setting up all git repos under $parent"
  local count=0
  for dir in "$parent"/*/; do
    [[ -d "$dir/.git" ]] || continue
    dir="$(cd "$dir" && pwd)"
    [[ "$dir" == "$BOOTSTRAP_DIR" ]] && { skip "Skipping bootstrap repo itself"; continue; }
    cmd_workspace "$dir"
    count=$((count + 1))
  done

  echo ""
  if [[ $count -eq 0 ]]; then
    warn "No git repos found under $parent"
  else
    ok "Set up $count workspace(s) under $parent"
  fi
}

cmd_uninstall() {
  header "Uninstalling agent_bootstrap"

  if [[ ! -f "$INSTALLED_LOG" ]]; then
    warn "No installation log found, nothing to uninstall"
    return 0
  fi

  while IFS= read -r line; do
    local type="${line%%:*}" path="${line#*:}"
    case "$type" in
      symlink)
        [[ -L "$path" ]] && { run rm "$path"; ok "Removed symlink: $path"; } ;;
      generated)
        [[ -f "$path" ]] && { run rm "$path"; ok "Removed generated: $path"; } ;;
      file)
        [[ -f "$path" ]] && { run rm "$path"; ok "Removed file: $path"; } ;;
      mcp-merge)
        warn "Cannot auto-undo MCP merge for $path — edit manually" ;;
      profile-line)
        if ! $DRY_RUN; then
          local marker="# agent_bootstrap"
          if grep -qF "$marker" "$path" 2>/dev/null; then
            sed -i "/$marker/d" "$path"
            ok "Removed AGENT_BOOTSTRAP_HOME from $path"
          fi
        else
          printf "${YELLOW}[dry]${NC}   Remove AGENT_BOOTSTRAP_HOME from %s\n" "$path"
        fi
        ;;
    esac
  done < "$INSTALLED_LOG"

  if ! $DRY_RUN; then
    rm -f "$INSTALLED_LOG"
    rm -f "$LOCAL_CONFIG"
    ok "Removed installation log"
  fi

  echo ""
  ok "Uninstall complete."
}

# ---------------------------------------------------------------------------
# Interactive mode — workspace management
# ---------------------------------------------------------------------------
_get_tracked_workspaces() {
  TRACKED_WS=()
  [[ -f "$INSTALLED_LOG" ]] || return 0
  while IFS= read -r line; do
    case "$line" in
      generated:*rules/bootstrap-skills.mdc)
        local ws_path="${line#generated:}"
        ws_path="${ws_path%/.cursor/rules/bootstrap-skills.mdc}"
        [[ "$ws_path" == "$BOOTSTRAP_DIR" ]] && continue
        TRACKED_WS+=("$ws_path")
        ;;
    esac
  done < "$INSTALLED_LOG"
}

cmd_workspaces_interactive() {
  discover_plugins

  while true; do
    _get_tracked_workspaces
    header "Workspaces"

    if [[ ${#TRACKED_WS[@]} -gt 0 ]]; then
      echo ""
      info "Currently tracked workspaces:"
      local i=1
      for ws in "${TRACKED_WS[@]}"; do
        if [[ -d "$ws" ]]; then
          printf "    %2d. ${GREEN}●${NC} %s\n" "$i" "$ws"
        else
          printf "    %2d. ${RED}✗${NC} %s ${DIM}(missing)${NC}\n" "$i" "$ws"
        fi
        i=$((i + 1))
      done
    else
      echo ""
      info "No workspaces tracked yet."
    fi

    echo ""
    printf "  ${BOLD}Options:${NC}\n"
    echo "    [a] Add a workspace or scan a parent directory"
    echo "    [r] Remove a stale/missing workspace"
    echo "    [q] Back to main menu"
    echo ""

    local action
    read -rsn1 -p "  Choose: " action < /dev/tty
    echo ""

    case "$action" in
      a|A)
        echo ""
        read -rp "  Path (workspace or parent dir): " ws_path < /dev/tty
        [[ -z "$ws_path" ]] && continue

        # Expand ~ and resolve
        ws_path="${ws_path/#\~/$HOME}"
        ws_path="$(cd "$ws_path" 2>/dev/null && pwd)" || { err "Directory not found: $ws_path"; continue; }

        if [[ -d "$ws_path/.git" ]]; then
          header "Setting up workspace: $ws_path"
          cmd_workspace "$ws_path"
        else
          local repos=()
          for dir in "$ws_path"/*/; do
            [[ -d "$dir/.git" ]] || continue
            dir="$(cd "$dir" && pwd)"
            [[ "$dir" == "$BOOTSTRAP_DIR" ]] && continue
            repos+=("$dir")
          done

          if [[ ${#repos[@]} -eq 0 ]]; then
            warn "No git repos found under $ws_path"
            continue
          fi

          info "Found ${#repos[@]} git repo(s) under $ws_path:"
          for r in "${repos[@]}"; do
            echo "    $(basename "$r")"
          done
          echo ""
          read -rp "  Set up all of them? [y/n]: " yn < /dev/tty
          case "$yn" in
            y|Y)
              for r in "${repos[@]}"; do
                cmd_workspace "$r"
              done
              ok "Set up ${#repos[@]} workspace(s)"
              ;;
            *) info "Skipped." ;;
          esac
        fi
        ;;
      r|R)
        if [[ ${#TRACKED_WS[@]} -eq 0 ]]; then
          warn "Nothing to remove."
          continue
        fi
        echo ""
        read -rp "  Enter number to remove (or 'all-missing' for stale ones): " choice < /dev/tty
        if [[ "$choice" == "all-missing" ]]; then
          local removed=0
          for ws in "${TRACKED_WS[@]}"; do
            if [[ ! -d "$ws" ]]; then
              local tmp; tmp=$(mktemp)
              grep -v "^generated:${ws}/" "$INSTALLED_LOG" > "$tmp" || true
              grep -v "^symlink:${ws}/" "$tmp" > "$INSTALLED_LOG" || true
              rm -f "$tmp"
              ok "Removed stale: $ws"
              removed=$((removed + 1))
            fi
          done
          [[ $removed -eq 0 ]] && info "No stale workspaces found."
        elif [[ "$choice" =~ ^[0-9]+$ ]] && [[ "$choice" -ge 1 ]] && [[ "$choice" -le ${#TRACKED_WS[@]} ]]; then
          local ws="${TRACKED_WS[$((choice - 1))]}"
          local tmp; tmp=$(mktemp)
          grep -v "^generated:${ws}/" "$INSTALLED_LOG" > "$tmp" || true
          grep -v "^symlink:${ws}/" "$tmp" > "$INSTALLED_LOG" || true
          rm -f "$tmp"
          ok "Removed workspace: $ws"
        else
          warn "Invalid choice."
        fi
        ;;
      q|Q)
        return 0
        ;;
      *)
        continue
        ;;
    esac
  done
}

# ---------------------------------------------------------------------------
# Interactive mode — arrow-key main menu
# ---------------------------------------------------------------------------
MAIN_MENU_ITEMS=("Update" "Initialize" "Workspaces" "Status" "Quit")
MAIN_MENU_DESCS=(
  "Pull latest from GitHub"
  "Manage plugins (add/remove, deploy/undeploy)"
  "Add/remove project folders"
  "Show current installation state"
  "Exit"
)

_draw_main_menu() {
  local cur=$1
  local count=${#MAIN_MENU_ITEMS[@]}

  printf "\n  ${BOLD}=== Agent Bootstrap ===${NC}\n"
  printf "  ↑/↓ navigate   Enter select\n\n"

  for i in "${!MAIN_MENU_ITEMS[@]}"; do
    if [[ $i -eq $cur ]]; then
      printf "  ${BOLD}${REVERSE} %d) %-14s${NC}  ${DIM}%s${NC}\e[K\n" \
        "$((i + 1))" "${MAIN_MENU_ITEMS[$i]}" "${MAIN_MENU_DESCS[$i]}"
    else
      printf "   %d) %-14s  ${DIM}%s${NC}\e[K\n" \
        "$((i + 1))" "${MAIN_MENU_ITEMS[$i]}" "${MAIN_MENU_DESCS[$i]}"
    fi
  done
  printf "\e[K\n"
}

_MAIN_CHOICE=0

main_menu() {
  local count=${#MAIN_MENU_ITEMS[@]}
  local cursor=0
  local menu_lines=$((count + 5))

  tput civis 2>/dev/null || true
  _draw_main_menu 0

  while true; do
    local key seq
    IFS= read -rsn1 key < /dev/tty

    case "$key" in
      $'\e')
        IFS= read -rsn2 -t 0.1 seq < /dev/tty || true
        case "${seq:-}" in
          '[A') [[ $cursor -gt 0 ]] && cursor=$((cursor - 1)) ;;
          '[B') [[ $cursor -lt $((count - 1)) ]] && cursor=$((cursor + 1)) ;;
        esac
        ;;
      '')
        tput cnorm 2>/dev/null || true
        _MAIN_CHOICE=$cursor
        return
        ;;
      *)
        continue
        ;;
    esac

    printf "\e[%dA" "$menu_lines"
    _draw_main_menu "$cursor"
  done
}

cmd_interactive() {
  migrate_manifest_v2

  while true; do
    main_menu

    case "$_MAIN_CHOICE" in
      0)
        header "Updating from GitHub"
        cd "$BOOTSTRAP_DIR"
        git fetch origin
        local branch; branch=$(git branch --show-current 2>/dev/null || echo "main")
        git pull origin "$branch"
        ok "Updated to latest"
        echo ""
        read -rsn1 -p "  Press any key to continue..." < /dev/tty
        ;;
      1)
        _get_tracked_workspaces
        if [[ ${#TRACKED_WS[@]} -eq 0 ]]; then
          echo ""
          warn "No workspaces configured yet. Add at least one workspace first."
          echo ""
          read -rsn1 -p "  Press any key to continue..." < /dev/tty
          cmd_workspaces_interactive
        else
          cmd_initialize
        fi
        echo ""
        read -rsn1 -p "  Press any key to continue..." < /dev/tty
        ;;
      2)
        cmd_workspaces_interactive
        echo ""
        read -rsn1 -p "  Press any key to continue..." < /dev/tty
        ;;
      3)
        cmd_status
        echo ""
        read -rsn1 -p "  Press any key to continue..." < /dev/tty
        ;;
      4)
        echo "  Bye."
        exit 0
        ;;
    esac
  done
}

cmd_initialize() {
  header "Discovering plugins..."
  discover_plugins
  info "Found ${#PLUGIN_NAMES[@]} plugins"
  echo ""

  plugin_menu || return 0
  confirm_loop || return 0
  execute_sync
}

# ---------------------------------------------------------------------------
# Main entry & argument parsing
# ---------------------------------------------------------------------------
usage() {
  printf "${BOLD}agent_bootstrap installer${NC}\n\n"
  cat <<EOF
Usage: $(basename "$0") [command] [options]

Interactive (no args):
  $(basename "$0")              Launch interactive plugin manager

Commands (CI / scripted):
  --global              Set up global configs (MCP, Codex skills, shell env)
  --workspace <path>    Set up a single workspace/repo
  --all <parent-dir>    Set up all git repos under a directory
  --status              Show current installation status
  --uninstall           Remove all installed symlinks and configs

Options:
  --dry-run             Show what would be done without making changes
  --force               Overwrite existing generated files
  -h, --help            Show this help

Examples:
  ./install.sh                          # Interactive mode
  ./install.sh --global
  ./install.sh --workspace ~/ATOM/repo
  ./install.sh --all ~/ATOM/
  ./install.sh --status
EOF
}

args=()
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --force)   FORCE=true ;;
    -h|--help) usage; exit 0 ;;
    *)         args+=("$arg") ;;
  esac
done
set -- "${args[@]:-}"

command="${1:-}"

case "$command" in
  "")
    cmd_interactive
    ;;
  --global|global)
    cmd_global
    ;;
  --workspace|workspace)
    shift
    [[ -z "${1:-}" ]] && { err "Usage: install.sh --workspace <path>"; exit 1; }
    migrate_manifest_v2
    discover_plugins
    cmd_workspace "$1"
    ;;
  --all|all)
    shift
    [[ -z "${1:-}" ]] && { err "Usage: install.sh --all <parent-dir>"; exit 1; }
    migrate_manifest_v2
    discover_plugins
    cmd_all "$1"
    ;;
  --status|status)
    cmd_status
    ;;
  --uninstall|uninstall)
    cmd_uninstall
    ;;
  *)
    usage
    exit 1
    ;;
esac
