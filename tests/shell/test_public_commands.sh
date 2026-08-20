#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=tests/lib/test_harness.sh
source "$ROOT/tests/lib/test_harness.sh"
test_harness_setup "$ROOT"

AGENTBOT="$ROOT/bin/agentbot"
passed=0 failed=0
pass() { printf 'PASS: %s\n' "$1"; passed=$((passed + 1)); }
fail() { printf 'FAIL: %s\n' "$1" >&2; failed=$((failed + 1)); }
check() { local name="$1"; shift; if "$@"; then pass "$name"; else fail "$name"; fi; }

test_launcher_and_headless_guidance() {
	local output rc
	[[ -x "$AGENTBOT" ]] || return 1
	set +e; output="$(AGENTBOT_TTY=0 "$AGENTBOT" 2>&1)"; rc=$?; set -e
	[[ "$rc" -ne 0 && "$output" == *'agentbot help'* && "$output" == *'agentbot install'* ]]
}

test_symlink_resolves_repository_root() {
	local link="$TEST_ROOT/agentbot-link" output rc
	ln -s "$AGENTBOT" "$link"
	set +e; output="$(AGENTBOT_TTY=0 "$link" status 2>&1)"; rc=$?; set -e
	[[ "$rc" -eq 0 && "$output" == *'=== Check Status ==='* && "$output" != *'No such file or directory'* ]]
}

test_dispatch_matrix() (
	AGENTBOT_SOURCE_ONLY=1 source "$AGENTBOT"
	local calls="$TEST_ROOT/dispatch.calls"; : >"$calls"
	agentbot_has_tty() { return 0; }
	agentbot_run_menu() { printf 'menu\n' >>"$calls"; return 11; }
	agentbot_run_token() { printf 'token\n' >>"$calls"; return 12; }
	agentbot_run_backend() { printf 'backend:%s\n' "$*" >>"$calls"; return 14; }
	set +e
	agentbot_main; [[ $? -eq 11 ]] || exit 1
	agentbot_main status; [[ $? -eq 14 ]] || exit 1
	agentbot_main install; [[ $? -eq 14 ]] || exit 1
	agentbot_main doctor; [[ $? -eq 14 ]] || exit 1
	agentbot_main token; [[ $? -eq 12 ]] || exit 1
	agentbot_main graphify status; [[ $? -eq 14 ]] || exit 1
	agentbot_main update; [[ $? -eq 14 ]] || exit 1
	agentbot_main workspace /tmp/project; [[ $? -eq 14 ]] || exit 1
	agentbot_main workspaces; [[ $? -eq 14 ]] || exit 1
	agentbot_main resync --all; [[ $? -eq 14 ]] || exit 1
	set -e
	[[ "$(<"$calls")" == $'menu\nbackend:status\nbackend:install\nbackend:doctor\ntoken\nbackend:graphify status\nbackend:update\nbackend:workspace /tmp/project\nbackend:workspaces\nbackend:resync --all' ]]
)

test_token_route_loads_existing_menu() (
	AGENTBOT_SOURCE_ONLY=1 source "$AGENTBOT"
	local calls="$TEST_ROOT/token-route.calls"; : >"$calls"
	AGENTBOT_MENU_LOADED=1
	agentbot_token_config_menu() { printf 'token-menu\n' >>"$calls"; }
	agentbot_run_token
	[[ "$(<"$calls")" == token-menu ]]
)

test_install_forwards_public_commands() (
	AGENTBOT_SOURCE_ONLY=1 source "$ROOT/install.sh"
	local calls="$TEST_ROOT/install-public.calls"; : >"$calls"
	check_python_deps() { :; }; check_skills_deps() { :; }
	run_cli() { printf '%s\n' "$*" >>"$calls"; }
	main skills install alpha
	main skills update beta
	main skills list
	main skills doctor
	main global
	main doctor
	main status --json
	main workspace --profile safe /tmp/project
	main workspaces --remove /tmp/project
	main resync --dry-run --all
	main graphify status
	[[ "$(<"$calls")" == $'skills install alpha\nskills update beta\nskills list\nskills doctor\nglobal\ndoctor\nstatus --json\nworkspace --profile safe /tmp/project\nworkspaces --remove /tmp/project\nresync --dry-run --all\ngraphify status' ]]
)

