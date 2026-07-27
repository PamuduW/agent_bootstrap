#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/tests/lib/test_harness.sh"
test_harness_setup "$ROOT"

AGENTBOT="$ROOT/bin/agentbot"
passed=0 failed=0
pass() { printf 'PASS: %s\n' "$1"; passed=$((passed + 1)); }
fail() { printf 'FAIL: %s\n' "$1" >&2; failed=$((failed + 1)); }
check() { local name="$1"; shift; if "$@"; then pass "$name"; else fail "$name"; fi; }

test_dispatcher_exists() { [[ -x "$AGENTBOT" ]]; }

test_headless_no_arg_guidance() {
	local output rc
	set +e; output="$(AGENTBOT_TTY=0 "$AGENTBOT" 2>&1)"; rc=$?; set -e
	[[ "$rc" -ne 0 && "$output" == *'agentbot help'* && "$output" == *'agentbot install'* ]]
}

test_symlink_invocation_resolves_repository_root() {
	local link="$TEST_ROOT/agentbot-link" output
	ln -s "$AGENTBOT" "$link"
	set +e
	output="$(AGENTBOT_TTY=0 "$link" status 2>&1)"
	local rc=$?
	set -e
	[[ "$rc" -eq 0 && "$output" == *'=== Status ==='* && "$output" != *'No such file or directory'* ]]
}

test_dispatch_matrix() (
	AGENTBOT_SOURCE_ONLY=1 source "$AGENTBOT"
	local calls="$TEST_ROOT/dispatch.calls"; : >"$calls"
	agentbot_has_tty() { return 0; }
	agentbot_run_menu() { printf 'menu\n' >>"$calls"; return 11; }
	agentbot_run_token() { printf 'token\n' >>"$calls"; return 12; }
	agentbot_run_dotfiles() { printf 'dotfiles\n' >>"$calls"; return 13; }
	agentbot_run_backend() { printf 'backend:%s\n' "$*" >>"$calls"; return 14; }
	set +e
	agentbot_main; [[ $? -eq 11 ]] || exit 1
	agentbot_main status; [[ $? -eq 14 ]] || exit 1
	agentbot_main install; [[ $? -eq 14 ]] || exit 1
	agentbot_main doctor; [[ $? -eq 14 ]] || exit 1
	agentbot_main token; [[ $? -eq 12 ]] || exit 1
	agentbot_main dotfiles; [[ $? -eq 13 ]] || exit 1
	agentbot_main graphify status; [[ $? -eq 14 ]] || exit 1
	agentbot_main update; [[ $? -eq 14 ]] || exit 1
	agentbot_main upgrade; [[ $? -eq 14 ]] || exit 1
	agentbot_main workspace /tmp/project; [[ $? -eq 14 ]] || exit 1
	agentbot_main workspaces; [[ $? -eq 14 ]] || exit 1
	agentbot_main resync --all; [[ $? -eq 14 ]] || exit 1
	set -e
	[[ "$(<"$calls")" == $'menu\nbackend:status\nbackend:install\nbackend:doctor\ntoken\ndotfiles\nbackend:graphify status\nbackend:update\nbackend:upgrade\nbackend:workspace /tmp/project\nbackend:workspaces\nbackend:resync --all' ]]
)

test_install_graphify_dispatch_does_not_require_full_skill_dependencies() (
	AGENTBOT_SOURCE_ONLY=1 source "$ROOT/install.sh"
	local calls="$TEST_ROOT/install-graphify.calls"
	: >"$calls"
	check_deps() { return 91; }
	run_cli() { printf '%s\n' "$*" >>"$calls"; }
	main graphify status
	[[ "$(<"$calls")" == 'graphify status' ]]
)

test_boot_selector_matrix() {
	local target="$TEST_ROOT/boot-target" config="$TEST_ROOT/boot-config"
	mkdir -p "$target"
	XDG_CONFIG_HOME="$config" AGENTBOT_HOME="$ROOT" "$AGENTBOT" boot "$target" >/dev/null
	[[ -f "$target/AGENTS.md" && -f "$target/CLAUDE.md" ]] || return 1
	[[ -f "$target/.cursor/rules/agentbot-policy.mdc" ]] || return 1
	[[ ! -e "$target/.github/copilot-instructions.md" ]] || return 1
	python3 -c 'import json, sys; state=json.load(open(sys.argv[1])); item=state["workspaces"][0]; assert item["kind"] == "directory"; assert item["targets"] == ["agents", "claude", "cursor"]' "$config/agentbot/workspaces.json" || return 1

	rm -rf "$target" "$config"
	mkdir -p "$target"
	XDG_CONFIG_HOME="$config" AGENTBOT_HOME="$ROOT" "$AGENTBOT" boot --copilot "$target" >/dev/null
	[[ -f "$target/AGENTS.md" && -f "$target/.github/copilot-instructions.md" ]] || return 1

	rm -rf "$target" "$config"
	mkdir -p "$target"
	XDG_CONFIG_HOME="$config" AGENTBOT_HOME="$ROOT" "$AGENTBOT" boot --claude "$target" >/dev/null
	[[ -f "$target/AGENTS.md" && -f "$target/CLAUDE.md" ]] || return 1
	[[ ! -e "$target/.github/copilot-instructions.md" && ! -e "$target/.cursor/rules/agentbot-policy.mdc" ]] || return 1
	printf stale >"$target/CLAUDE.md"
	set +e
	XDG_CONFIG_HOME="$config" AGENTBOT_HOME="$ROOT" "$AGENTBOT" boot --force "$target" >/dev/null 2>&1
	local rc=$?
	set -e
	[[ "$rc" -ne 0 ]]
}

