#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

STRIPPED_INSTALL="$TMP_DIR/install-functions.sh"
sed '/^args=/,$d' "$ROOT_DIR/install.sh" > "$STRIPPED_INSTALL"

# Load install.sh functions without executing its main argument parser.
# shellcheck disable=SC1090
source "$STRIPPED_INSTALL"

BOOTSTRAP_DIR="$TMP_DIR/bootstrap"
MANIFEST="$BOOTSTRAP_DIR/manifest.json"
CURSOR_PLUGIN_CACHE="$TMP_DIR/cursor-cache"
CURSOR_NATIVE_DIR="$TMP_DIR/cursor-native"
INSTALLED_LOG="$TMP_DIR/.installed"
LOCAL_CONFIG="$TMP_DIR/.local-config"
MCP_REPO="$BOOTSTRAP_DIR/mcp/mcp.json"
LOG_DIR="$TMP_DIR/log"
LOG_FILE="$LOG_DIR/test.log"

mkdir -p "$BOOTSTRAP_DIR"/{skills,rules,agents,commands,hooks,mcp} "$CURSOR_PLUGIN_CACHE" "$LOG_DIR"

cat > "$MANIFEST" <<'JSON'
{
  "version": 2,
  "last_sync": "",
  "sources": {
    "cursor-plugins": {
      "base_path": "~/.cursor/plugins/cache/cursor-public",
      "plugins": {
        "repo-skill": {
          "hash": "repohash",
          "synced_at": "0",
          "skills": 1,
          "rules": 0,
          "agents": 0,
          "commands": 0,
          "hooks": 0,
          "mcp": 0,
          "mcp_servers": []
        },
        "repo-mcp": {
          "hash": "mcphash",
          "synced_at": "0",
          "skills": 0,
          "rules": 0,
          "agents": 0,
          "commands": 0,
          "hooks": 0,
          "mcp": 1,
          "mcp_servers": ["repo-mcp-server"]
        },
        "stale-plugin": {
          "hash": "stalehash",
          "synced_at": "0",
          "skills": 0,
          "rules": 0,
          "agents": 0,
          "commands": 0,
          "hooks": 0,
          "mcp": 0,
          "mcp_servers": []
        }
      }
    },
    "codex-skills": {
      "base_path": "~/.codex/skills",
      "skills": {}
    },
    "cursor-native-skills": {
      "base_path": "~/.cursor/skills-cursor",
      "skills": {}
    }
  }
}
JSON

cat > "$MCP_REPO" <<'JSON'
{
  "mcpServers": {
    "repo-mcp-server": {
      "command": "echo"
    }
  }
}
JSON

mkdir -p "$BOOTSTRAP_DIR/skills/repo-skill-example"
cat > "$BOOTSTRAP_DIR/skills/repo-skill-example/SKILL.md" <<'EOF'
# test skill
EOF

mkdir -p "$CURSOR_PLUGIN_CACHE/local-only/hash123/skills/example"

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

discover_plugins

assert_has_plugin() {
  local expected="$1"
  local name
  for name in "${PLUGIN_NAMES[@]}"; do
    [[ "$name" == "$expected" ]] && return 0
  done
  echo "Expected plugin '$expected' in discovery list, got: ${PLUGIN_NAMES[*]}" >&2
  exit 1
}

assert_missing_plugin() {
  local unexpected="$1"
  local name
  for name in "${PLUGIN_NAMES[@]}"; do
    if [[ "$name" == "$unexpected" ]]; then
      echo "Did not expect plugin '$unexpected' in discovery list" >&2
      exit 1
    fi
  done
}

assert_has_plugin "repo-skill"
assert_has_plugin "repo-mcp"
assert_missing_plugin "local-only"
assert_missing_plugin "stale-plugin"

rm -rf "$BOOTSTRAP_DIR/skills/repo-skill-example" "$CURSOR_PLUGIN_CACHE/local-only"

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

discover_plugins

assert_missing_plugin "repo-skill"
assert_has_plugin "repo-mcp"
assert_missing_plugin "local-only"
assert_missing_plugin "stale-plugin"

echo "discover_plugins keeps the list dynamic and up to date"
