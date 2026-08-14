#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/tests/lib/test_harness.sh"
test_harness_setup "$ROOT"
source "$ROOT/scripts/lib/sibling_dotfiles.sh"

passed=0 failed=0
pass() { printf 'PASS: %s\n' "$1"; passed=$((passed + 1)); }
fail() { printf 'FAIL: %s\n' "$1" >&2; failed=$((failed + 1)); }
check() { local name="$1"; shift; if "$@"; then pass "$name"; else fail "$name"; fi; }

prepare_existing() {
	DOTFILES_HOME="$TEST_FAKE_SIBLING"
	FAKE_GIT_STDOUT="${1:-git@github.com:PamuduW/dotfiles.git}"
	FAKE_SIBLING_EXIT=0
	export DOTFILES_HOME FAKE_GIT_STDOUT FAKE_SIBLING_EXIT
	sibling_dotfiles_update_all() { :; }
	: >"$TEST_SIBLING_LOG"
}

test_existing_allowed_launch() {
	prepare_existing
	sibling_dotfiles_launch >/dev/null
	grep -Fq $'sibling\tcaller=agentbot' "$TEST_SIBLING_LOG"
}

test_existing_launch_requires_both_repository_gates() {
	prepare_existing
	local gates="$TEST_ROOT/repo-gates"
	: >"$gates"
	sibling_dotfiles_update_all() { printf '%s\n' gated >>"$gates"; }
	sibling_dotfiles_launch >/dev/null
	[[ "$(<"$gates")" == gated ]] && grep -Fq $'sibling\tcaller=agentbot' "$TEST_SIBLING_LOG"
}

test_repository_gate_failure_stops_child_launch() {
	prepare_existing
	sibling_dotfiles_update_all() { return 23; }
	set +e
	sibling_dotfiles_launch >/dev/null 2>&1
	local rc=$?
	set -e
	[[ "$rc" -eq 23 && ! -s "$TEST_SIBLING_LOG" ]]
}

install_alias_git_fake() {
	cat >"$TEST_FAKE_BIN/git" <<'FAKE'
#!/usr/bin/env bash
set -u
source "${TEST_HARNESS_LIB:?}"
_harness_append_sanitized "$TEST_COMMAND_LOG" git "$@"
args=("$@")
if [[ "${args[0]:-}" == -C ]]; then
	args=("${args[@]:2}")
fi
if [[ "${args[*]}" == 'remote get-url origin' ]]; then
	printf '%s\n' "${FAKE_DOTFILES_ORIGIN:?}"
	exit 0
fi
if [[ "${args[*]}" == 'config --global --get-regexp ^url\..*\.insteadof$' ]]; then
	printf '%s\n' 'url.git@github-personal:.insteadof git@github.com:'
	exit 0
fi
exit 97
FAKE
	chmod 700 "$TEST_FAKE_BIN/git"
}

test_configured_alias_allowed() {
	prepare_existing
	FAKE_DOTFILES_ORIGIN='git@github-personal:PamuduW/dotfiles.git'
	export FAKE_DOTFILES_ORIGIN
	install_alias_git_fake
	sibling_dotfiles_launch >/dev/null
	grep -Fq $'sibling\tcaller=agentbot' "$TEST_SIBLING_LOG"
}

test_configured_alias_wrong_path_rejected() {
	prepare_existing
	FAKE_DOTFILES_ORIGIN='git@github-personal:Other/dotfiles.git'
	export FAKE_DOTFILES_ORIGIN
	install_alias_git_fake
	set +e
	sibling_dotfiles_launch >/dev/null 2>&1
	local rc=$?
	set -e
	[[ "$rc" -ne 0 && ! -s "$TEST_SIBLING_LOG" ]]
}

test_invalid_origin_stops() {
	prepare_existing 'https://credential@github.com/PamuduW/dotfiles.git'
	set +e
	sibling_dotfiles_launch >/dev/null 2>&1
	local rc=$?
	set -e
	[[ "$rc" -ne 0 && ! -s "$TEST_SIBLING_LOG" ]]
}

