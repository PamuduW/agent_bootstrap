#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

SHELL_SUITES=(
  "$ROOT/tests/test_harness.sh"
  "$ROOT/tests/shell/test_menu_core.sh"
  "$ROOT/tests/shell/test_menu_actions.sh"
  "$ROOT/tests/shell/test_public_commands.sh"
  "$ROOT/tests/test_github_token.sh"
  "$ROOT/tests/test_repo_update.sh"
  "$ROOT/tests/test_token_consumers.sh"
  "$ROOT/tests/test_update_integration.sh"
)

if [[ "${AGENTBOT_TEST_RUNNER_SOURCE_ONLY:-0}" == 1 ]]; then
  return 0
fi

run_check() {
  local label="$1" started=$SECONDS elapsed
  shift
  printf '\n==> %s\n' "$label"
  "$@"
  elapsed=$((SECONDS - started))
  printf '<== %s (%ss)\n' "$label" "$elapsed"
}

mapfile -t shell_files < <(
  find "$ROOT" \
    -path "$ROOT/.git" -prune -o \
    -path "$ROOT/archive" -prune -o \
    -type f -name '*.sh' -print | sort
)
production_shell_files=()
for shell_file in "${shell_files[@]}"; do
  [[ "$shell_file" == "$ROOT/tests/"* ]] || production_shell_files+=("$shell_file")
done

cd "$ROOT"
total_started=$SECONDS
if command -v ruff >/dev/null 2>&1; then
  run_check "Ruff" ruff check src tests
else
  printf '\n==> Ruff (skipped: ruff is not installed)\n'
fi
if command -v coverage >/dev/null 2>&1; then
  coverage erase
  run_check "Python unit tests with coverage" coverage run -m unittest discover -s tests
  run_check "Coverage" coverage report
else
  printf '\n==> Coverage (skipped: coverage is not installed)\n'
  run_check "Python unit tests" python3 -m unittest discover -s tests
fi
for suite in "${SHELL_SUITES[@]}"; do
  run_check "$(basename "$suite")" bash "$suite"
done
run_check "Bash syntax" bash -n "${shell_files[@]}"
if command -v shellcheck >/dev/null 2>&1; then
  run_check "ShellCheck" shellcheck "${production_shell_files[@]}"
else
  printf '\n==> ShellCheck (skipped: shellcheck is not installed)\n'
fi
run_check "Whitespace errors" git diff --check

printf '\nAll Agentbot checks passed in %ss.\n' "$((SECONDS - total_started))"
