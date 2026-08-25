import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import tomllib

_BOOST_CLAUDE_SETTINGS = json.dumps(
    {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "~/.claude/hooks/boost-hook-claude.sh",
                        }
                    ],
                }
            ]
        }
    }
)


_BOOST_CODEX_HOOKS = json.dumps(
    {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "~/.codex/hooks/boost-hook-codex.sh",
                        }
                    ],
                }
            ],
            "Stop": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": "~/.codex/hooks/boost-sync.sh",
                        }
                    ]
                }
            ],
        }
    }
)


class BoostIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.codex = self.root / ".codex"
        self.claude = self.root / ".claude"
        (self.root / "global").mkdir()
        (self.root / "global/AGENTS.md").write_text("# baseline\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _paths(self):
        from src.paths import AgentbotPaths

        return AgentbotPaths(
            self.root,
            self.codex,
            self.claude,
            self.root / ".cursor",
            config_home=self.root / ".config/agentbot",
            agents_home=self.root / ".agents",
        )

    def _integration_type(self):
        try:
            from src.boost import BoostIntegration
        except ModuleNotFoundError:
            self.fail("src.boost.BoostIntegration is missing")
        return BoostIntegration

    def test_safe_config_merge_preserves_unrelated_valid_toml(self) -> None:
        BoostIntegration = self._integration_type()
        config = self.root / ".boost/config.toml"
        config.parent.mkdir()
        config.write_text(
            'accept_terms = "yes"\n\n[hooks]\nexclude_commands = ["vim"]\n'
            "\n[tracing]\nreport = false\nupload = true\n",
            encoding="utf-8",
        )

        integration = BoostIntegration(self._paths())
        integration.ensure_safe_config()

        parsed = tomllib.loads(config.read_text(encoding="utf-8"))
        self.assertEqual("yes", parsed["accept_terms"])
        self.assertEqual(["vim"], parsed["hooks"]["exclude_commands"])
        self.assertFalse(parsed["tracing"]["report"])
        self.assertFalse(parsed["tracing"]["upload"])
        self.assertFalse(parsed["update"]["auto_update"])

    def test_setup_runs_gated_shell_only_plan_without_accept_terms(self) -> None:
        from src.command_runner import CommandResult

        BoostIntegration = self._integration_type()
        boost = self.root / "bin/boost"
        boost.parent.mkdir()
        boost.write_text("binary", encoding="utf-8")
        paths = self._paths()

        class Runner:
            def __init__(self) -> None:
                self.calls: list[list[str]] = []
                self.interactive_calls: list[list[str]] = []

            def run(self, argv, **_kwargs):
                self.calls.append(list(argv))
                if argv[-1] == "version":
                    return CommandResult(0, stdout="boost v0.12.6\n")
                return CommandResult(
                    0,
                    stdout=(
                        "Claude Code global settings.json patch\n"
                        "Codex CLI global hooks.json and BOOST.md\n"
                    ),
                )

            def run_interactive(self, argv, **_kwargs):
                self.interactive_calls.append(list(argv))
                (paths.claude_home / "hooks").mkdir(parents=True)
                (paths.claude_home / "hooks/boost-hook-claude.sh").write_text("hook\n")
                (paths.claude_home / "rules").mkdir(parents=True)
                (paths.claude_home / "rules/boost-awareness.md").write_text("rule\n")
                (paths.claude_home / "settings.json").write_text(
                    _BOOST_CLAUDE_SETTINGS
                )
                (paths.codex_home / "hooks").mkdir(parents=True)
                (paths.codex_home / "hooks/boost-hook-codex.sh").write_text("hook\n")
                (paths.codex_home / "hooks/boost-sync.sh").write_text("hook\n")
                (paths.codex_home / "BOOST.md").write_text("# Boost\n")
                (paths.codex_home / "hooks.json").write_text(_BOOST_CODEX_HOOKS)
                return CommandResult(0)

        runner = Runner()
        with mock.patch("src.boost.shutil.which", return_value=str(boost)):
            status = BoostIntegration(paths, runner=runner).setup()

        expected = [
            str(boost),
            "init",
            "--no-boostgraph",
            "--claude",
            "--codex",
        ]
        self.assertIn([*expected[:2], "--dry-run", *expected[2:]], runner.calls)
        self.assertEqual([expected], runner.interactive_calls)
        self.assertNotIn("--accept-terms", runner.interactive_calls[0])
        self.assertEqual("ready", status.state)

    def test_setup_rejects_forbidden_graph_plan_before_writing(self) -> None:
        from src.command_runner import CommandResult

        BoostIntegration = self._integration_type()
        boost = self.root / "boost"
        boost.write_text("binary", encoding="utf-8")
        runner = mock.Mock()

        def run(argv, **_kwargs):
            if argv[-1] == "version":
                return CommandResult(0, stdout="boost v0.12.6\n")
            return CommandResult(0, stdout="write MCP config and start BoostGraph watcher\n")

        runner.run.side_effect = run

        with mock.patch("src.boost.shutil.which", return_value=str(boost)):
            status = BoostIntegration(self._paths(), runner=runner).setup()

        self.assertEqual("broken", status.state)
        self.assertIn("forbidden", status.message.lower())
        runner.run_interactive.assert_not_called()

    def test_off_uninstalls_one_target_per_call_and_never_previews(self) -> None:
        # `boost init --uninstall` rejects more than one target ("specify only
        # one target to uninstall"), unlike setup which accepts several. The
        # first version of this passed both at once and never worked.
        #
        # It must also never pass --dry-run: v0.12.6 honours that flag for
        # install but performs the removal anyway for uninstall, so a "preview"
        # call would tear the integration down before the real one ran.
        from src.command_runner import CommandResult

        BoostIntegration = self._integration_type()
        boost = self.root / "boost"
        boost.write_text("binary", encoding="utf-8")
        runner = mock.Mock()

        def run(argv, **_kwargs):
            if argv[-1] == "version":
                return CommandResult(0, stdout="boost v0.12.6\n")
            return CommandResult(0, stdout="Claude Code\nCodex CLI\n")

        runner.run.side_effect = run
        runner.run_interactive.return_value = CommandResult(0)

        with mock.patch("src.boost.shutil.which", return_value=str(boost)):
            BoostIntegration(self._paths(), runner=runner).off()

        interactive = [call.args[0] for call in runner.run_interactive.call_args_list]
        self.assertEqual(
            [
                [str(boost), "init", "--uninstall", "--no-boostgraph", "--claude"],
                [str(boost), "init", "--uninstall", "--no-boostgraph", "--codex"],
            ],
            interactive,
        )
        for argv in interactive:
            self.assertNotIn("--yes", argv)
            # Exactly one target per invocation.
            self.assertEqual(
                1,
                sum(argv.count(flag) for flag in ("--claude", "--codex", "--cursor")),
            )

        previews = [
            call.args[0]
            for call in runner.run.call_args_list + runner.run_interactive.call_args_list
            if "--dry-run" in call.args[0] and "--uninstall" in call.args[0]
        ]
        self.assertEqual([], previews)

    def test_off_stops_at_the_first_target_that_fails(self) -> None:
        from src.command_runner import CommandResult

        BoostIntegration = self._integration_type()
        boost = self.root / "boost"
        boost.write_text("binary", encoding="utf-8")
        runner = mock.Mock()
        runner.run.return_value = CommandResult(0, stdout="boost v0.12.6\n")
        runner.run_interactive.return_value = CommandResult(
            1, stderr="specify only one target to uninstall"
        )

        with mock.patch("src.boost.shutil.which", return_value=str(boost)):
            status = BoostIntegration(self._paths(), runner=runner).off()

        self.assertEqual("broken", status.state)
        self.assertIn("--claude", status.message)
        # Codex is never attempted once Claude fails.
        self.assertEqual(1, runner.run_interactive.call_count)

    def test_setup_rejects_a_plan_missing_a_requested_target(self) -> None:
        from src.command_runner import CommandResult

        BoostIntegration = self._integration_type()
        boost = self.root / "boost"
        boost.write_text("binary", encoding="utf-8")
        runner = mock.Mock()

        def run(argv, **_kwargs):
            if argv[-1] == "version":
                return CommandResult(0, stdout="boost v0.12.6\n")
            return CommandResult(0, stdout="Claude Code global settings.json patch\n")

        runner.run.side_effect = run
        with mock.patch("src.boost.shutil.which", return_value=str(boost)):
            status = BoostIntegration(self._paths(), runner=runner).setup()

        self.assertEqual("broken", status.state)
        self.assertIn("Claude and Codex", status.message)
        runner.run_interactive.assert_not_called()

    def test_status_reports_cli_only_partial_ready_and_forbidden_states(self) -> None:
        from src.boost import BoostIntegration
        from src.command_runner import CommandResult

        boost = self.root / "boost"
        boost.write_text("binary", encoding="utf-8")
        runner = mock.Mock()
        runner.run.return_value = CommandResult(0, stdout="boost v0.12.6\n")
        integration = BoostIntegration(self._paths(), runner=runner)
        integration.ensure_safe_config()

        with mock.patch("src.boost.shutil.which", return_value=str(boost)):
            self.assertEqual("cli-only", integration.status().state)
            (self.claude / "hooks").mkdir(parents=True)
            (self.claude / "hooks/boost-hook-claude.sh").write_text("hook\n")
            (self.claude / "rules").mkdir(parents=True)
            (self.claude / "rules/boost-awareness.md").write_text("rule\n")
            (self.claude / "settings.json").write_text(_BOOST_CLAUDE_SETTINGS)
            self.assertEqual("partial", integration.status().state)
            (self.codex / "hooks").mkdir(parents=True)
            for name in ("boost-hook-codex.sh", "boost-sync.sh"):
                (self.codex / "hooks" / name).write_text("hook\n")
            (self.codex / "hooks.json").write_text("{}\n")
            (self.codex / "BOOST.md").write_text("# Boost\n")
            # An empty hooks.json is a file, but Codex is not running anything
            # through it. File existence alone must not read as "ready".
            self.assertEqual("partial", integration.status().state)
            self.assertEqual("unregistered", integration._codex_state())
            (self.codex / "hooks.json").write_text(_BOOST_CODEX_HOOKS)
            self.assertEqual("ready", integration.status().state)
            (self.codex / "hooks.json").write_text('{"server":"boostgraph"}\n')
            self.assertEqual("forbidden", integration.status().state)
            self.assertEqual("forbidden", integration.setup().state)
            runner.run_interactive.assert_not_called()

    def test_invalid_timeout_and_invalid_config_fail_cleanly(self) -> None:
        from src.boost import BoostIntegration

        integration = BoostIntegration(self._paths())
        with mock.patch.dict("os.environ", {"AGENTBOT_BOOST_TIMEOUT_SECONDS": "bad"}):
            with self.assertRaises(ValueError):
                integration._timeout_seconds()
        with mock.patch.dict("os.environ", {"AGENTBOT_BOOST_TIMEOUT_SECONDS": "0"}):
            with self.assertRaises(ValueError):
                integration._timeout_seconds()

        integration.config_path.parent.mkdir()
        integration.config_path.write_text("not valid toml = [\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            integration.ensure_safe_config()


if __name__ == "__main__":
    unittest.main()


class BoostClaudeRegistrationTests(BoostIntegrationTests):
    """Hook files on disk do not mean Claude runs them."""

    def _install_claude_hook_files(self) -> None:
        (self.claude / "hooks").mkdir(parents=True, exist_ok=True)
        (self.claude / "rules").mkdir(parents=True, exist_ok=True)
        (self.claude / "hooks/boost-hook-claude.sh").write_text("#!/bin/sh\n", encoding="utf-8")
        (self.claude / "rules/boost-awareness.md").write_text("# boost\n", encoding="utf-8")

    def _settings(self, payload: dict) -> None:
        self.claude.mkdir(parents=True, exist_ok=True)
        (self.claude / "settings.json").write_text(json.dumps(payload), encoding="utf-8")

    def test_hook_files_without_settings_registration_are_unregistered(self) -> None:
        integration = self._integration_type()(self._paths())
        self._install_claude_hook_files()
        self._settings({"statusLine": {"command": "~/.claude/statusline-command.sh"}})

        self.assertEqual("unregistered", integration._claude_state())

    def test_registered_hook_reads_ready(self) -> None:
        integration = self._integration_type()(self._paths())
        self._install_claude_hook_files()
        self._settings(
            {
                "hooks": {
                    "PreToolUse": [
                        {
                            "matcher": "Bash",
                            "hooks": [{"type": "command", "command": "~/.claude/hooks/boost-hook-claude.sh"}],
                        }
                    ]
                }
            }
        )

        self.assertEqual("ready", integration._claude_state())

    def test_missing_hook_files_still_read_missing(self) -> None:
        integration = self._integration_type()(self._paths())
        self.assertEqual("missing", integration._claude_state())

    def test_unparseable_settings_do_not_claim_registration(self) -> None:
        integration = self._integration_type()(self._paths())
        self._install_claude_hook_files()
        self.claude.mkdir(parents=True, exist_ok=True)
        (self.claude / "settings.json").write_text("{not json", encoding="utf-8")

        self.assertEqual("unregistered", integration._claude_state())


class BoostConfigLockTests(BoostIntegrationTests):
    def test_safe_config_write_holds_the_boost_lock(self) -> None:
        import fcntl

        integration = self._integration_type()(self._paths())
        lock_path = self.root / ".boost/config.toml.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.touch()

        observed: list[bool] = []
        original = integration._ensure_safe_config_locked

        def _record() -> None:
            # A second exclusive flock must fail while the write is in flight.
            with open(lock_path, "a+", encoding="utf-8") as probe:
                try:
                    fcntl.flock(probe.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    observed.append(False)
                    fcntl.flock(probe.fileno(), fcntl.LOCK_UN)
                except OSError:
                    observed.append(True)
            original()

        with mock.patch.object(integration, "_ensure_safe_config_locked", _record):
            integration.ensure_safe_config()

        self.assertEqual([True], observed)

    def test_a_held_lock_fails_loudly_instead_of_racing(self) -> None:
        import fcntl

        from src.boost import CONFIG_LOCK_TIMEOUT_SECONDS

        self.assertGreater(CONFIG_LOCK_TIMEOUT_SECONDS, 0)
        integration = self._integration_type()(self._paths())
        lock_path = self.root / ".boost/config.toml.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.touch()

        with open(lock_path, "a+", encoding="utf-8") as holder:
            fcntl.flock(holder.fileno(), fcntl.LOCK_EX)
            with mock.patch("src.boost.CONFIG_LOCK_TIMEOUT_SECONDS", 0.1):
                with self.assertRaises(ValueError) as caught:
                    integration.ensure_safe_config()
            fcntl.flock(holder.fileno(), fcntl.LOCK_UN)

        self.assertIn("lock", str(caught.exception).lower())


class BoostOffCwdTests(BoostIntegrationTests):
    """Boost v0.12.6 resolves `--uninstall --claude` relative to cwd.

    Install is always global, so running the rollback from a repository
    deletes `<repo>/.claude/...` and leaves `~/.claude` boosted.
    """

    def test_uninstall_runs_from_the_home_directory(self) -> None:
        from src.command_runner import CommandResult

        BoostIntegration = self._integration_type()
        boost = self.root / "boost"
        boost.write_text("binary", encoding="utf-8")
        runner = mock.Mock()

        def run(argv, **_kwargs):
            if argv[-1] == "version":
                return CommandResult(0, stdout="boost v0.12.6\n")
            return CommandResult(0, stdout="Claude Code\nCodex CLI\n")

        runner.run.side_effect = run
        runner.run_interactive.return_value = CommandResult(0)

        with mock.patch("src.boost.shutil.which", return_value=str(boost)):
            BoostIntegration(self._paths(), runner=runner).off()

        home = self.codex.parent
        uninstalls = [
            call
            for call in runner.run_interactive.call_args_list
            if "--uninstall" in call.args[0]
        ]
        self.assertEqual(2, len(uninstalls))
        for call in uninstalls:
            self.assertEqual(home, call.kwargs.get("cwd"))

    def test_setup_is_not_pinned_to_home(self) -> None:
        # Only uninstall has the cwd bug; leave setup's behaviour alone.
        from src.command_runner import CommandResult

        BoostIntegration = self._integration_type()
        boost = self.root / "boost"
        boost.write_text("binary", encoding="utf-8")
        runner = mock.Mock()

        def run(argv, **_kwargs):
            if argv[-1] == "version":
                return CommandResult(0, stdout="boost v0.12.6\n")
            return CommandResult(0, stdout="Claude Code\nCodex CLI\n")

        runner.run.side_effect = run
        runner.run_interactive.return_value = CommandResult(0)

        with mock.patch("src.boost.shutil.which", return_value=str(boost)):
            BoostIntegration(self._paths(), runner=runner).setup()

        for call in runner.run_interactive.call_args_list:
            self.assertIsNone(call.kwargs.get("cwd"))


class BoostCodexRegistrationTests(BoostIntegrationTests):
    """Codex must earn "ready" the same way Claude does.

    `_codex_state` used to return "ready" as soon as hooks.json existed, while
    a comment in `_claude_state` claimed it already checked registration. It
    did not, so an inert Codex install reported ready.
    """

    def _install_codex_files(self) -> None:
        (self.codex / "hooks").mkdir(parents=True, exist_ok=True)
        for name in ("boost-hook-codex.sh", "boost-sync.sh"):
            (self.codex / "hooks" / name).write_text("hook\n", encoding="utf-8")
        (self.codex / "BOOST.md").write_text("# Boost\n", encoding="utf-8")

    def test_hooks_json_without_a_boost_entry_is_unregistered(self) -> None:
        integration = self._integration_type()(self._paths())
        self._install_codex_files()
        (self.codex / "hooks.json").write_text(
            json.dumps({"hooks": {"PreToolUse": [{"hooks": [{"command": "other.sh"}]}]}}),
            encoding="utf-8",
        )
        self.assertEqual("unregistered", integration._codex_state())

    def test_registered_codex_hooks_read_ready(self) -> None:
        integration = self._integration_type()(self._paths())
        self._install_codex_files()
        (self.codex / "hooks.json").write_text(_BOOST_CODEX_HOOKS, encoding="utf-8")
        self.assertEqual("ready", integration._codex_state())

    def test_absent_codex_integration_is_missing(self) -> None:
        integration = self._integration_type()(self._paths())
        self.assertEqual("missing", integration._codex_state())


class BoostRegisteredHookFileTests(BoostIntegrationTests):
    """A half-removed install must not read "ready".

    Boost installs more hook scripts than the two files the state check used to
    require, and registers all of them. Whatever is registered has to be on
    disk, so the check follows the registration rather than a hardcoded list
    that upstream can change under it.
    """

    def _install_claude(self, *, hook_names: tuple[str, ...]) -> None:
        (self.claude / "hooks").mkdir(parents=True, exist_ok=True)
        for name in hook_names:
            (self.claude / "hooks" / name).write_text("hook\n", encoding="utf-8")
        (self.claude / "rules").mkdir(parents=True, exist_ok=True)
        (self.claude / "rules/boost-awareness.md").write_text("rule\n", encoding="utf-8")
        (self.claude / "settings.json").write_text(
            json.dumps(
                {
                    "hooks": {
                        "PreToolUse": [
                            {
                                "hooks": [
                                    {
                                        "type": "command",
                                        "command": "~/.claude/hooks/boost-hook-claude.sh",
                                    }
                                ]
                            }
                        ],
                        "Stop": [
                            {
                                "hooks": [
                                    {
                                        "type": "command",
                                        "command": "~/.claude/hooks/boost-sync.sh",
                                    }
                                ]
                            }
                        ],
                    }
                }
            ),
            encoding="utf-8",
        )

    def test_a_registered_hook_missing_from_disk_is_partial(self) -> None:
        integration = self._integration_type()(self._paths())
        self._install_claude(hook_names=("boost-hook-claude.sh",))
        self.assertEqual("partial", integration._claude_state())

    def test_every_registered_hook_present_is_ready(self) -> None:
        integration = self._integration_type()(self._paths())
        self._install_claude(hook_names=("boost-hook-claude.sh", "boost-sync.sh"))
        self.assertEqual("ready", integration._claude_state())

    def test_a_missing_awareness_file_is_partial(self) -> None:
        integration = self._integration_type()(self._paths())
        self._install_claude(hook_names=("boost-hook-claude.sh", "boost-sync.sh"))
        (self.claude / "rules/boost-awareness.md").unlink()
        self.assertEqual("partial", integration._claude_state())


class BoostShadowingConfigTests(BoostIntegrationTests):
    """Boost reads the FIRST config it finds, and does not merge.

    A repository `.boost/config.toml` replaces `~/.boost/config.toml` outright,
    so the global `tracing.upload = false` stops applying there while Doctor
    still reads the global file and reports it disabled.
    """

    def _register_workspace(self, path: Path) -> None:
        from src.workspace_state import WorkspaceRecord, WorkspaceStore

        path.mkdir(parents=True, exist_ok=True)
        state_file = self._paths().workspace_state_file
        state_file.parent.mkdir(parents=True, exist_ok=True)
        WorkspaceStore(state_file).upsert(
            WorkspaceRecord(
                path=str(path.resolve()),
                kind="directory",
                policy_mode="managed",
                profile="default",
                targets=("agents",),
                enabled=True,
                last_commit=None,
                last_rendered_at=None,
            )
        )

    def _ready_integration(self):
        integration = self._integration_type()(self._paths())
        integration.ensure_safe_config()
        return integration

    def test_a_repository_config_that_leaves_upload_on_is_unsafe(self) -> None:
        integration = self._ready_integration()
        workspace = self.root / "work"
        self._register_workspace(workspace)
        shadow = workspace / ".boost/config.toml"
        shadow.parent.mkdir(parents=True)
        shadow.write_text("[tracing]\nupload = true\n", encoding="utf-8")

        status = integration.status()
        self.assertEqual((shadow,), status.shadowing_configs)
        self.assertEqual("unsafe-config", status.state)
        self.assertIn(str(shadow), status.message)

    def test_a_repository_config_that_disables_upload_is_accepted(self) -> None:
        integration = self._ready_integration()
        workspace = self.root / "work"
        self._register_workspace(workspace)
        shadow = workspace / ".boost/config.toml"
        shadow.parent.mkdir(parents=True)
        shadow.write_text("[tracing]\nupload = false\n", encoding="utf-8")

        self.assertEqual((), integration.status().shadowing_configs)

    def test_no_repository_config_reports_nothing(self) -> None:
        integration = self._ready_integration()
        self._register_workspace(self.root / "work")
        self.assertEqual((), integration.status().shadowing_configs)
