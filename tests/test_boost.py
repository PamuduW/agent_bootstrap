import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 compatibility
    import tomli as tomllib

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
        boost = self.root / ".local/bin/boost"
        boost.parent.mkdir(parents=True, exist_ok=True)
        boost.write_text("#!/bin/sh\nprintf 'boost v0.12.6\\n'\n", encoding="utf-8")
        boost.chmod(0o755)
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


class BoostArtifactVersionTests(BoostIntegrationTests):
    """Hook and awareness files carry the version of the release that wrote them.

    Dotfiles owns the binary and Agentbot owns the integration, so upgrading
    Boost refreshes neither. `dotfiles full-update` happens to close this by
    running `agentbot install` afterwards, which re-runs `boost init`;
    `dotfiles update` alone does not, and a silently skipped setup would not
    either. The gap is invisible without a check, because every file is
    present and registered -- just stale.
    """

    def _install(self, *, marker: str | None, version: str = "v0.12.6") -> None:
        (self.claude / "hooks").mkdir(parents=True, exist_ok=True)
        stamp = f"# boost-hook-version: {marker}\n" if marker else ""
        (self.claude / "hooks/boost-hook-claude.sh").write_text(
            f"#!/bin/sh\n{stamp}", encoding="utf-8"
        )
        (self.claude / "rules").mkdir(parents=True, exist_ok=True)
        (self.claude / "rules/boost-awareness.md").write_text(
            f"# boost-skill-version: {marker}\n" if marker else "# boost\n",
            encoding="utf-8",
        )
        (self.claude / "settings.json").write_text(_BOOST_CLAUDE_SETTINGS, encoding="utf-8")
        (self.codex / "hooks").mkdir(parents=True, exist_ok=True)
        for name in ("boost-hook-codex.sh", "boost-sync.sh"):
            (self.codex / "hooks" / name).write_text(f"#!/bin/sh\n{stamp}", encoding="utf-8")
        (self.codex / "hooks.json").write_text(_BOOST_CODEX_HOOKS, encoding="utf-8")
        (self.codex / "BOOST.md").write_text(
            f"# boost-skill-version: {marker}\n" if marker else "# Boost\n",
            encoding="utf-8",
        )

    def _status(self, version: str = "boost v0.12.6"):
        from src.command_runner import CommandResult

        boost = self.root / "boost"
        boost.write_text("binary", encoding="utf-8")
        runner = mock.Mock()
        runner.run.return_value = CommandResult(0, stdout=f"{version}\n")
        integration = self._integration_type()(self._paths(), runner=runner)
        integration.ensure_safe_config()
        with mock.patch("src.boost.shutil.which", return_value=str(boost)):
            return integration.status()

    def test_artifacts_from_an_older_release_are_stale(self) -> None:
        self._install(marker="v0.12.5")
        status = self._status("boost v0.12.6")
        self.assertEqual("stale", status.state)
        self.assertTrue(status.stale_artifacts)
        self.assertIn("v0.12.6", status.message)
        # Every stamped surface is named, not just the first one found.
        names = {path.name for path in status.stale_artifacts}
        self.assertIn("boost-hook-claude.sh", names)
        self.assertIn("boost-hook-codex.sh", names)
        self.assertIn("boost-awareness.md", names)

    def test_artifacts_matching_the_cli_are_ready(self) -> None:
        self._install(marker="v0.12.6")
        status = self._status("boost v0.12.6")
        self.assertEqual("ready", status.state)
        self.assertEqual((), status.stale_artifacts)

    def test_unstamped_artifacts_are_not_reported_stale(self) -> None:
        # Upstream owns that comment and may drop it. A daily false "stale"
        # would train the row to be ignored, which is worse than not checking.
        self._install(marker=None)
        status = self._status("boost v0.12.6")
        self.assertEqual("ready", status.state)
        self.assertEqual((), status.stale_artifacts)

    def test_an_unreadable_cli_version_disables_the_check(self) -> None:
        from src.command_runner import CommandResult

        self._install(marker="v0.12.5")
        boost = self.root / "boost"
        boost.write_text("binary", encoding="utf-8")
        runner = mock.Mock()
        runner.run.return_value = CommandResult(1, stderr="boom")
        integration = self._integration_type()(self._paths(), runner=runner)
        integration.ensure_safe_config()
        with mock.patch("src.boost.shutil.which", return_value=str(boost)):
            status = integration.status()
        self.assertEqual((), status.stale_artifacts)

    def test_a_forbidden_graph_write_outranks_staleness(self) -> None:
        self._install(marker="v0.12.5")
        (self.codex / "hooks.json").write_text('{"server":"boostgraph"}\n', encoding="utf-8")
        self.assertEqual("forbidden", self._status().state)


