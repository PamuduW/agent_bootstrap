#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AGENTBOOT="${ROOT}/bin/agentboot"
TMPDIR="$(mktemp -d)"
FAILURES=0
TESTS=0

trap 'rm -rf "$TMPDIR"' EXIT

pass() {
  printf 'PASS: %s\n' "$1"
}

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  FAILURES=$((FAILURES + 1))
}

assert_file_exists() {
  local file="$1"
  local label="$2"
  TESTS=$((TESTS + 1))
  if [[ -f "$file" ]]; then
    pass "$label"
  else
    fail "$label (missing: $file)"
  fi
}

assert_contains() {
  local file="$1"
  local needle="$2"
  local label="$3"
  TESTS=$((TESTS + 1))
  if grep -Fq "$needle" "$file"; then
    pass "$label"
  else
    fail "$label (expected '$needle' in $file)"
  fi
}

assert_output_contains() {
  local output="$1"
  local needle="$2"
  local label="$3"
  TESTS=$((TESTS + 1))
  if [[ "$output" == *"$needle"* ]]; then
    pass "$label"
  else
    fail "$label (expected output to contain '$needle')"
  fi
}

run_agentboot() {
  AGENT_BOOTSTRAP_HOME="$ROOT" "$AGENTBOOT" "$@"
}

# Legacy aliases are public compatibility commands. --status is read-only and
# verifies its argument is remapped by install.sh's main scope.
STATUS_OUTPUT="$(${ROOT}/install.sh --status 2>&1)"
assert_output_contains "$STATUS_OUTPUT" "Status" "legacy --status maps to status"

LEGACY_HOME="${TMPDIR}/legacy-home"
mkdir -p "$LEGACY_HOME"
HOME="$LEGACY_HOME" "${ROOT}/install.sh" --global >/dev/null
assert_file_exists "${LEGACY_HOME}/.codex/AGENTS.md" "legacy --global maps to global"

# Test 1: creates AGENTS.md + CLAUDE.md in empty dir
WORKDIR1="${TMPDIR}/empty-repo"
mkdir -p "$WORKDIR1"
(
  cd "$WORKDIR1"
  run_agentboot
)
assert_file_exists "${WORKDIR1}/AGENTS.md" "creates AGENTS.md in empty dir"
assert_file_exists "${WORKDIR1}/CLAUDE.md" "creates CLAUDE.md in empty dir"
assert_contains "${WORKDIR1}/CLAUDE.md" "@AGENTS.md" "CLAUDE.md contains @AGENTS.md"

# Test 2: second run without --force skips existing files
OUTPUT2="$(
  cd "$WORKDIR1"
  run_agentboot 2>&1
)"
assert_output_contains "$OUTPUT2" "skip (exists): ./AGENTS.md" "second run skips AGENTS.md"
assert_output_contains "$OUTPUT2" "skip (exists): ./CLAUDE.md" "second run skips CLAUDE.md"

# Test 3: --force overwrites existing files
echo "stale content" > "${WORKDIR1}/AGENTS.md"
echo "stale content" > "${WORKDIR1}/CLAUDE.md"
(
  cd "$WORKDIR1"
  run_agentboot --force >/dev/null
)
assert_contains "${WORKDIR1}/AGENTS.md" "## Project" "--force overwrites AGENTS.md with template"
assert_contains "${WORKDIR1}/CLAUDE.md" "@AGENTS.md" "--force overwrites CLAUDE.md with template"

printf '\nRan %s test(s); %s failure(s).\n' "$TESTS" "$FAILURES"
if [[ "$FAILURES" -gt 0 ]]; then
  exit 1
fi
