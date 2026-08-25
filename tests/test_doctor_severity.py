import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


class DoctorSeverityTests(unittest.TestCase):
    def test_installed_boost_with_unsafe_config_is_an_error(self) -> None:
        from src.boost import BoostStatus
        from src.diagnostics import Diagnostics
        from src.paths import AgentbotPaths

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "global").mkdir()
            (root / "global/AGENTS.md").write_text("# baseline\n", encoding="utf-8")
            paths = AgentbotPaths(root, root / "codex", root / "claude", root / "cursor")
            status = BoostStatus(
                "unsafe-config",
                root / "boost",
                "boost v0.12.6",
                root / ".boost/config.toml",
                False,
                False,
                "ready",
                "ready",
                "absent",
                "Boost privacy or update pinning is not safely configured.",
            )
            with patch("src.diagnostics.BoostIntegration.status", return_value=status):
                issues = Diagnostics(paths).doctor_issues()

            self.assertTrue(
                any(issue.level == "error" and issue.scope == "boost" for issue in issues)
            )

    def test_missing_boost_does_not_create_a_doctor_issue(self) -> None:
        from src.diagnostics import Diagnostics
        from src.paths import AgentbotPaths

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "global").mkdir()
            (root / "global/AGENTS.md").write_text("# baseline\n", encoding="utf-8")
            paths = AgentbotPaths(root, root / "codex", root / "claude", root / "cursor")
            issues = Diagnostics(paths).doctor_issues()
            self.assertFalse(any(issue.scope == "boost" for issue in issues))

    def test_unsafe_saved_token_is_actionable_warning_without_value_leak(self) -> None:
        from src.diagnostics import Diagnostics
        from src.paths import AgentbotPaths

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "global").mkdir()
            (root / "global" / "AGENTS.md").write_text("# baseline\n", encoding="utf-8")
            config = root / "config" / "agentbot"
            config.mkdir(parents=True)
            token_file = config / "github.env"
            token_file.write_text("GITHUB_TOKEN=short\n", encoding="utf-8")
            token_file.chmod(0o600)
            paths = AgentbotPaths(
                root,
                root / "codex",
                root / "claude",
                root / "cursor",
                config,
                agents_home=root / ".agents",
            )
            issues = Diagnostics(paths).doctor_issues()
            self.assertTrue(
                any(issue.level == "warning" and issue.scope == "token" for issue in issues)
            )
            self.assertFalse(any("short" in issue.message for issue in issues))

    def test_warning_only_doctor_is_success(self) -> None:
        from src.models import DoctorIssue
        from src.ui import print_doctor_summary

        with redirect_stdout(io.StringIO()):
            rc = print_doctor_summary(
                [DoctorIssue(level="warning", scope="skills", message="manual skill")]
            )
        self.assertEqual(0, rc)

    def test_errors_fail_even_with_warnings(self) -> None:
        from src.models import DoctorIssue
        from src.ui import print_doctor_summary

        with redirect_stdout(io.StringIO()):
            rc = print_doctor_summary(
                [
                    DoctorIssue(level="warning", scope="skills", message="manual skill"),
                    DoctorIssue(level="error", scope="global", message="missing baseline"),
                ]
            )
        self.assertEqual(1, rc)

    def test_official_graphify_skill_uses_graphify_scope_instead_of_manual_warning(self) -> None:
        from src.diagnostics import Diagnostics
        from src.paths import AgentbotPaths

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            home = root / "home"
            (root / "global").mkdir()
            (root / "global" / "AGENTS.md").write_text("# baseline\n", encoding="utf-8")
            graphify = home / ".agents" / "skills" / "graphify"
            graphify.mkdir(parents=True)
            (graphify / "SKILL.md").write_text("# graphify\n", encoding="utf-8")
            (graphify / ".graphify_version").write_text("1.2.3\n", encoding="utf-8")
            paths = AgentbotPaths(
                root,
                root / "codex",
                root / "claude",
                root / "cursor",
                agents_home=home / ".agents",
            )

            with patch.dict(os.environ, {"HOME": str(home)}, clear=False):
                issues = Diagnostics(paths).doctor_issues()

            self.assertTrue(any(issue.scope == "graphify" for issue in issues))
            self.assertFalse(any("Manual skill 'graphify'" in issue.message for issue in issues))

    def test_unstamped_graphify_directory_keeps_manual_skill_warning(self) -> None:
        from src.diagnostics import Diagnostics
        from src.paths import AgentbotPaths

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            home = root / "home"
            (root / "global").mkdir()
            (root / "global" / "AGENTS.md").write_text("# baseline\n", encoding="utf-8")
            manual = home / ".agents" / "skills" / "graphify"
            manual.mkdir(parents=True)
            (manual / "SKILL.md").write_text("# user skill\n", encoding="utf-8")
            paths = AgentbotPaths(
                root,
                root / "codex",
                root / "claude",
                root / "cursor",
                agents_home=home / ".agents",
            )

            with patch.dict(os.environ, {"HOME": str(home)}, clear=False):
                issues = Diagnostics(paths).doctor_issues()

            manual_messages = [
                issue.message for issue in issues if "Manual skill 'graphify'" in issue.message
            ]
            self.assertTrue(manual_messages)
            self.assertTrue(
                all("outside managed sources" in message for message in manual_messages)
            )

    def test_broken_official_graphify_state_is_an_error(self) -> None:
        from src.diagnostics import Diagnostics
        from src.graphify import GraphifyStatus
        from src.paths import AgentbotPaths

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            home = root / "home"
            (root / "global").mkdir()
            (root / "global" / "AGENTS.md").write_text("# baseline\n", encoding="utf-8")
            paths = AgentbotPaths(
                root,
                root / "codex",
                root / "claude",
                root / "cursor",
                agents_home=home / ".agents",
            )
            service = Diagnostics(paths)
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
            with (
                patch.dict(os.environ, {"HOME": str(home)}, clear=False),
                patch.object(service, "graphify_status", return_value=status),
            ):
                issues = service.doctor_issues()

            self.assertTrue(
                any(issue.level == "error" and issue.scope == "graphify" for issue in issues)
            )

    def test_cursor_lock_older_than_the_global_lock_is_a_warning(self) -> None:
        import os
        import time

        from src.diagnostics import Diagnostics
        from src.paths import AgentbotPaths

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            home = root / "home"
            (root / "global").mkdir()
            (root / "global" / "AGENTS.md").write_text("# baseline\n", encoding="utf-8")
            agents = home / ".agents"
            agents.mkdir(parents=True)
            cursor_lock = agents / "cursor-skills-lock.json"
            global_lock = agents / ".skill-lock.json"
            cursor_lock.write_text("{}\n", encoding="utf-8")
            global_lock.write_text("{}\n", encoding="utf-8")

            paths = AgentbotPaths(
                root,
                root / "codex",
                root / "claude",
                root / "cursor",
                agents_home=agents,
            )

            # cursor behind global -> warning naming the fix
            old = time.time() - 3600
            os.utime(cursor_lock, (old, old))
            issues = Diagnostics(paths).doctor_issues()
            cursor_issues = [issue for issue in issues if issue.scope == "skills-cursor"]
            self.assertEqual(1, len(cursor_issues))
            self.assertEqual("warning", cursor_issues[0].level)
            self.assertIn("skills install", cursor_issues[0].message)

            # caught up -> silent
            now = time.time()
            os.utime(cursor_lock, (now, now))
            os.utime(global_lock, (now - 10, now - 10))
            issues = Diagnostics(paths).doctor_issues()
            self.assertEqual([], [i for i in issues if i.scope == "skills-cursor"])

    def test_no_cursor_lock_means_no_cursor_warning(self) -> None:
        from src.diagnostics import Diagnostics
        from src.paths import AgentbotPaths

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            home = root / "home"
            (root / "global").mkdir()
            (root / "global" / "AGENTS.md").write_text("# baseline\n", encoding="utf-8")
            agents = home / ".agents"
            agents.mkdir(parents=True)
            (agents / ".skill-lock.json").write_text("{}\n", encoding="utf-8")
            paths = AgentbotPaths(
                root, root / "codex", root / "claude", root / "cursor", agents_home=agents
            )
            issues = Diagnostics(paths).doctor_issues()
            self.assertEqual([], [i for i in issues if i.scope == "skills-cursor"])


if __name__ == "__main__":
    unittest.main()