class BoostFeatureFlagTests(BoostIntegrationTests):
    """Boost feature flags are a declared set that setup enforces.

    Boost's report UI writes `user = <bool>` under `[feature_flags."name"]`, and
    a user value beats the remote default. Four were toggled on this machine --
    including BoostGraph -- while Doctor stayed silent, because the config check
    only ever read `tracing.upload` and `update.auto_update`.

    Agentbot now declares the intended value for each. A flag left unpinned
    counts as diverged: its effective value falls back to a remote default that
    JFrog can change under the machine.
    """

    def _config(self, body: str) -> None:
        path = self.root / ".boost/config.toml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "[tracing]\nupload = false\n\n[update]\nauto_update = false\n\n" + body,
            encoding="utf-8",
        )

    def _parsed(self):
        return tomllib.loads((self.root / ".boost/config.toml").read_text(encoding="utf-8"))

    def _status(self):
        from src.command_runner import CommandResult

        boost = self.root / "boost"
        boost.write_text("binary", encoding="utf-8")
        runner = mock.Mock()
        runner.run.return_value = CommandResult(0, stdout="boost v0.12.6\n")
        with mock.patch("src.boost.shutil.which", return_value=str(boost)):
            return self._integration_type()(self._paths(), runner=runner).status()

    def test_policy_declares_every_flag_agentbot_has_a_stake_in(self) -> None:
        from src.boost import BOOST_FEATURE_POLICY

        self.assertEqual(
            {
                "boost-agent-facing-redaction": True,
                "boost-english-abbreviation": False,
                "boost-files-optimization": True,
                "boost-graph-integration": False,
                "boost-mcp-toon-format": True,
            },
            dict(BOOST_FEATURE_POLICY),
        )

    def test_safe_config_writes_the_declared_set(self) -> None:
        self._config('[feature_flags."boost-graph-integration"]\nuser = true\nremote = false\n')
        self._integration_type()(self._paths()).ensure_safe_config()

        flags = self._parsed()["feature_flags"]
        self.assertIs(False, flags["boost-graph-integration"]["user"])
        self.assertIs(True, flags["boost-agent-facing-redaction"]["user"])
        self.assertIs(False, flags["boost-english-abbreviation"]["user"])
        self.assertIs(True, flags["boost-files-optimization"]["user"])
        self.assertIs(True, flags["boost-mcp-toon-format"]["user"])
        # The remote value is JFrog's to set; only `user` is ours.
        self.assertIs(False, flags["boost-graph-integration"]["remote"])

    def test_safe_config_preserves_flags_outside_the_declared_set(self) -> None:
        self._config(
            '[feature_flags."boost-share-cli-outputs"]\nuser = true\nremote = false\n\n'
            '[feature_flags._metadata]\nlast_updated_at = "2026-08-25T00:00:00Z"\n'
        )
        self._integration_type()(self._paths()).ensure_safe_config()

        flags = self._parsed()["feature_flags"]
        self.assertIs(True, flags["boost-share-cli-outputs"]["user"])
        self.assertEqual("2026-08-25T00:00:00Z", flags["_metadata"]["last_updated_at"])
        self.assertFalse(self._parsed()["tracing"]["upload"])

    def test_user_overrides_are_collected_and_remote_only_flags_are_not(self) -> None:
        self._config(
            '[feature_flags."boost-english-abbreviation"]\nuser = true\nremote = false\n\n'
            '[feature_flags."boost-cli-filtering"]\nremote = true\n'
        )
        status = self._status()
        self.assertIn(("boost-english-abbreviation", True), status.user_flags)
        self.assertNotIn(
            "boost-cli-filtering", [name for name, _ in status.user_flags]
        )

    def test_flags_matching_policy_do_not_diverge(self) -> None:
        from src.diagnostics import Diagnostics

        self._integration_type()(self._paths()).ensure_safe_config()
        status = self._status()
        self.assertEqual((), status.diverged_flags)
        self.assertEqual([], Diagnostics(self._paths())._boost_flag_issues(status))

    def test_a_flag_flipped_against_policy_diverges(self) -> None:
        from src.diagnostics import Diagnostics

        self._integration_type()(self._paths()).ensure_safe_config()
        self._config('[feature_flags."boost-graph-integration"]\nuser = true\nremote = false\n')
        status = self._status()

        self.assertIn("boost-graph-integration", status.diverged_flags)
        issues = Diagnostics(self._paths())._boost_flag_issues(status)
        self.assertEqual(1, len(issues))
        self.assertEqual("warning", issues[0].level)
        self.assertIn("boost-graph-integration", issues[0].message)
        self.assertIn("agentbot boost setup", issues[0].message)

    def test_an_unpinned_flag_counts_as_diverged(self) -> None:
        # Unpinned means the effective value is a remote default JFrog can
        # change without warning, which is the drift the policy exists to stop.
        self._config('[feature_flags."boost-cli-filtering"]\nremote = true\n')
        self.assertEqual(
            (
                "boost-agent-facing-redaction",
                "boost-english-abbreviation",
                "boost-files-optimization",
                "boost-graph-integration",
                "boost-mcp-toon-format",
            ),
            self._status().diverged_flags,
        )


class BoostRepositoryGraphIndexTests(BoostIntegrationTests):
    """A repository `.boost/` index is a forbidden write the plan names but nothing checked."""

    def _workspace(self) -> Path:
        from src.workspace_state import WorkspaceRecord, WorkspaceStore

        path = self.root / "work"
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
        return path

    def test_a_repository_graph_index_is_forbidden(self) -> None:
        workspace = self._workspace()
        index = workspace / ".boost"
        index.mkdir()
        (index / "graph.db").write_text("index", encoding="utf-8")
        integration = self._integration_type()(self._paths())
        self.assertTrue(integration._forbidden_graph_evidence())

    def test_a_repository_config_alone_is_not_a_graph_index(self) -> None:
        workspace = self._workspace()
        index = workspace / ".boost"
        index.mkdir()
        (index / "config.toml").write_text("[tracing]\nupload = false\n", encoding="utf-8")
        (index / "config.toml.lock").write_text("", encoding="utf-8")
        integration = self._integration_type()(self._paths())
        self.assertFalse(integration._forbidden_graph_evidence())