test_boot_selectors_and_atomic_validation() {
	local target="$TEST_ROOT/boot-target" config="$TEST_ROOT/boot-config" rc
	mkdir -p "$target"
	XDG_CONFIG_HOME="$config" AGENTBOT_HOME="$ROOT" "$AGENTBOT" boot "$target" >/dev/null
	[[ -f "$target/AGENTS.md" && -f "$target/CLAUDE.md" && -f "$target/.cursor/rules/agentbot-policy.mdc" ]] || return 1
	[[ ! -e "$target/.github/copilot-instructions.md" ]] || return 1
	rm -rf "$target" "$config"; mkdir -p "$target"
	set +e; XDG_CONFIG_HOME="$config" AGENTBOT_HOME="$ROOT" "$AGENTBOT" boot --unknown "$target" >/dev/null 2>&1; rc=$?; set -e
	[[ "$rc" -ne 0 && ! -e "$target/AGENTS.md" && ! -e "$target/CLAUDE.md" ]]
}

test_install_repo_gate_link_and_failure_status() (
	AGENTBOT_SOURCE_ONLY=1 source "$ROOT/install.sh"
	local calls="$TEST_ROOT/install.calls" output rc; : >"$calls"
	repo_update_run() { printf 'repo\n' >>"$calls"; printf -v "$3" '%s' current; printf -v "$4" '%s' current; }
	run_bootstrap_backend() { printf 'backend\n' >>"$calls"; return 7; }
	set +e; output="$(run_install 2>&1)"; rc=$?; set -e
	[[ "$rc" -eq 7 && "$(<"$calls")" == $'repo\nbackend' ]] || return 1
	[[ "$output" == *'Agentbot install failed (exit 7)'* && "$output" != *'Agentbot install complete'* ]] || return 1
	[[ "$(readlink "$HOME/bin/agentbot")" == "$ROOT/bin/agentbot" ]]
)

test_one_backend_and_complete_help() {
	local bin_files output boot_help workspace_help workspaces_help
	bin_files="$(find "$ROOT/bin" -maxdepth 1 -type f -printf '%f\n' | sort)"
	[[ "$bin_files" == agentbot ]] || return 1
	output="$(NO_COLOR=1 AGENTBOT_TTY=0 "$AGENTBOT" help)"
	[[ "$output" == *'AGENTBOT_HOME'* && "$output" == *'GITHUB_TOKEN'* ]] || return 1
	boot_help="$(NO_COLOR=1 "$AGENTBOT" help boot)"
	workspace_help="$(NO_COLOR=1 "$AGENTBOT" help workspace)"
	workspaces_help="$(NO_COLOR=1 "$AGENTBOT" help workspaces)"
	[[ "$boot_help" == *'--claude'* ]] || return 1
	[[ "$workspace_help" == *'--targets LIST'* ]] || return 1
	[[ "$workspaces_help" == *'--paths0'* && "$workspaces_help" == *'--remove PATH'* ]]
}

check 'launcher exists and headless invocation gives guidance' test_launcher_and_headless_guidance
check 'symlink invocation resolves the owning repository' test_symlink_resolves_repository_root
check 'public dispatcher preserves commands and exit statuses' test_dispatch_matrix
check 'token command opens the existing token menu' test_token_route_loads_existing_menu
check 'install.sh forwards public commands unchanged' test_install_forwards_public_commands
check 'boot selectors render safely and invalid input is atomic' test_boot_selectors_and_atomic_validation
check 'install gates backend work, links launcher, and reports failure truthfully' test_install_repo_gate_link_and_failure_status
check 'one backend remains and help documents the public surface' test_one_backend_and_complete_help

test_harness_verify_safety || failed=$((failed + 1))
printf '\nRan %d public-command test(s); %d failure(s).\n' "$((passed + failed))" "$failed"
test_harness_cleanup || failed=$((failed + 1))
((failed == 0))
