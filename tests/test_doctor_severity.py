import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


class DoctorSeverityTests(unittest.TestCase):
    def test_unsafe_saved_token_is_actionable_warning_without_value_leak(self) -> None:
        from src.paths import AgentbotPaths
        from src.service import AgentbotService

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "global").mkdir()
            (root / "global" / "AGENTS.md").write_text("# baseline\n", encoding="utf-8")
            config = root / "config" / "agentbot"
            config.mkdir(parents=True)
            token_file = config / "github.env"
            token_file.write_text("GITHUB_TOKEN=short\n", encoding="utf-8")
            token_file.chmod(0o600)
            paths = AgentbotPaths(root, root / "codex", root / "claude", root / "cursor", config)
            issues = AgentbotService(paths).doctor_issues()
            self.assertTrue(any(issue.level == "warning" and issue.scope == "token" for issue in issues))
            self.assertFalse(any("short" in issue.message for issue in issues))

    def test_warning_only_doctor_is_success(self) -> None:
        from src.models import DoctorIssue
        from src.ui import print_doctor_summary

        with redirect_stdout(io.StringIO()):
            rc = print_doctor_summary([DoctorIssue(level="warning", scope="skills", message="manual skill")])
        self.assertEqual(0, rc)

    def test_errors_fail_even_with_warnings(self) -> None:
        from src.models import DoctorIssue
        from src.ui import print_doctor_summary

        with redirect_stdout(io.StringIO()):
            rc = print_doctor_summary([
                DoctorIssue(level="warning", scope="skills", message="manual skill"),
                DoctorIssue(level="error", scope="global", message="missing baseline"),
            ])
        self.assertEqual(1, rc)

    def test_official_graphify_skill_uses_graphify_scope_instead_of_manual_warning(self) -> None:
        from src.paths import AgentbotPaths
        from src.service import AgentbotService

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            home = root / "home"
            (root / "global").mkdir()
            (root / "global" / "AGENTS.md").write_text("# baseline\n", encoding="utf-8")
            graphify = home / ".agents" / "skills" / "graphify"
            graphify.mkdir(parents=True)
            (graphify / "SKILL.md").write_text("# graphify\n", encoding="utf-8")
            (graphify / ".graphify_version").write_text("1.2.3\n", encoding="utf-8")
            paths = AgentbotPaths(root, root / "codex", root / "claude", root / "cursor")

            with patch.dict(os.environ, {"HOME": str(home)}, clear=False):
                issues = AgentbotService(paths).doctor_issues()

            self.assertTrue(any(issue.scope == "graphify" for issue in issues))
            self.assertFalse(any("Manual skill 'graphify'" in issue.message for issue in issues))

    def test_unstamped_graphify_directory_keeps_manual_skill_warning(self) -> None:
        from src.paths import AgentbotPaths
        from src.service import AgentbotService

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            home = root / "home"
            (root / "global").mkdir()
            (root / "global" / "AGENTS.md").write_text("# baseline\n", encoding="utf-8")
            manual = home / ".agents" / "skills" / "graphify"
            manual.mkdir(parents=True)
            (manual / "SKILL.md").write_text("# user skill\n", encoding="utf-8")
            paths = AgentbotPaths(root, root / "codex", root / "claude", root / "cursor")

            with patch.dict(os.environ, {"HOME": str(home)}, clear=False):
                issues = AgentbotService(paths).doctor_issues()

            manual_messages = [issue.message for issue in issues if "Manual skill 'graphify'" in issue.message]
            self.assertTrue(manual_messages)
            self.assertTrue(all("outside managed sources" in message for message in manual_messages))

    def test_broken_official_graphify_state_is_an_error(self) -> None:
        from src.graphify import GraphifyStatus
        from src.paths import AgentbotPaths
        from src.service import AgentbotService

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            home = root / "home"
            (root / "global").mkdir()
            (root / "global" / "AGENTS.md").write_text("# baseline\n", encoding="utf-8")
            paths = AgentbotPaths(root, root / "codex", root / "claude", root / "cursor")
            service = AgentbotService(paths)
            graphify = home / ".agents/skills/graphify"
            graphify.mkdir(parents=True)
            (graphify / "SKILL.md").write_text("# graphify\n", encoding="utf-8")
            (graphify / ".graphify_version").write_text("1.2.3\n", encoding="utf-8")
            status = GraphifyStatus(
                "broken",
                None,
                None,
                graphify / "SKILL.md",
                None,
                "missing",
                "missing",
                "Graphify skill setup failed: subprocess failed",
            )
            with patch.dict(os.environ, {"HOME": str(home)}, clear=False), patch.object(
                service, "graphify_status", return_value=status
            ):
                issues = service.doctor_issues()

            self.assertTrue(any(issue.level == "error" and issue.scope == "graphify" for issue in issues))


if __name__ == "__main__":
    unittest.main()