test_boot_without_target_registers_pwd() {
	local target="$TEST_ROOT/current-dir" config="$TEST_ROOT/current-config"
	mkdir -p "$target"
	(
		cd "$target"
		XDG_CONFIG_HOME="$config" AGENTBOT_HOME="$ROOT" "$AGENTBOT" boot >/dev/null
	)
	[[ -f "$target/AGENTS.md" && -f "$config/agentbot/workspaces.json" ]]
}

test_boot_validation_is_atomic() {
	local target="$TEST_ROOT/atomic-target" output rc
	mkdir -p "$target"
	set +e; output="$(AGENTBOT_HOME="$ROOT" "$AGENTBOT" boot --unknown "$target" 2>&1)"; rc=$?; set -e
	[[ "$rc" -ne 0 && ! -e "$target/AGENTS.md" && ! -e "$target/CLAUDE.md" ]] || return 1
	set +e; output="$(AGENTBOT_HOME="$ROOT" "$AGENTBOT" boot "$target" "$target" 2>&1)"; rc=$?; set -e
	[[ "$rc" -ne 0 && ! -e "$target/AGENTS.md" && ! -e "$target/CLAUDE.md" ]]
}

test_install_link_and_owned_cleanup() (
	AGENTBOT_SOURCE_ONLY=1 source "$ROOT/install.sh"
	run_bootstrap_backend() { :; }
	mkdir -p "$HOME/bin"
	ln -s "$ROOT/bin/agentboot" "$HOME/bin/agentboot"
	run_install >/dev/null
	[[ "$(readlink "$HOME/bin/agentbot")" == "$ROOT/bin/agentbot" && ! -e "$HOME/bin/agentboot" && ! -L "$HOME/bin/agentboot" ]]
)

test_foreign_old_paths_are_preserved() (
	AGENTBOT_SOURCE_ONLY=1 source "$ROOT/install.sh"
	mkdir -p "$HOME/bin"
	printf keep >"$HOME/bin/agentboot"
	cleanup_owned_old_agentboot_link >/dev/null 2>&1
	[[ -f "$HOME/bin/agentboot" && "$(<"$HOME/bin/agentboot")" == keep ]] || return 1
	rm -f "$HOME/bin/agentboot"
	ln -s "$TEST_ROOT/foreign/agentboot" "$HOME/bin/agentboot"
	cleanup_owned_old_agentboot_link >/dev/null 2>&1
	[[ -L "$HOME/bin/agentboot" ]]
)

test_environment_and_no_old_binary() {
	[[ ! -e "$ROOT/bin/agentboot" && ! -e "$ROOT/tests/test_agentboot.sh.old" ]] || return 1
	local output
	output="$(AGENTBOT_HOME="$ROOT" "$AGENTBOT" help)"
	[[ "$output" == *'agentbot boot'* && "$output" != *link-agentboot* ]]
}

test_agentbot_help_describes_full_command_options() {
	local output
	output="$(NO_COLOR=1 AGENTBOT_HOME="$ROOT" AGENTBOT_TTY=0 "$AGENTBOT" help)"
	[[ "$output" == *'--claude'* ]] || return 1
	[[ "$output" == *'--targets LIST'* ]] || return 1
	[[ "$output" == *'AGENTBOT_HOME'* ]] || return 1
	[[ "$output" == *'GITHUB_TOKEN'* ]] || return 1
	[[ "$output" == *'agentbot update|upgrade'* ]]
}

check 'agentbot dispatcher exists and is executable' test_dispatcher_exists
if [[ -x "$AGENTBOT" ]]; then
	check 'headless no-arg fails with explicit guidance' test_headless_no_arg_guidance
	check 'symlink invocation resolves the Agentbot repository root' test_symlink_invocation_resolves_repository_root
	check 'dispatcher routes exact backend and future seams' test_dispatch_matrix
	check 'install.sh routes Graphify without requiring Node/npx' test_install_graphify_dispatch_does_not_require_full_skill_dependencies
	check 'boot selectors register folders and keep AGENTS canonical' test_boot_selector_matrix
	check 'boot without a target registers the current directory' test_boot_without_target_registers_pwd
	check 'boot rejects invalid inputs before partial writes' test_boot_validation_is_atomic
	check 'explicit install links agentbot and cleans owned old link' test_install_link_and_owned_cleanup
	check 'foreign and regular old paths are preserved' test_foreign_old_paths_are_preserved
	check 'help and executable expose no old public surface' test_environment_and_no_old_binary
	check 'agentbot help describes full command options and configuration' test_agentbot_help_describes_full_command_options
else
	fail 'headless no-arg fails with explicit guidance'
	fail 'symlink invocation resolves the Agentbot repository root'
	fail 'dispatcher routes exact backend and future seams'
	fail 'boot selectors produce default agents claude and combined outputs'
	fail 'boot rejects invalid inputs before partial writes'
	fail 'explicit install links agentbot and cleans owned old link'
	fail 'foreign and regular old paths are preserved'
	fail 'help and executable expose no old public surface'
	fail 'agentbot help describes full command options and configuration'
fi

printf '\nRan %d Agentbot test(s); %d failure(s).\n' "$((passed + failed))" "$failed"
((failed == 0))
