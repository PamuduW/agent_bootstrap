import os
import stat
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


class GraphifyIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.home = self.root / "home"
        self.fake_bin = self.root / "bin"
        self.home.mkdir()
        self.fake_bin.mkdir()
        (self.root / "global").mkdir()
        (self.root / "global" / "AGENTS.md").write_text("# baseline\n", encoding="utf-8")
        self.paths = None

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _env(self) -> dict[str, str]:
        return {
            "HOME": str(self.home),
            "PATH": f"{self.fake_bin}:{os.environ['PATH']}",
        }

    def _write_graphify(self, *, version: str = "1.2.3") -> Path:
        executable = self.fake_bin / "graphify"
        executable.write_text(
            "#!/usr/bin/env bash\n"
            "if [[ \"$1\" == --version ]]; then printf 'graphify %s\\n' '" + version + "'; exit 0; fi\n"
            "if [[ \"$1 $2 $3\" == 'install --platform agents' ]]; then\n"
            "  mkdir -p \"$HOME/.agents/skills/graphify\"\n"
            "  printf '# graphify\\n' >\"$HOME/.agents/skills/graphify/SKILL.md\"\n"
            "  printf '%s\\n' '" + version + "' >\"$HOME/.agents/skills/graphify/.graphify_version\"\n"
            "  printf '%s\\n' \"$*\" >>\"$GRAPHIFY_TEST_LOG\"\n"
            "  exit 0\n"
            "fi\n"
            "exit 23\n",
            encoding="utf-8",
        )
        executable.chmod(executable.stat().st_mode | stat.S_IEXEC)
        return executable

    def _paths(self):
        from src.paths import AgentbotPaths

        return AgentbotPaths(
            self.root,
            self.root / "codex",
            self.root / "claude",
            self.root / "cursor",
        )

    def test_status_reports_not_installed_without_writing(self) -> None:
        from src.graphify import GraphifyIntegration

        paths = self._paths()
        before = sorted(path.relative_to(self.root) for path in self.root.rglob("*"))
        with patch("src.graphify.shutil.which", return_value=None), patch.dict(
            os.environ, self._env(), clear=False
        ):
            status = GraphifyIntegration(paths).status()
        after = sorted(path.relative_to(self.root) for path in self.root.rglob("*"))

        self.assertEqual("not-installed", status.state)
        self.assertEqual(before, after)
        self.assertIsNone(status.cli_version)

    def test_status_reports_cli_only(self) -> None:
        from src.graphify import GraphifyIntegration

        self._write_graphify()
        with patch.dict(os.environ, self._env(), clear=False):
            status = GraphifyIntegration(self._paths()).status()

        self.assertEqual("cli-only", status.state)
        self.assertEqual("graphify 1.2.3", status.cli_version)

    def test_setup_uses_only_generic_agent_skills_command(self) -> None:
        from src.graphify import GraphifyIntegration

        self._write_graphify()
        log = self.root / "graphify.log"
        with patch.dict(
            os.environ,
            {**self._env(), "GRAPHIFY_TEST_LOG": str(log)},
            clear=False,
        ):
            status = GraphifyIntegration(self._paths()).setup()

        self.assertEqual("ready", status.state)
        self.assertEqual("install --platform agents", log.read_text(encoding="utf-8").strip())
        self.assertTrue((self.home / ".agents/skills/graphify/SKILL.md").is_file())
        self.assertFalse((self.root / "AGENTS.md").exists())
        self.assertFalse((self.root / ".cursor").exists())

    def test_status_reports_stale_skill_version(self) -> None:
        from src.graphify import GraphifyIntegration

        self._write_graphify(version="2.0.0")
        skill_dir = self.home / ".agents/skills/graphify"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# graphify\n", encoding="utf-8")
        (skill_dir / ".graphify_version").write_text("1.0.0\n", encoding="utf-8")
        with patch.dict(os.environ, self._env(), clear=False):
            status = GraphifyIntegration(self._paths()).status()

        self.assertEqual("stale", status.state)
        self.assertEqual("1.0.0", status.skill_version)

    def test_status_preserves_and_reports_conflicting_assistant_target(self) -> None:
        from src.graphify import GraphifyIntegration

        self._write_graphify()
        skill_dir = self.home / ".agents/skills/graphify"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# graphify\n", encoding="utf-8")
        (skill_dir / ".graphify_version").write_text("1.2.3\n", encoding="utf-8")
        claude_target = self.root / "claude/skills/graphify"
        claude_target.mkdir(parents=True)
        (claude_target / "SKILL.md").write_text("# user-owned\n", encoding="utf-8")
        with patch.dict(os.environ, self._env(), clear=False):
            status = GraphifyIntegration(self._paths()).status()

        self.assertEqual("conflict", status.state)
        self.assertEqual("conflict", status.claude_state)
        self.assertEqual("# user-owned\n", (claude_target / "SKILL.md").read_text(encoding="utf-8"))

    def test_setup_fails_with_actionable_message_when_cli_is_absent(self) -> None:
        from src.graphify import GraphifyIntegration

        with patch("src.graphify.shutil.which", return_value=None), patch.dict(
            os.environ, self._env(), clear=False
        ):
            status = GraphifyIntegration(self._paths()).setup()

        self.assertEqual("not-installed", status.state)
        self.assertIn("uv tool install graphifyy", status.message)

    def test_service_setup_refreshes_existing_agent_outputs(self) -> None:
        from src.service import AgentbotService

        self._write_graphify()
        log = self.root / "graphify-service.log"
        service = AgentbotService(self._paths())
        with patch.dict(
            os.environ,
            {**self._env(), "GRAPHIFY_TEST_LOG": str(log)},
            clear=False,
        ), patch.object(service, "refresh_agent_outputs", return_value=(0, 0, 0)) as refresh:
            status = service.setup_graphify()

        self.assertEqual("ready", status.state)
        refresh.assert_called_once_with()

    def test_service_sync_enables_graphify_when_cli_exists(self) -> None:
        from src.service import AgentbotService

        self._write_graphify()
        log = self.root / "graphify-sync.log"
        service = AgentbotService(self._paths())
        with patch.dict(
            os.environ,
            {**self._env(), "GRAPHIFY_TEST_LOG": str(log)},
            clear=False,
        ), patch.object(
            service, "refresh_agent_outputs", return_value=(0, 0, 0)
        ) as refresh:
            status = service.sync_graphify_if_cli_available()

        self.assertEqual("ready", status.state)
        self.assertEqual("install --platform agents", log.read_text(encoding="utf-8").strip())
        refresh.assert_called_once_with()

    def test_bootstrap_reports_broken_graphify_as_failure(self) -> None:
        from src.graphify import GraphifyStatus
        from src.service import AgentbotService

        service = AgentbotService(self._paths())
        broken = GraphifyStatus(
            "broken",
            self.fake_bin / "graphify",
            "graphify 1.2.3",
            self.home / ".agents/skills/graphify/SKILL.md",
            None,
            "missing",
            "missing",
            "Graphify skill setup failed: exit 23",
        )
        with patch("src.service.run_skills_install", return_value=[]), patch(
            "src.service.print_skills_report", return_value=0
        ), patch.object(
            service, "sync_graphify_if_cli_available", return_value=broken
        ), patch.object(
            service, "refresh_agent_outputs", return_value=(0, 0, 0)
        ) as refresh, patch.object(
            service, "doctor_issues", return_value=[]
        ), patch.object(
            service, "skills_doctor_issues", return_value=[]
        ), patch(
            "src.service.print_graphify_status"
        ) as print_status:
            rc = service.run_bootstrap()

        self.assertEqual(1, rc)
        refresh.assert_called_once_with()
        print_status.assert_called_once_with(broken)

    def test_reconciliation_update_refreshes_enabled_graphify_before_one_output_render(self) -> None:
        from src.service import AgentbotService
        from src.skill_reconcile import ReconcileResult
        from src.workspace_service import WorkspaceReport

        service = AgentbotService(self._paths())
        with patch.object(service, "update_skills", return_value=SimpleNamespace(stdout="", stderr="")), \
             patch.object(service, "reconcile_skills", return_value=ReconcileResult("applied", (), (), ())), \
             patch.object(service, "sync_graphify_if_cli_available", return_value=None) as refresh_graphify, \
             patch.object(
                 service,
                 "resync_workspaces",
                 return_value=WorkspaceReport(results=()),
             ) as resync:
            result = service.run_reconciliation_update()

        self.assertEqual("applied", result.status)
        refresh_graphify.assert_called_once_with(refresh_outputs=False)
        resync.assert_called_once_with(apply=True)
        self.assertIs(result.workspace_report, resync.return_value)

    def test_reconciliation_dry_run_reports_enabled_graphify_without_setup(self) -> None:
        from src.graphify import GraphifyStatus
        from src.service import AgentbotService
        from src.skill_reconcile import ReconcileResult
        from src.workspace_service import WorkspaceReport

        skill_path = self.root / "graphify" / "SKILL.md"
        skill_path.parent.mkdir()
        skill_path.write_text("# graphify\n", encoding="utf-8")
        service = AgentbotService(self._paths())
        status = GraphifyStatus(
            "ready",
            self.fake_bin / "graphify",
            "graphify 1.2.3",
            skill_path,
            "1.2.3",
            "linked",
            "linked",
            "Graphify CLI and Agent Skills integration are ready.",
        )
        with patch.object(service, "graphify_status", return_value=status), \
             patch.object(service, "reconcile_skills", return_value=ReconcileResult("preview", (), (), ())), \
             patch.object(service, "sync_graphify_if_cli_available") as refresh_graphify, \
             patch.object(
                 service,
                 "resync_workspaces",
                 return_value=WorkspaceReport(results=()),
             ) as resync:
            result = service.run_reconciliation_update(dry_run=True)

        self.assertIn(
            "Graphify: the generic Agent Skills integration would be refreshed after reconciliation.",
            result.message,
        )
        self.assertIn("surfaces:", result.message)
        refresh_graphify.assert_not_called()
        resync.assert_called_once_with(apply=False)

    def test_workspace_summary_counts_only_mutating_actions(self) -> None:
        from src.service import AgentbotService
        from src.workspace_render import RenderAction
        from src.workspace_service import WorkspaceReport, WorkspaceResult

        changed = WorkspaceResult(
            Path("/workspace/changed"),
            "preview",
            (
                RenderAction("AGENTS.md", "update", None, "refresh"),
                RenderAction("CLAUDE.md", "unchanged", None, "current"),
            ),
            "preview",
        )
        unchanged = WorkspaceResult(
            Path("/workspace/current"),
            "preview",
            (RenderAction("AGENTS.md", "unchanged", None, "current"),),
            "preview",
        )
        report = WorkspaceReport(
            results=(changed, unchanged),
            global_actions=(
                RenderAction("~/.codex/AGENTS.md", "create", None, "create"),
                RenderAction("~/.claude/AGENTS.md", "unchanged", None, "current"),
            ),
        )

        self.assertEqual(
            "surfaces: would refresh 1 workspace(s) and 1 global output(s)",
            AgentbotService._workspace_resync_summary(report, dry_run=True),
        )

    def test_workspace_summary_reports_zero_for_noop_actions(self) -> None:
        from src.service import AgentbotService
        from src.workspace_render import RenderAction
        from src.workspace_service import WorkspaceReport, WorkspaceResult

        report = WorkspaceReport(
            results=(
                WorkspaceResult(
                    Path("/workspace/current"),
                    "preview",
                    (RenderAction("AGENTS.md", "unchanged", None, "current"),),
                    "preview",
                ),
            ),
            global_actions=(
                RenderAction("~/.codex/AGENTS.md", "unchanged", None, "current"),
            ),
        )

        self.assertEqual(
            "surfaces: would refresh 0 workspace(s) and 0 global output(s)",
            AgentbotService._workspace_resync_summary(report, dry_run=True),
        )

    def test_reconciliation_dry_run_reports_cli_only_setup_without_mutation(self) -> None:
        from src.graphify import GraphifyStatus
        from src.service import AgentbotService
        from src.skill_reconcile import ReconcileResult
        from src.workspace_service import WorkspaceReport

        service = AgentbotService(self._paths())
        status = GraphifyStatus(
            "cli-only",
            self.fake_bin / "graphify",
            "graphify 1.2.3",
            self.home / ".agents/skills/graphify/SKILL.md",
            None,
            "missing",
            "missing",
            "Graphify CLI is installed; the Agent Skills integration is not set up.",
        )
        with patch.object(service, "graphify_status", return_value=status), patch.object(
            service, "reconcile_skills", return_value=ReconcileResult("preview", (), (), ())
        ), patch.object(
            service, "sync_graphify_if_cli_available"
        ) as sync, patch.object(
            service, "resync_workspaces", return_value=WorkspaceReport(results=())
        ):
            result = service.run_reconciliation_update(dry_run=True)

        self.assertIn(
            "Graphify: the generic Agent Skills integration would be set up after reconciliation.",
            result.message,
        )
        sync.assert_not_called()

    def test_reconciliation_broken_graphify_setup_fails_truthfully(self) -> None:
        from src.graphify import GraphifyStatus
        from src.service import AgentbotService
        from src.skill_reconcile import ReconcileResult
        from src.workspace_service import WorkspaceReport

        service = AgentbotService(self._paths())
        broken = GraphifyStatus(
            "broken",
            self.fake_bin / "graphify",
            "graphify 1.2.3",
            self.home / ".agents/skills/graphify/SKILL.md",
            None,
            "missing",
            "missing",
            "Graphify skill setup failed: exit 23",
        )
        with patch.object(
            service, "update_skills", return_value=SimpleNamespace(stdout="", stderr="")
        ), patch.object(
            service, "reconcile_skills", return_value=ReconcileResult("applied", (), (), ())
        ), patch.object(
            service, "sync_graphify_if_cli_available", return_value=broken
        ), patch.object(
            service, "resync_workspaces", return_value=WorkspaceReport(results=())
        ):
            result = service.run_reconciliation_update()

        self.assertEqual("failed", result.status)
        self.assertIn("Graphify: Graphify skill setup failed: exit 23", result.message)


if __name__ == "__main__":
    unittest.main()