test_missing_decline_does_not_clone() {
	DOTFILES_HOME="$TEST_ROOT/missing-dotfiles"
	SIBLING_DOTFILES_CONFIRM=no
	export DOTFILES_HOME SIBLING_DOTFILES_CONFIRM
	: >"$TEST_COMMAND_LOG"
	sibling_dotfiles_launch >"$TEST_ROOT/decline.out"
	! grep -q $'git\tclone' "$TEST_COMMAND_LOG" && grep -Fq 'launch cancelled' "$TEST_ROOT/decline.out"
}

install_clone_fake() {
	cat >"$TEST_FAKE_BIN/git" <<'FAKE'
#!/usr/bin/env bash
set -u
source "${TEST_HARNESS_LIB:?}"
_harness_append_sanitized "$TEST_COMMAND_LOG" git "$@"
args=("$@")
if [[ "${args[0]:-}" == -C ]]; then
	args=("${args[@]:2}")
fi
if [[ "${args[0]:-}" == clone ]]; then
	dest="${args[${#args[@]}-1]}"
	mkdir -p "$dest"
	printf '%s\n' '#!/usr/bin/env bash' 'source "${TEST_HARNESS_LIB:?}"' 'harness_fake_sibling_dispatch "$@"' >"$dest/install.sh"
	chmod 700 "$dest/install.sh"
	exit 0
fi
if [[ "${args[*]}" == 'remote get-url origin' ]]; then
	printf '%s\n' 'https://github.com/PamuduW/dotfiles.git'
	exit 0
fi
exit 97
FAKE
	chmod 700 "$TEST_FAKE_BIN/git"
}

test_missing_approved_clones_and_launches() {
	install_clone_fake
	DOTFILES_HOME="$TEST_ROOT/cloned-dotfiles"
	SIBLING_DOTFILES_CONFIRM=yes
	export DOTFILES_HOME SIBLING_DOTFILES_CONFIRM
	: >"$TEST_SIBLING_LOG"
	sibling_dotfiles_launch >/dev/null
	[[ -x "$DOTFILES_HOME/install.sh" ]] && grep -Fq $'sibling\tcaller=agentbot' "$TEST_SIBLING_LOG"
}

test_launch_failure_propagates() {
	prepare_existing
	FAKE_SIBLING_EXIT=23
	export FAKE_SIBLING_EXIT
	set +e
	sibling_dotfiles_launch >/dev/null 2>&1
	local rc=$?
	set -e
	[[ "$rc" -eq 23 ]]
}

test_clone_failure_stops() {
	DOTFILES_HOME="$TEST_ROOT/clone-fails"
	SIBLING_DOTFILES_CONFIRM=yes
	export DOTFILES_HOME SIBLING_DOTFILES_CONFIRM
	cat >"$TEST_FAKE_BIN/git" <<'FAKE'
#!/usr/bin/env bash
set -u
source "${TEST_HARNESS_LIB:?}"
_harness_append_sanitized "$TEST_COMMAND_LOG" git "$@"
exit 24
FAKE
	chmod 700 "$TEST_FAKE_BIN/git"
	set +e
	sibling_dotfiles_launch >/dev/null 2>&1
	local rc=$?
	set -e
	[[ "$rc" -ne 0 && ! -e "$DOTFILES_HOME/install.sh" ]]
}

check 'existing allowlisted Dotfiles launches as a child' test_existing_allowed_launch
check 'existing Dotfiles launch gates both repositories first' test_existing_launch_requires_both_repository_gates
check 'repository gate failure stops Dotfiles child launch' test_repository_gate_failure_stops_child_launch
check 'configured SSH alias resolving to Dotfiles is allowed' test_configured_alias_allowed
check 'configured SSH alias resolving to another path is rejected' test_configured_alias_wrong_path_rejected
check 'wrong or token-bearing Dotfiles origin is rejected' test_invalid_origin_stops
check 'declining a missing Dotfiles clone does not run Git clone' test_missing_decline_does_not_clone
check 'approved missing Dotfiles clone is validated then launched' test_missing_approved_clones_and_launches
check 'Dotfiles child launch status propagates' test_launch_failure_propagates
check 'Dotfiles clone failure stops before launch' test_clone_failure_stops

test_harness_verify_safety || failed=$((failed + 1))
printf '\nRan %d sibling test(s); %d failure(s).\n' "$((passed + failed))" "$failed"
test_harness_cleanup || failed=$((failed + 1))
((failed == 0))
