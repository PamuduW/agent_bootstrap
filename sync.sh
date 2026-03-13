#!/usr/bin/env bash
set -euo pipefail

BOOTSTRAP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANIFEST="$BOOTSTRAP_DIR/manifest.json"
CURSOR_PLUGIN_CACHE="$HOME/.cursor/plugins/cache/cursor-public"
CODEX_SKILLS_DIR="$HOME/.codex/skills"

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

info()   { printf "${CYAN}[info]${NC}  %s\n" "$*"; }
ok()     { printf "${GREEN}[ok]${NC}    %s\n" "$*"; }
warn()   { printf "${YELLOW}[warn]${NC}  %s\n" "$*"; }
err()    { printf "${RED}[err]${NC}   %s\n" "$*" >&2; }
added()  { printf "${GREEN}[new]${NC}   %s\n" "$*"; }
changed(){ printf "${YELLOW}[upd]${NC}  %s\n" "$*"; }
header() { printf "\n${BOLD}── %s${NC}\n" "$*"; }

# ---------------------------------------------------------------------------
# Pre-checks
# ---------------------------------------------------------------------------

if ! command -v jq &>/dev/null; then
  err "jq is required. Install with: sudo apt install jq"
  exit 1
fi

if [ ! -f "$MANIFEST" ]; then
  err "manifest.json not found at $MANIFEST"
  exit 1
fi

# ---------------------------------------------------------------------------
# Read manifest
# ---------------------------------------------------------------------------

manifest_plugin_hash() {
  jq -r ".sources[\"cursor-plugins\"].plugins[\"$1\"].hash // empty" "$MANIFEST"
}

manifest_codex_skill_exists() {
  jq -e ".sources[\"codex-skills\"].skills[\"$1\"]" "$MANIFEST" &>/dev/null
}

# ---------------------------------------------------------------------------
# Scan cursor plugins
# ---------------------------------------------------------------------------

