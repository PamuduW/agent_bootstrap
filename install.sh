#!/usr/bin/env bash
set -euo pipefail

BOOTSTRAP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DRY_RUN=false
FORCE=false
INSTALLED_LOG="$BOOTSTRAP_DIR/.installed"

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

info()  { printf "${CYAN}[info]${NC}  %s\n" "$*"; }
ok()    { printf "${GREEN}[ok]${NC}    %s\n" "$*"; }
warn()  { printf "${YELLOW}[skip]${NC}  %s\n" "$*"; }
err()   { printf "${RED}[err]${NC}   %s\n" "$*" >&2; }
dry()   { printf "${YELLOW}[dry]${NC}   %s\n" "$*"; }
header(){ printf "\n${BOLD}── %s${NC}\n" "$*"; }

run() {
  if $DRY_RUN; then dry "$*"; else "$@"; fi
}

log_installed() {
  $DRY_RUN && return 0
  echo "$1" >> "$INSTALLED_LOG"
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

merge_mcp_json() {
  local src="$1" dst="$2"
  if [ ! -f "$dst" ]; then
    run cp "$src" "$dst"
    if ! $DRY_RUN; then
      log_installed "file:$dst"
      ok "Created $dst"
    fi
    return
  fi

  if ! command -v jq &>/dev/null; then
    err "jq is required for MCP config merging. Install with: sudo apt install jq"
    return 1
  fi

  if $DRY_RUN; then
    dry "Merge MCP servers from $src into $dst"
    return
  fi

  local tmp
  tmp=$(mktemp)
  jq -s '.[0].mcpServers as $existing |
         .[1].mcpServers as $new |
         { mcpServers: ($existing + $new) }' "$dst" "$src" > "$tmp"
  mv "$tmp" "$dst"
  log_installed "mcp-merge:$dst"
  ok "Merged MCP servers into $dst"
}

symlink_file() {
  local src="$1" dst="$2"
  if [ -L "$dst" ]; then
    local current
    current=$(readlink -f "$dst" 2>/dev/null || true)
    if [ "$current" = "$(readlink -f "$src")" ]; then
      warn "Already linked: $dst"
      return 0
    fi
    run rm "$dst"
  elif [ -e "$dst" ]; then
    warn "Already exists (not symlink), skipping: $dst"
    return 0
  fi
  run ln -s "$src" "$dst"
  if ! $DRY_RUN; then
    log_installed "symlink:$dst"
    ok "Linked $dst -> $src"
  fi
}

generate_skills_rule() {
  local target_dir="$1"
  local rule_file="$target_dir/.cursor/rules/bootstrap-skills.mdc"

  if $DRY_RUN; then
    dry "Generate $rule_file with skill catalog"
    return
  fi

  mkdir -p "$target_dir/.cursor/rules"

  cat > "$rule_file" << 'HEADER'
---
description: Agent capabilities provided by agent_bootstrap
alwaysApply: true
---
HEADER

  echo "You have access to additional skills from the agent bootstrap repo." >> "$rule_file"
  echo "To use a skill, read its SKILL.md file and follow the instructions within." >> "$rule_file"
  echo "" >> "$rule_file"
  echo "## Available Skills" >> "$rule_file"
  echo "" >> "$rule_file"

  for skill_dir in "$BOOTSTRAP_DIR"/skills/*/; do
    [ -f "$skill_dir/SKILL.md" ] || continue
    local name
    name=$(basename "$skill_dir")
    local desc=""
    desc=$(head -20 "$skill_dir/SKILL.md" | grep -i "^description:" | head -1 | sed 's/^description:\s*//' || true)
    if [ -z "$desc" ]; then
      desc=$(head -5 "$skill_dir/SKILL.md" | grep "^#" | head -1 | sed 's/^#\+\s*//' || true)
    fi
    echo "- **$name**: \`$skill_dir/SKILL.md\`${desc:+ — $desc}" >> "$rule_file"
  done

  echo "" >> "$rule_file"
  echo "## Available Commands (prompt templates)" >> "$rule_file"
  echo "" >> "$rule_file"
  for cmd in "$BOOTSTRAP_DIR"/commands/*.md; do
    [ -f "$cmd" ] || continue
    echo "- $(basename "$cmd" .md): \`$cmd\`" >> "$rule_file"
  done

  echo "" >> "$rule_file"
  echo "## Available Agents (subagent definitions)" >> "$rule_file"
  echo "" >> "$rule_file"
  for agent in "$BOOTSTRAP_DIR"/agents/*.md; do
    [ -f "$agent" ] || continue
    echo "- $(basename "$agent" .md): \`$agent\`" >> "$rule_file"
  done

  echo "" >> "$rule_file"

  local mcp_servers=""
  if command -v jq &>/dev/null && [ -f "$BOOTSTRAP_DIR/mcp/mcp.json" ]; then
    mcp_servers=$(jq -r '.mcpServers | keys | join(", ")' "$BOOTSTRAP_DIR/mcp/mcp.json" 2>/dev/null || true)
  fi
  if [ -n "$mcp_servers" ]; then
    echo "## MCP Servers" >> "$rule_file"
    echo "" >> "$rule_file"
    echo "Configured MCP servers: $mcp_servers" >> "$rule_file"
    echo "See \`$BOOTSTRAP_DIR/mcp/mcp-inventory.md\` for details." >> "$rule_file"
  fi

  log_installed "generated:$rule_file"
  ok "Generated $rule_file"
}

# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

cmd_global() {
  header "Global setup"

  # --- Cursor MCP ---
  if [ -d "$HOME/.cursor" ]; then
    header "Cursor: MCP servers"
    mkdir -p "$HOME/.cursor"
    merge_mcp_json "$BOOTSTRAP_DIR/mcp/mcp.json" "$HOME/.cursor/mcp.json"
  else
    warn "~/.cursor not found, skipping Cursor MCP setup"
  fi

  # --- Codex ---
  if [ -d "$HOME/.codex" ]; then
    header "Codex: global AGENTS.md"
    local codex_agents="$HOME/.codex/AGENTS.md"
    if [ -f "$codex_agents" ] && ! $FORCE; then
      warn "$codex_agents already exists (use --force to overwrite)"
    else
      run cp "$BOOTSTRAP_DIR/templates/AGENTS.md" "$codex_agents"
      if ! $DRY_RUN; then
        log_installed "file:$codex_agents"
        ok "Installed $codex_agents"
      fi
    fi

    header "Codex: skills"
    mkdir -p "$HOME/.codex/skills"
    for skill_dir in "$BOOTSTRAP_DIR"/skills/*/; do
      [ -f "$skill_dir/SKILL.md" ] || continue
      local name
      name=$(basename "$skill_dir")
      local dst="$HOME/.codex/skills/$name"
      symlink_file "$skill_dir" "$dst"
    done
  else
    warn "~/.codex not found, skipping Codex setup"
  fi

  # --- Claude Code ---
  if [ -d "$HOME/.claude" ]; then
    header "Claude Code: MCP servers"
    mkdir -p "$HOME/.claude"
    merge_mcp_json "$BOOTSTRAP_DIR/mcp/mcp.json" "$HOME/.claude/mcp.json"
  else
    info "~/.claude not found, skipping Claude Code setup"
  fi

  # --- Shell profile: AGENT_BOOTSTRAP_HOME ---
  header "Shell profile"
  local profile="$HOME/.bashrc"
  local marker="# agent_bootstrap"
  local export_line="export AGENT_BOOTSTRAP_HOME=\"$BOOTSTRAP_DIR\" $marker"

  if grep -qF "$marker" "$profile" 2>/dev/null; then
    warn "AGENT_BOOTSTRAP_HOME already in $profile"
  else
    if $DRY_RUN; then
      dry "Append AGENT_BOOTSTRAP_HOME to $profile"
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

  if [ "$target" = "$BOOTSTRAP_DIR" ]; then
    warn "Skipping bootstrap repo itself"
    return 0
  fi

  header "Workspace: $target"

  # --- Cursor rules ---
  info "Symlinking rules into $target/.cursor/rules/"
  run mkdir -p "$target/.cursor/rules"
  for rule in "$BOOTSTRAP_DIR"/rules/*.mdc; do
    [ -f "$rule" ] || continue
    symlink_file "$rule" "$target/.cursor/rules/$(basename "$rule")"
  done

  # --- Generated skills rule ---
  generate_skills_rule "$target"

  # --- Workspace MCP ---
  info "Setting up workspace MCP config"
  run mkdir -p "$target/.cursor"
  merge_mcp_json "$BOOTSTRAP_DIR/mcp/mcp.json" "$target/.cursor/mcp.json"

  echo ""
  ok "Workspace $target setup complete."
}

cmd_all() {
  local parent="$1"
  parent="$(cd "$parent" 2>/dev/null && pwd)" || { err "Directory not found: $1"; return 1; }

  header "Setting up all git repos under $parent"
  local count=0

  for dir in "$parent"/*/; do
    [ -d "$dir/.git" ] || continue
    dir="$(cd "$dir" && pwd)"
    [ "$dir" = "$BOOTSTRAP_DIR" ] && { warn "Skipping bootstrap repo itself"; continue; }
    cmd_workspace "$dir"
    count=$((count + 1))
  done

  echo ""
  if [ "$count" -eq 0 ]; then
    warn "No git repos found under $parent"
  else
    ok "Set up $count workspace(s) under $parent"
  fi
}

cmd_status() {
  header "Agent Bootstrap Status"

  echo ""
  info "Bootstrap home: $BOOTSTRAP_DIR"
  info "Skills:   $(find "$BOOTSTRAP_DIR/skills" -name SKILL.md | wc -l)"
  info "Rules:    $(find "$BOOTSTRAP_DIR/rules" -name '*.mdc' | wc -l)"
  info "Agents:   $(find "$BOOTSTRAP_DIR/agents" -name '*.md' | wc -l)"
  info "Commands: $(find "$BOOTSTRAP_DIR/commands" -name '*.md' | wc -l)"

  echo ""
  header "Global installations"

  if [ -f "$HOME/.cursor/mcp.json" ]; then
    local servers
    servers=$(jq -r '.mcpServers | keys | join(", ")' "$HOME/.cursor/mcp.json" 2>/dev/null || echo "(cannot parse)")
    ok "Cursor MCP: $servers"
  else
    warn "Cursor MCP: not configured"
  fi

  if [ -d "$HOME/.codex" ]; then
    local codex_skills=0
    for s in "$HOME/.codex/skills"/*/; do
      [ -L "$s" ] || continue
      local link_target
      link_target=$(readlink -f "$s" 2>/dev/null || true)
      if [[ "$link_target" == "$BOOTSTRAP_DIR"* ]]; then
        codex_skills=$((codex_skills + 1))
      fi
    done
    ok "Codex skills linked: $codex_skills"
    [ -f "$HOME/.codex/AGENTS.md" ] && ok "Codex AGENTS.md: present" || warn "Codex AGENTS.md: missing"
  else
    warn "Codex: not installed"
  fi

  if grep -qF "AGENT_BOOTSTRAP_HOME" "$HOME/.bashrc" 2>/dev/null; then
    ok "AGENT_BOOTSTRAP_HOME: set in .bashrc"
  else
    warn "AGENT_BOOTSTRAP_HOME: not in .bashrc"
  fi

  echo ""
  header "Workspace installations"

  local ws_count=0
  if [ -f "$INSTALLED_LOG" ]; then
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
  [ "$ws_count" -eq 0 ] && info "No workspaces configured yet"
}

cmd_uninstall() {
  header "Uninstalling agent_bootstrap"

  if [ ! -f "$INSTALLED_LOG" ]; then
    warn "No installation log found, nothing to uninstall"
    return 0
  fi

  while IFS= read -r line; do
    local type="${line%%:*}"
    local path="${line#*:}"
    case "$type" in
      symlink)
        if [ -L "$path" ]; then
          run rm "$path"
          ok "Removed symlink: $path"
        fi
        ;;
      generated)
        if [ -f "$path" ]; then
          run rm "$path"
          ok "Removed generated file: $path"
        fi
        ;;
      file)
        if [ -f "$path" ]; then
          run rm "$path"
          ok "Removed file: $path"
        fi
        ;;
      mcp-merge)
        warn "Cannot auto-undo MCP merge for $path — edit manually"
        ;;
      profile-line)
        if ! $DRY_RUN; then
          local marker="# agent_bootstrap"
          if grep -qF "$marker" "$path" 2>/dev/null; then
            sed -i "/$marker/d" "$path"
            ok "Removed AGENT_BOOTSTRAP_HOME from $path"
          fi
        else
          dry "Remove AGENT_BOOTSTRAP_HOME from $path"
        fi
        ;;
    esac
  done < "$INSTALLED_LOG"

  if ! $DRY_RUN; then
    rm -f "$INSTALLED_LOG"
    ok "Removed installation log"
  fi

  echo ""
  ok "Uninstall complete."
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

usage() {
  printf "${BOLD}agent_bootstrap installer${NC}\n\n"
  cat <<EOF
Usage: $(basename "$0") <command> [options]

Commands:
  global              Set up global configs (MCP, Codex skills, shell env)
  workspace <path>    Set up a single workspace/repo
  all <parent-dir>    Set up all git repos under a directory
  status              Show current installation status
  uninstall           Remove all installed symlinks and configs

Options:
  --dry-run           Show what would be done without making changes
  --force             Overwrite existing files (with global)
  -h, --help          Show this help

Examples:
  ./install.sh global
  ./install.sh workspace ~/ATOM/my-repo
  ./install.sh all ~/ATOM/
  ./install.sh all ~/ATOM/ --dry-run
  ./install.sh uninstall
EOF
}

# Parse --dry-run and --force from anywhere in args
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
shift || true

case "$command" in
  global)    cmd_global ;;
  workspace) [ -z "${1:-}" ] && { err "Usage: install.sh workspace <path>"; exit 1; }; cmd_workspace "$1" ;;
  all)       [ -z "${1:-}" ] && { err "Usage: install.sh all <parent-dir>"; exit 1; }; cmd_all "$1" ;;
  status)    cmd_status ;;
  uninstall) cmd_uninstall ;;
  *)         usage; exit 1 ;;
esac
