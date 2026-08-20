import io
import sys
import unittest
from unittest.mock import MagicMock, patch


class CliTests(unittest.TestCase):
    def _run_main(self, argv: list[str]) -> tuple[int, str, str]:
        from src.cli import main

        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch.object(sys, "argv", argv), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
            return main(), stdout.getvalue(), stderr.getvalue()

    def _configure_update(self, lifecycle: MagicMock, result) -> None:
        from src.models import UpdateOutcome, UpdatePlan, UpdateSnapshot
        from src.skill_reconcile import SkillReconcilePlan
        from src.workspace_service import WorkspaceReport

        workspace_report = result.workspace_report or WorkspaceReport(())
        lifecycle.plan_update.return_value = UpdatePlan(
            UpdateSnapshot("head", "manifest", None),
            SkillReconcilePlan(
                (),
                tuple(result.added_skills),
                tuple(result.removed_skills),
                (),
                (),
                (),
            ),
            "skip",
            workspace_report,
        )
        lifecycle.apply_update.return_value = UpdateOutcome(
            result.status,
            result.message,
            reconcile=result,
            workspace_report=result.workspace_report,
        )

    def test_command_specs_cover_parser_and_public_dispatcher(self) -> None:
        import argparse

        from src.cli import build_parser
        from src.commands import COMMANDS, commands_for_surface

        parser = build_parser()
        subparsers = next(
            action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
        )
        parser_commands = set(subparsers.choices)
        covered_parser_commands = {
            command for spec in COMMANDS for command in spec.parser_commands
        }
        self.assertEqual(parser_commands, covered_parser_commands)
        self.assertEqual(
            {
                "status", "install", "update", "token", "boot", "workspace",
                "workspaces", "resync", "doctor", "graphify", "help",
            },
            {spec.name for spec in commands_for_surface("public")},
        )

    def test_every_command_spec_has_a_help_detail(self) -> None:
        from src.commands import COMMANDS

        for spec in COMMANDS:
            with self.subTest(command=spec.name):
                rc, stdout, stderr = self._run_main(["agentbot", "help", spec.name])
                self.assertEqual(0, rc, stderr)
                self.assertIn(f"=== {spec.name} ===", stdout)
                for command_option in spec.options:
                    self.assertIn(command_option.usage, stdout)

    def test_help_aliases_resolve_to_canonical_commands(self) -> None:
        for alias, canonical in (("upgrade", "update"), ("skills upgrade", "skills update")):
            with self.subTest(alias=alias):
                rc, stdout, stderr = self._run_main(["agentbot", "help", alias])
                self.assertEqual(0, rc, stderr)
                self.assertIn(f"=== {canonical} ===", stdout)

    @patch("src.cli.default_paths")
    @patch("src.cli.Lifecycle")
    def test_skills_install_refreshes_agent_outputs(self, service_type, _default_paths) -> None:
        service = MagicMock()
        service.install_skills.return_value = []
        service_type.return_value = service

        rc, _stdout, _stderr = self._run_main(["agentbot", "skills", "install"])

        self.assertEqual(0, rc)
        service.refresh_outputs.assert_called_once_with()

    @patch("src.cli.default_paths")
    @patch("src.cli.Lifecycle")
    def test_bootstrap_skill_failure_is_a_clean_cli_error(self, service_type, _default_paths) -> None:
        from src.skills_installer import SkillsInstallError

        service = MagicMock()
        service.install.side_effect = SkillsInstallError("failed to install source 'test': offline")
        service_type.return_value = service

        rc, _stdout, stderr = self._run_main(["agentbot", "bootstrap"])

        self.assertEqual(1, rc)
        self.assertIn("Error: failed to install source 'test': offline", stderr)

    def test_bootstrap_header_uses_install_breadcrumb(self) -> None:
        from pathlib import Path

        from src.cli import run_bootstrap_command
        from src.graphify import GraphifyStatus
        from src.models import DiagnosticsSnapshot, InstallOutcome, OutputRefreshOutcome
        from src.paths import AgentbotPaths

        paths = AgentbotPaths(
            Path("/repo"), Path("/codex"), Path("/claude"), Path("/cursor")
        )
        outcome = InstallOutcome(
            skills=(),
            graphify=GraphifyStatus(
                "not-installed",
                None,
                None,
                Path("/agents/skills/graphify/SKILL.md"),
                None,
                "missing",
                "missing",
                "Graphify is not installed.",
            ),
            outputs=OutputRefreshOutcome(0, 0, 0),
            diagnostics=DiagnosticsSnapshot(
                (), 0, True, True, False, 0, 0, 0, 0, "missing", ()
            ),
        )
        lifecycle = MagicMock()
        lifecycle.install.return_value = outcome
        output = io.StringIO()

        with patch("sys.stdout", output):
            rc = run_bootstrap_command(lifecycle, paths)

        self.assertEqual(0, rc)
        self.assertIn("Agentbot › Install Agentbot", output.getvalue())

    @patch("src.cli.default_paths")
    @patch("src.cli.Lifecycle")
    def test_update_prints_reconciliation_result_report(self, service_type, _default_paths) -> None:
        from pathlib import Path

        from src.skill_reconcile import ReconcileResult

        service = MagicMock()
        self._configure_update(service, ReconcileResult(
            "applied",
            (Path("AGENTS.md"),),
            ("removed-skill",),
            ("added-skill",),
            updated_skills=("updated-skill",),
        ))
        service_type.return_value = service

        rc, stdout, _stderr = self._run_main(["agentbot", "update", "--yes"])

        self.assertEqual(0, rc)
        self.assertIn("Reconciliation report", stdout)
        self.assertIn("added-skill", stdout)
        self.assertIn("removed-skill", stdout)
        self.assertIn("updated-skill", stdout)

    @patch("src.cli.default_paths")
    @patch("src.cli.Lifecycle")
    def test_update_returns_failure_for_global_output_conflict(
        self, service_type, _default_paths
    ) -> None:
        from src.skill_reconcile import ReconcileResult
        from src.workspace_render import RenderAction
        from src.workspace_service import WorkspaceReport

        service = MagicMock()
        self._configure_update(service, ReconcileResult(
            "applied",
            (),
            (),
            (),
            workspace_report=WorkspaceReport(
                results=(),
                global_actions=(
                    RenderAction(
                        "global/AGENTS.md",
                        "conflict",
                        None,
                        "missing global baseline",
                    ),
                ),
            ),
        ))
        service_type.return_value = service

        rc, stdout, _stderr = self._run_main(["agentbot", "update", "--yes"])

        self.assertEqual(1, rc)
        self.assertIn("conflict", stdout)

    @patch("src.cli.default_paths")
    @patch("src.cli.Lifecycle")
    def test_update_accepts_non_conflicting_global_output_actions(
        self, service_type, _default_paths
    ) -> None:
        from src.skill_reconcile import ReconcileResult
        from src.workspace_render import RenderAction
        from src.workspace_service import WorkspaceReport

        actions = tuple(
            RenderAction(f"global/{kind}", kind, None, kind)
            for kind in ("create", "update", "unchanged")
        )
        service = MagicMock()
        self._configure_update(service, ReconcileResult(
            "applied",
            (),
            (),
            (),
            workspace_report=WorkspaceReport(results=(), global_actions=actions),
        ))
        service_type.return_value = service

        rc, _stdout, _stderr = self._run_main(["agentbot", "update", "--yes"])

        self.assertEqual(0, rc)

    @patch("src.cli.default_paths")
    @patch("src.cli.Lifecycle")
    def test_update_returns_failure_for_broken_graphify_setup(
        self, service_type, _default_paths
    ) -> None:
        from src.skill_reconcile import ReconcileResult

        service = MagicMock()
        self._configure_update(service, ReconcileResult(
            "failed", (), (), (), message="Graphify: skill setup failed"
        ))
        service_type.return_value = service

        rc, stdout, _stderr = self._run_main(["agentbot", "update", "--yes"])

        self.assertEqual(1, rc)
        self.assertIn("Graphify: skill setup failed", stdout)

    @patch("src.cli.default_paths")
    @patch("src.cli.Lifecycle")
    def test_upgrade_is_update_alias_and_prints_skill_delta(self, service_type, _default_paths) -> None:
        from src.skill_reconcile import ReconcileResult

        service = MagicMock()
        self._configure_update(service, ReconcileResult(
            "applied", (), ("removed-skill",), (), updated_skills=("updated-skill",)
        ))
        service_type.return_value = service

        rc, stdout, _stderr = self._run_main(["agentbot", "upgrade", "--yes"])

        self.assertEqual(0, rc)
        self.assertIn("Agentbot › Upgrade", stdout)
        self.assertIn("updated-skill", stdout)
        self.assertIn("removed-skill", stdout)
        service.apply_update.assert_called_once_with(service.plan_update.return_value)

    def test_parser_accepts_upgrade_alias(self) -> None:
        from src.cli import build_parser

        args = build_parser().parse_args(["upgrade", "--dry-run"])

        self.assertEqual("upgrade", args.command)
        self.assertTrue(args.dry_run)

    def test_parser_accepts_interactive_update(self) -> None:
        from src.cli import build_parser

        args = build_parser().parse_args(["update", "--interactive"])

        self.assertTrue(args.interactive)

    @patch("src.cli.default_paths")
    @patch("src.cli.Lifecycle")
    @patch("src.cli.confirm_update_plan", return_value=True)
    @patch("src.cli.print_update_plan")
    @patch("src.cli.print_update_outcome")
    def test_interactive_update_applies_the_same_confirmed_plan_once(
        self,
        _print_outcome,
        _print_plan,
        _confirm,
        lifecycle_type,
        _default_paths,
    ) -> None:
        from src.models import UpdateOutcome

        lifecycle = MagicMock()
        plan = MagicMock()
        lifecycle.plan_update.return_value = plan
        lifecycle.apply_update.return_value = UpdateOutcome("applied")
        lifecycle_type.return_value = lifecycle

        rc, _stdout, _stderr = self._run_main(
            ["agentbot", "update", "--interactive"]
        )

        self.assertEqual(0, rc)
        lifecycle.plan_update.assert_called_once_with()
        lifecycle.apply_update.assert_called_once_with(plan)

    def test_parser_accepts_graphify_status_and_setup(self) -> None:
        from src.cli import build_parser

        status = build_parser().parse_args(["graphify", "status"])
        setup = build_parser().parse_args(["graphify", "setup"])

        self.assertEqual("graphify", status.command)
        self.assertEqual("status", status.graphify_command)
        self.assertEqual("setup", setup.graphify_command)

    @patch("src.cli.default_paths")
    @patch("src.cli.Lifecycle")
    def test_graphify_status_is_read_only_and_prints_state(self, service_type, _default_paths) -> None:
        from pathlib import Path

        from src.graphify import GraphifyStatus

        service = MagicMock()
        service.graphify_status.return_value = GraphifyStatus(
            "cli-only",
            None,
            None,
            Path("/tmp/.agents/skills/graphify/SKILL.md"),
            None,
            "missing",
            "missing",
            "Graphify CLI is installed; the Agent Skills integration is not set up.",
        )
        service_type.return_value = service

        rc, stdout, _stderr = self._run_main(["agentbot", "graphify", "status"])

        self.assertEqual(0, rc)
        self.assertIn("Agentbot › Graphify", stdout)
        self.assertIn("cli-only", stdout)
        service.graphify_status.assert_called_once_with()
        service.setup_graphify.assert_not_called()

    @patch("src.cli.default_paths")
    @patch("src.cli.Lifecycle")
    def test_graphify_setup_returns_success_for_ready_state(self, service_type, _default_paths) -> None:
        from pathlib import Path

        from src.graphify import GraphifyStatus

        service = MagicMock()
        service.setup_graphify.return_value = GraphifyStatus(
            "ready",
            Path("/usr/local/bin/graphify"),
            "graphify 1.2.3",
            Path("/tmp/.agents/skills/graphify/SKILL.md"),
            "1.2.3",
            "linked",
            "linked",
            "Graphify CLI and Agent Skills integration are ready.",
        )
        service_type.return_value = service

        rc, stdout, _stderr = self._run_main(["agentbot", "graphify", "setup"])

        self.assertEqual(0, rc)
        self.assertIn("ready", stdout)
        service.setup_graphify.assert_called_once_with()

    @patch("src.cli.default_paths")
    @patch("src.cli.Lifecycle")
    def test_graphify_setup_fails_cleanly_when_cli_is_missing(self, service_type, _default_paths) -> None:
        from pathlib import Path

        from src.graphify import GraphifyStatus

        service = MagicMock()
        service.setup_graphify.return_value = GraphifyStatus(
            "not-installed",
            None,
            None,
            Path("/tmp/.agents/skills/graphify/SKILL.md"),
            None,
            "missing",
            "missing",
            "Graphify CLI and Agent Skills integration are not installed. Install it separately, or run: uv tool install graphifyy",
        )
        service_type.return_value = service

        rc, stdout, _stderr = self._run_main(["agentbot", "graphify", "setup"])

        self.assertEqual(1, rc)
        self.assertIn("uv tool install graphifyy", stdout)

    @patch("src.cli.default_paths")
    @patch("src.cli.Lifecycle")
    @patch("src.cli.Diagnostics")
    def test_status_and_update_use_hierarchical_breadcrumbs(
        self, diagnostics_type, service_type, _default_paths
    ) -> None:
        from src.models import DiagnosticsSnapshot
        from src.skill_reconcile import ReconcileResult

        service = MagicMock()
        diagnostics_type.return_value.collect.return_value = DiagnosticsSnapshot(
            installed_skills=("alpha",),
            enabled_sources=1,
            global_agents_exists=True,
            skills_sources_exists=True,
            global_lock_exists=True,
            global_lock_skills=1,
            managed_skill_count=1,
            manual_skill_count=0,
            claude_bridge_links=1,
            claude_statusline_state="ok",
            issues=(),
        )
        self._configure_update(service, ReconcileResult(
            "preview", (), (), ()
        ))
        service_type.return_value = service

        status_rc, status_stdout, _ = self._run_main(["agentbot", "status"])
        update_rc, update_stdout, _ = self._run_main(["agentbot", "update", "--dry-run"])

        self.assertEqual(0, status_rc)
        self.assertEqual(0, update_rc)
        self.assertIn("Agentbot › Check Status", status_stdout)
        self.assertIn("Agentbot › Update", update_stdout)

    def test_status_labels_trial_skills_outside_managed_sources(self) -> None:
        from src.ui import print_status_summary

        output = io.StringIO()
        with patch("sys.stdout", output):
            print_status_summary(
                installed_skills=4,
                global_agents_exists=True,
                skills_sources_exists=True,
                enabled_sources=1,
                global_lock_exists=True,
                global_lock_skills=4,
                claude_bridge_links=4,
                claude_statusline_state="ok",
                manual_skill_count=4,
                doctor_issue_count=4,
            )

        rendered = output.getvalue()
        self.assertIn("4 outside managed sources", rendered)
        self.assertNotIn("outside global lock", rendered)

    @patch("src.cli.default_paths")
    @patch("src.cli.Lifecycle")
    @patch("src.cli.Diagnostics")
    def test_status_doctor_renders_one_snapshot(
        self, diagnostics_type, _lifecycle_type, _default_paths
    ) -> None:
        from src.models import DiagnosticsSnapshot, DoctorIssue

        diagnostics = diagnostics_type.return_value
        diagnostics.collect.return_value = DiagnosticsSnapshot(
            (), 1, True, True, False, 0, 0, 0, 0, "missing",
            (DoctorIssue("error", "global", "baseline is missing"),),
        )

        rc, stdout, _stderr = self._run_main(["agentbot", "status", "--doctor"])

        self.assertEqual(1, rc)
        diagnostics.collect.assert_called_once_with()
        self.assertIn("Skills & baseline", stdout)
        self.assertIn("Doctor issues", stdout)
        self.assertIn("baseline is missing", stdout)

    def test_table_model_exposes_json_compatible_rows(self) -> None:
        from src.models import Table, TableSection
        from src.ui import table_rows

        table = Table(
            "Status",
            "Agentbot › Check Status",
            (TableSection("Health", (("Agentbot", "current", "ok"),)),),
        )

        self.assertEqual(
            [{"section": "Health", "component": "Agentbot", "detail": "current", "result": "ok"}],
            table_rows(table),
        )

    @patch("src.cli.default_paths")
    @patch("src.cli.Lifecycle")
    def test_update_reconciliation_report_has_one_table_header(self, service_type, _default_paths) -> None:
        from pathlib import Path

        from src.skill_reconcile import ReconcileResult

        service = MagicMock()
        self._configure_update(service, ReconcileResult(
            "preview", (Path("AGENTS.md"),), ("added",), ("removed",)
        ))
        service_type.return_value = service

        rc, stdout, _ = self._run_main(["agentbot", "update", "--dry-run"])

        self.assertEqual(0, rc)
        self.assertEqual(1, stdout.count("  component              | detail"))

    def test_reconciliation_report_shows_every_skill_in_each_delta(self) -> None:
        from src.skill_reconcile import ReconcileResult
        from src.ui import print_reconciliation_report

        result = ReconcileResult(
            "applied",
            (),
            tuple(f"removed-skill-{index}" for index in range(1, 8)),
            tuple(f"added-skill-{index}" for index in range(1, 8)),
            updated_skills=tuple(f"updated-skill-{index}" for index in range(1, 8)),
        )
        output = io.StringIO()
        with patch("sys.stdout", output):
            print_reconciliation_report(result)

        rendered = output.getvalue()
        for skill in (*result.updated_skills, *result.added_skills, *result.removed_skills):
            self.assertIn(skill, rendered)

    def test_preview_result_uses_informational_color(self) -> None:
        import os

        from src.ui import color_result

        with patch.dict(os.environ, {"AGENTBOT_TUI": "1"}, clear=False):
            os.environ.pop("NO_COLOR", None)
            self.assertEqual("\033[36mpreview\033[0m", color_result("preview"))

    def test_shared_palette_hierarchy(self) -> None:
        import os

        from src.ui import print_header, print_section

        output = io.StringIO()
        with patch.dict(os.environ, {"AGENTBOT_TUI": "1"}, clear=False):
            os.environ.pop("NO_COLOR", None)
            with patch("sys.stdout", output):
                print_header("Status", "Agentbot › Status")
                print_section("── Sources ──")

        rendered = output.getvalue()
        self.assertIn("\033[1m\033[38;5;208m=== Status ===\033[0m", rendered)
        self.assertIn("\033[1m\033[33m── Sources ──\033[0m", rendered)

    def test_reports_use_hierarchical_breadcrumbs(self) -> None:
        from src.ui import print_doctor_summary, print_skills_report

        output = io.StringIO()
        with patch("sys.stdout", output):
            print_doctor_summary([])
            print_skills_report([], title="Skills install")

        rendered = output.getvalue()
        self.assertIn("Agentbot › Doctor", rendered)
        self.assertIn("Agentbot › Skills install", rendered)

    def test_doctor_report_wraps_full_issue_details(self) -> None:
        from src.models import DoctorIssue
        from src.ui import print_doctor_summary

        message = (
            "Manual skill 'brainstorming' is available but outside managed sources; "
            "add a manifest source to make it reproducible"
        )
        output = io.StringIO()
        with patch("sys.stdout", output):
            print_doctor_summary([DoctorIssue("warning", "reproducibility", message)])

        rendered = output.getvalue()
        self.assertIn("Manual skill 'brainstorming' is", rendered)
        self.assertIn("available but outside managed sources;", rendered)
        self.assertIn("add a manifest source to make it", rendered)
        self.assertIn("reproducible", rendered)
        self.assertNotIn("...", output.getvalue())

    def test_python_reports_fit_tui_widths(self) -> None:
        import os

        from src.models import DoctorIssue
        from src.ui import print_doctor_summary, strip_ansi

        issue = DoctorIssue(
            "warning",
            "reproducibility",
            "A deliberately long diagnostic remains width-safe at every supported terminal size",
        )
        for columns in (48, 80, 120):
            output = io.StringIO()
            with patch.dict(
                os.environ,
                {"AGENTBOT_TUI": "1", "AGENTBOT_MENU_COLS": str(columns), "NO_COLOR": "1"},
                clear=False,
            ):
                with patch("sys.stdout", output):
                    print_doctor_summary([issue])
            for line in strip_ansi(output.getvalue()).splitlines():
                self.assertLessEqual(len(line), columns, (columns, line))

    def test_doctor_highlights_manual_skill_names_without_shifting_columns(self) -> None:
        import os

        from src.models import DoctorIssue
        from src.ui import print_doctor_summary, strip_ansi

        issues = [
            DoctorIssue(
                "warning",
                "reproducibility",
                "Manual skill 'writing-clearly-and-concisely' is outside managed sources",
            ),
            DoctorIssue("warning", "token", "saved token path 'example' needs attention"),
        ]
        output = io.StringIO()
        with patch.dict(os.environ, {"FORCE_COLOR": "1"}, clear=False):
            os.environ.pop("NO_COLOR", None)
            with patch("sys.stdout", output):
                print_doctor_summary(issues)

        rendered = output.getvalue()
        self.assertIn(
            "\033[1m\033[36mwriting-clearly-and-concisely\033[0m",
            rendered,
        )
        self.assertEqual(1, rendered.count("\033[1m\033[36m"))
        highlighted_line = next(
            line for line in rendered.splitlines() if "writing-clearly-and-concisely" in line
        )
        separators = [
            index
            for index, char in enumerate(strip_ansi(highlighted_line))
            if char == "|"
        ]
        self.assertEqual([25, 68], separators)

        plain_output = io.StringIO()
        with patch.dict(os.environ, {"NO_COLOR": "1"}, clear=False):
            with patch("sys.stdout", plain_output):
                print_doctor_summary(issues)
        self.assertNotIn("\033[", plain_output.getvalue())
        self.assertIn("'writing-clearly-and-concisely'", plain_output.getvalue())

    def test_parser_and_paths_use_agentbot_product_contract(self) -> None:
        import os
        import tempfile
        from pathlib import Path

        from src.cli import build_parser
        from src.paths import AgentbotPaths, default_paths

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "agent_bootstrap"
            xdg = Path(temp_dir) / "config"
            with patch.dict(
                os.environ,
                {"AGENTBOT_HOME": str(root), "XDG_CONFIG_HOME": str(xdg)},
                clear=False,
            ):
                args = build_parser().parse_args(["status"])
                paths = default_paths()

        self.assertEqual("agentbot", build_parser().prog)
        self.assertEqual(root, Path(args.root))
        self.assertIsInstance(paths, AgentbotPaths)
        self.assertEqual(root, paths.root)
        self.assertEqual(xdg / "agentbot", paths.config_home)
        self.assertEqual(root / "agentos.yaml", paths.workspace_profiles_file)
        self.assertEqual(xdg / "agentbot" / "workspaces.json", paths.workspace_state_file)


if __name__ == "__main__":
    unittest.main()
