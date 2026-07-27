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

    @patch("src.cli.default_paths")
    @patch("src.cli.AgentbotService")
    def test_skills_install_refreshes_agent_outputs(self, service_type, _default_paths) -> None:
        service = MagicMock()
        service.install_skills.return_value = []
        service.refresh_agent_outputs.return_value = (0, 0, 0)
        service_type.return_value = service

        rc, _stdout, _stderr = self._run_main(["agentbot", "skills", "install"])

        self.assertEqual(0, rc)
        service.refresh_agent_outputs.assert_called_once_with()

    @patch("src.cli.default_paths")
    @patch("src.cli.AgentbotService")
    def test_bootstrap_skill_failure_is_a_clean_cli_error(self, service_type, _default_paths) -> None:
        from src.skills_installer import SkillsInstallError

        service = MagicMock()
        service.run_bootstrap.side_effect = SkillsInstallError("failed to install source 'test': offline")
        service_type.return_value = service

        rc, _stdout, stderr = self._run_main(["agentbot", "bootstrap"])

        self.assertEqual(1, rc)
        self.assertIn("Error: failed to install source 'test': offline", stderr)

    @patch("src.cli.default_paths")
    @patch("src.cli.AgentbotService")
    def test_update_prints_reconciliation_result_report(self, service_type, _default_paths) -> None:
        from pathlib import Path
        from src.skill_reconcile import ReconcileResult

        service = MagicMock()
        service.run_reconciliation_update.return_value = ReconcileResult(
            "applied",
            (Path("AGENTS.md"),),
            ("removed-skill",),
            ("added-skill",),
            updated_skills=("updated-skill",),
        )
        service_type.return_value = service

        rc, stdout, _stderr = self._run_main(["agentbot", "update", "--yes"])

        self.assertEqual(0, rc)
        self.assertIn("Reconciliation report", stdout)
        self.assertIn("added-skill", stdout)
        self.assertIn("removed-skill", stdout)
        self.assertIn("updated-skill", stdout)

    @patch("src.cli.default_paths")
    @patch("src.cli.AgentbotService")
    def test_upgrade_is_update_alias_and_prints_skill_delta(self, service_type, _default_paths) -> None:
        from src.skill_reconcile import ReconcileResult

        service = MagicMock()
        service.run_reconciliation_update.return_value = ReconcileResult(
            "applied", (), ("removed-skill",), (), updated_skills=("updated-skill",)
        )
        service_type.return_value = service

        rc, stdout, _stderr = self._run_main(["agentbot", "upgrade", "--yes"])

        self.assertEqual(0, rc)
        self.assertIn("Agentbot › Upgrade", stdout)
        self.assertIn("updated-skill", stdout)
        self.assertIn("removed-skill", stdout)
        service.run_reconciliation_update.assert_called_once_with(dry_run=False, confirm=True)

    def test_parser_accepts_upgrade_alias(self) -> None:
        from src.cli import build_parser

        args = build_parser().parse_args(["upgrade", "--dry-run"])

        self.assertEqual("upgrade", args.command)
        self.assertTrue(args.dry_run)

    def test_parser_accepts_graphify_status_and_setup(self) -> None:
        from src.cli import build_parser

        status = build_parser().parse_args(["graphify", "status"])
        setup = build_parser().parse_args(["graphify", "setup"])

        self.assertEqual("graphify", status.command)
        self.assertEqual("status", status.graphify_command)
        self.assertEqual("setup", setup.graphify_command)

    @patch("src.cli.default_paths")
    @patch("src.cli.AgentbotService")
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
    @patch("src.cli.AgentbotService")
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
    @patch("src.cli.AgentbotService")
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
            "Graphify CLI and Agent Skills integration are not installed. Install it from Dotfiles > Install Dotfiles > Graphify CLI, or run: uv tool install graphifyy",
        )
        service_type.return_value = service

        rc, stdout, _stderr = self._run_main(["agentbot", "graphify", "setup"])

        self.assertEqual(1, rc)
        self.assertIn("uv tool install graphifyy", stdout)

    @patch("src.cli.default_paths")
    @patch("src.cli.AgentbotService")
    def test_status_and_update_use_hierarchical_breadcrumbs(self, service_type, _default_paths) -> None:
        from src.skill_reconcile import ReconcileResult

        service = MagicMock()
        service.status_summary.return_value = {
            "installed_skills": 1,
            "global_agents_exists": True,
            "skills_sources_exists": True,
            "enabled_sources": 1,
            "global_lock_exists": True,
            "global_lock_skills": 1,
            "claude_bridge_links": 1,
            "manual_skill_count": 0,
            "doctor_issue_count": 0,
        }
        service.run_reconciliation_update.return_value = ReconcileResult(
            "preview", (), (), ()
        )
        service_type.return_value = service

        status_rc, status_stdout, _ = self._run_main(["agentbot", "status"])
        update_rc, update_stdout, _ = self._run_main(["agentbot", "update", "--dry-run"])

        self.assertEqual(0, status_rc)
        self.assertEqual(0, update_rc)
        self.assertIn("Agentbot › Status", status_stdout)
        self.assertIn("Agentbot › Update", update_stdout)

    @patch("src.cli.default_paths")
    @patch("src.cli.AgentbotService")
    def test_update_reconciliation_report_has_one_table_header(self, service_type, _default_paths) -> None:
        from pathlib import Path
        from src.skill_reconcile import ReconcileResult

        service = MagicMock()
        service.run_reconciliation_update.return_value = ReconcileResult(
            "preview", (Path("AGENTS.md"),), ("added",), ("removed",)
        )
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
            "Manual skill 'brainstorming' is available but outside the global lock; "
            "add a manifest source to make it reproducible"
        )
        output = io.StringIO()
        with patch("sys.stdout", output):
            print_doctor_summary([DoctorIssue("warning", "reproducibility", message)])

        rendered = output.getvalue()
        self.assertIn("Manual skill 'brainstorming' is", rendered)
        self.assertIn("available but outside the global lock;", rendered)
        self.assertIn("add a manifest source to make it", rendered)
        self.assertIn("reproducible", rendered)
        self.assertNotIn("...", output.getvalue())

    def test_doctor_highlights_manual_skill_names_without_shifting_columns(self) -> None:
        import os

        from src.models import DoctorIssue
        from src.ui import print_doctor_summary, strip_ansi

        issues = [
            DoctorIssue(
                "warning",
                "reproducibility",
                "Manual skill 'writing-clearly-and-concisely' is outside the global lock",
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