scan_cursor_plugins() {
  local new_plugins=() updated_plugins=() unchanged_plugins=() removed_plugins=()

  if [ ! -d "$CURSOR_PLUGIN_CACHE" ]; then
    warn "Cursor plugin cache not found at $CURSOR_PLUGIN_CACHE"
    return
  fi

  # Check for new and updated plugins
  for plugin_dir in "$CURSOR_PLUGIN_CACHE"/*/; do
    [ -d "$plugin_dir" ] || continue
    local plugin_name
    plugin_name=$(basename "$plugin_dir")
    local current_hash
    current_hash=$(ls "$plugin_dir" 2>/dev/null | head -1)
    [ -z "$current_hash" ] && continue

    local manifest_hash
    manifest_hash=$(manifest_plugin_hash "$plugin_name")

    if [ -z "$manifest_hash" ]; then
      new_plugins+=("$plugin_name|$current_hash")
    elif [ "$manifest_hash" != "$current_hash" ]; then
      updated_plugins+=("$plugin_name|$manifest_hash|$current_hash")
    else
      unchanged_plugins+=("$plugin_name")
    fi
  done

  # Check for removed plugins
  for plugin_name in $(jq -r '.sources["cursor-plugins"].plugins | keys[]' "$MANIFEST" 2>/dev/null); do
    if [ ! -d "$CURSOR_PLUGIN_CACHE/$plugin_name" ]; then
      removed_plugins+=("$plugin_name")
    fi
  done

  # Report
  header "Cursor Plugins"

  if [ ${#new_plugins[@]} -eq 0 ] && [ ${#updated_plugins[@]} -eq 0 ] && [ ${#removed_plugins[@]} -eq 0 ]; then
    ok "All ${#unchanged_plugins[@]} plugins up to date"
  fi

  for entry in "${new_plugins[@]:-}"; do
    [ -z "$entry" ] && continue
    local name="${entry%%|*}" hash="${entry##*|}"
    local base="$CURSOR_PLUGIN_CACHE/$name/$hash"
    local sk=$(ls "$base/skills/" 2>/dev/null | wc -l)
    local ru=$(ls "$base/rules/" 2>/dev/null | wc -l)
    local ag=$(ls "$base/agents/" 2>/dev/null | wc -l)
    local cm=$(ls "$base/commands/" 2>/dev/null | wc -l)
    added "NEW plugin: $name (hash: ${hash:0:12}...) — skills=$sk rules=$ru agents=$ag commands=$cm"
  done

  for entry in "${updated_plugins[@]:-}"; do
    [ -z "$entry" ] && continue
    IFS='|' read -r name old_hash new_hash <<< "$entry"
    changed "UPDATED plugin: $name (${old_hash:0:12}... -> ${new_hash:0:12}...)"
  done

  for name in "${removed_plugins[@]:-}"; do
    [ -z "$name" ] && continue
    warn "REMOVED plugin: $name (still in bootstrap but not in cache)"
  done

  # Return arrays via globals for pull mode
  _NEW_PLUGINS=("${new_plugins[@]:-}")
  _UPDATED_PLUGINS=("${updated_plugins[@]:-}")
}

# ---------------------------------------------------------------------------
# Scan codex skills
# ---------------------------------------------------------------------------

scan_codex_skills() {
  local new_skills=() existing_skills=()

  header "Codex Skills"

  if [ ! -d "$CODEX_SKILLS_DIR" ]; then
    warn "Codex skills dir not found at $CODEX_SKILLS_DIR"
    return
  fi

  for skill_dir in "$CODEX_SKILLS_DIR"/*/; do
    [ -d "$skill_dir" ] || continue
    local skill_name
    skill_name=$(basename "$skill_dir")

    # Skip system skills
    [[ "$skill_name" == .* ]] && continue

    # Skip skills that are symlinks back to our bootstrap
    local skill_path="${skill_dir%/}"
    if [ -L "$skill_path" ]; then
      local target
      target=$(readlink -f "$skill_path" 2>/dev/null || true)
      [[ "$target" == "$BOOTSTRAP_DIR"* ]] && continue
    fi

    # Check if skill exists in bootstrap
    if [ -d "$BOOTSTRAP_DIR/skills/$skill_name" ]; then
      existing_skills+=("$skill_name")
    else
      if [ -f "$skill_dir/SKILL.md" ]; then
        new_skills+=("$skill_name")
      fi
    fi
  done

  if [ ${#new_skills[@]} -eq 0 ]; then
    ok "No new Codex skills to import"
  fi

  for name in "${new_skills[@]:-}"; do
    [ -z "$name" ] && continue
    added "NEW Codex skill: $name"
  done

  _NEW_CODEX_SKILLS=("${new_skills[@]:-}")
}

# ---------------------------------------------------------------------------
# Export a cursor plugin into bootstrap
# ---------------------------------------------------------------------------

export_plugin() {
  local plugin_name="$1" hash="$2"
  local src="$CURSOR_PLUGIN_CACHE/$plugin_name/$hash"

  if [ ! -d "$src" ]; then
    err "Plugin source not found: $src"
    return 1
  fi

  info "Exporting plugin: $plugin_name"

  # Skills
  if [ -d "$src/skills" ]; then
    for skill_dir in "$src/skills"/*/; do
      [ -d "$skill_dir" ] || continue
      local skill_name
      skill_name=$(basename "$skill_dir")
      local dst="$BOOTSTRAP_DIR/skills/${plugin_name}-${skill_name}"
      if [ -d "$dst" ]; then
        rm -rf "$dst"
      fi
      cp -r "$skill_dir" "$dst"
      ok "  skill: ${plugin_name}-${skill_name}"
    done
  fi

  # Rules
  if [ -d "$src/rules" ]; then
    for rule in "$src/rules"/*.mdc; do
      [ -f "$rule" ] || continue
      local rule_name
      rule_name=$(basename "$rule")
      cp "$rule" "$BOOTSTRAP_DIR/rules/${plugin_name}-${rule_name}"
      ok "  rule: ${plugin_name}-${rule_name}"
    done
  fi

  # Agents
  if [ -d "$src/agents" ]; then
    for agent in "$src/agents"/*.md; do
      [ -f "$agent" ] || continue
      local agent_name
      agent_name=$(basename "$agent")
      cp "$agent" "$BOOTSTRAP_DIR/agents/${plugin_name}-${agent_name}"
      ok "  agent: ${plugin_name}-${agent_name}"
    done
  fi

  # Commands
  if [ -d "$src/commands" ]; then
    for cmd in "$src/commands"/*.md; do
      [ -f "$cmd" ] || continue
      local cmd_name
      cmd_name=$(basename "$cmd")
      cp "$cmd" "$BOOTSTRAP_DIR/commands/${plugin_name}-${cmd_name}"
      ok "  command: ${plugin_name}-${cmd_name}"
    done
  fi

  # Hooks
  if [ -d "$src/hooks" ]; then
    local hook_dst="$BOOTSTRAP_DIR/hooks/$plugin_name"
    rm -rf "$hook_dst"
    cp -r "$src/hooks" "$hook_dst"
    # Also grab lib/ if it exists (superpowers needs it)
    if [ -d "$src/lib" ]; then
      cp -r "$src/lib" "$hook_dst/lib"
    fi
    ok "  hooks: $plugin_name"
  fi

  # MCP config
  local mcp_file=""
  [ -f "$src/.mcp.json" ] && mcp_file="$src/.mcp.json"
  [ -f "$src/mcp.json" ] && mcp_file="$src/mcp.json"
  if [ -n "$mcp_file" ]; then
    local existing_mcp="$BOOTSTRAP_DIR/mcp/mcp.json"
    if [ -f "$existing_mcp" ]; then
      local tmp
      tmp=$(mktemp)
      jq -s '.[0] * { mcpServers: (.[0].mcpServers + .[1].mcpServers) }' "$existing_mcp" "$mcp_file" > "$tmp"
      mv "$tmp" "$existing_mcp"
    else
      mkdir -p "$BOOTSTRAP_DIR/mcp"
      cp "$mcp_file" "$existing_mcp"
    fi
    ok "  mcp: merged config"
  fi

  # Update manifest
  local skills_count=$(ls "$src/skills/" 2>/dev/null | wc -l)
  local rules_count=$(ls "$src/rules/" 2>/dev/null | wc -l)
  local agents_count=$(ls "$src/agents/" 2>/dev/null | wc -l)
  local commands_count=$(ls "$src/commands/" 2>/dev/null | wc -l)
  local hooks_count=$(ls "$src/hooks/" 2>/dev/null | wc -l)
  local mcp_count=0; [ -n "$mcp_file" ] && mcp_count=1

  local today
  today=$(date +%Y-%m-%d)
  local tmp
  tmp=$(mktemp)
  jq --arg name "$plugin_name" \
     --arg hash "$hash" \
     --arg date "$today" \
     --argjson sk "$skills_count" \
     --argjson ru "$rules_count" \
     --argjson ag "$agents_count" \
     --argjson cm "$commands_count" \
     --argjson hk "$hooks_count" \
     --argjson mc "$mcp_count" \
     '.sources["cursor-plugins"].plugins[$name] = {
        hash: $hash,
        synced_at: $date,
        skills: $sk,
        rules: $ru,
        agents: $ag,
        commands: $cm,
        hooks: $hk,
        mcp: $mc
      }' "$MANIFEST" > "$tmp"
  mv "$tmp" "$MANIFEST"
}

# ---------------------------------------------------------------------------
# Export a codex skill into bootstrap
# ---------------------------------------------------------------------------

export_codex_skill() {
  local skill_name="$1"
  local src="$CODEX_SKILLS_DIR/$skill_name"
  local dst="$BOOTSTRAP_DIR/skills/$skill_name"

  if [ -d "$dst" ]; then
    warn "Skill $skill_name already exists in bootstrap, skipping"
    return 0
  fi

  cp -r "$src" "$dst"
  ok "Imported Codex skill: $skill_name"

  local today
  today=$(date +%Y-%m-%d)
  local tmp
  tmp=$(mktemp)
  jq --arg name "$skill_name" --arg date "$today" \
     '.sources["codex-skills"].skills[$name] = { synced_at: $date }' \
     "$MANIFEST" > "$tmp"
  mv "$tmp" "$MANIFEST"
}

# ---------------------------------------------------------------------------
# Update manifest timestamp
# ---------------------------------------------------------------------------

update_manifest_timestamp() {
  local today
  today=$(date +%Y-%m-%d)
  local tmp
  tmp=$(mktemp)
  jq --arg date "$today" '.last_sync = $date' "$MANIFEST" > "$tmp"
  mv "$tmp" "$MANIFEST"
}

# ---------------------------------------------------------------------------
# Regenerate workspace rules (re-run install for existing workspaces)
# ---------------------------------------------------------------------------

refresh_workspaces() {
  local installed_log="$BOOTSTRAP_DIR/.installed"
  [ -f "$installed_log" ] || return 0

  local workspaces=()
  while IFS= read -r line; do
    case "$line" in
      generated:*rules/bootstrap-skills.mdc)
        local ws_path="${line#generated:}"
        ws_path="${ws_path%/.cursor/rules/bootstrap-skills.mdc}"
        [ -d "$ws_path" ] && workspaces+=("$ws_path")
        ;;
    esac
  done < "$installed_log"

  if [ ${#workspaces[@]} -gt 0 ]; then
    header "Refreshing workspace skill catalogs"
    for ws in "${workspaces[@]}"; do
      "$BOOTSTRAP_DIR/install.sh" workspace "$ws" --force || true
      ok "Refreshed: $ws"
    done
  fi
}

# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

cmd_check() {
  header "Sync Check — $(date +%Y-%m-%d)"
  info "Manifest last sync: $(jq -r '.last_sync' "$MANIFEST")"
  echo ""

  _NEW_PLUGINS=()
  _UPDATED_PLUGINS=()
  _NEW_CODEX_SKILLS=()

  scan_cursor_plugins
  scan_codex_skills

  local total_changes=0
  for arr in "${_NEW_PLUGINS[@]:-}" "${_UPDATED_PLUGINS[@]:-}" "${_NEW_CODEX_SKILLS[@]:-}"; do
    [ -n "$arr" ] && total_changes=$((total_changes + 1))
  done

  echo ""
  if [ "$total_changes" -gt 0 ]; then
    info "Run './sync.sh --pull' to apply changes"
  else
    ok "Everything is up to date"
  fi
}

cmd_pull() {
  header "Sync Pull — $(date +%Y-%m-%d)"
  info "Pulling updates into bootstrap repo..."

  _NEW_PLUGINS=()
  _UPDATED_PLUGINS=()
  _NEW_CODEX_SKILLS=()

  scan_cursor_plugins
  scan_codex_skills

  local did_work=false

  # Export new plugins
  for entry in "${_NEW_PLUGINS[@]:-}"; do
    [ -z "$entry" ] && continue
    local name="${entry%%|*}" hash="${entry##*|}"
    header "Exporting new plugin: $name"
    export_plugin "$name" "$hash"
    did_work=true
  done

  # Export updated plugins
  for entry in "${_UPDATED_PLUGINS[@]:-}"; do
    [ -z "$entry" ] && continue
    IFS='|' read -r name old_hash new_hash <<< "$entry"
    header "Updating plugin: $name"
    export_plugin "$name" "$new_hash"
    did_work=true
  done

  # Export new codex skills
  for name in "${_NEW_CODEX_SKILLS[@]:-}"; do
    [ -z "$name" ] && continue
    header "Importing Codex skill: $name"
    export_codex_skill "$name"
    did_work=true
  done

  if $did_work; then
    update_manifest_timestamp

    header "Regenerating global agent configs"
    "$BOOTSTRAP_DIR/install.sh" global --force || warn "Global regeneration had errors (see above)"
    ok "Regenerated global AGENTS.md / CLAUDE.md / MCP configs"

    refresh_workspaces

    echo ""
    header "Summary"
    ok "Sync complete. Changes pulled into bootstrap repo."
    info "Review with: git diff"
    info "Commit with: git add -A && git commit -m 'sync: update from sources'"
  else
    update_manifest_timestamp
    echo ""
    ok "Nothing to pull — already up to date."
  fi
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

usage() {
  printf "${BOLD}agent_bootstrap sync${NC}\n\n"
  cat <<EOF
Usage: $(basename "$0") <mode>

Modes:
  --check     Scan sources and report what's new/changed (read-only)
  --pull      Pull updates from sources into the bootstrap repo

Sources scanned:
  - Cursor plugin cache: $CURSOR_PLUGIN_CACHE
  - Codex skills: $CODEX_SKILLS_DIR

Examples:
  ./sync.sh --check    # See what's changed
  ./sync.sh --pull     # Apply changes
EOF
}

case "${1:-}" in
  --check) cmd_check ;;
  --pull)  cmd_pull ;;
  -h|--help) usage ;;
  *) usage; exit 1 ;;
esac
