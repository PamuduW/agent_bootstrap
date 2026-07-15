import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock


class InstallLifecycleTests(unittest.TestCase):
    def test_bootstrap_orders_install_refresh_doctor_and_returns_warning_success(self) -> None:
        from src.models import DoctorIssue
        from src.paths import AgentbotPaths
        from src.service import AgentbotService

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "global").mkdir()
            (root / "global" / "AGENTS.md").write_text("# baseline\n", encoding="utf-8")
            paths = AgentbotPaths(root, root / "codex", root / "claude", root / "cursor")
            service = AgentbotService(paths)
            events: list[str] = []
            with mock.patch("src.service.run_skills_install", side_effect=lambda _paths: events.append("install") or []), \
                 mock.patch.object(service, "refresh_agent_outputs", side_effect=lambda: events.append("refresh") or (0, 0, 0)), \
                 mock.patch.object(service, "doctor_issues", side_effect=lambda: events.append("doctor") or []), \
                 mock.patch.object(service, "skills_doctor_issues", return_value=[DoctorIssue("warning", "skills", "manual")]):
                rc = service.run_bootstrap()
            self.assertEqual(0, rc)
            self.assertEqual(["install", "refresh", "doctor"], events)

    def test_bootstrap_header_uses_install_breadcrumb(self) -> None:
        from src.paths import AgentbotPaths
        from src.service import AgentbotService

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "global").mkdir()
            (root / "global" / "AGENTS.md").write_text("# baseline\n", encoding="utf-8")
            paths = AgentbotPaths(root, root / "codex", root / "claude", root / "cursor")
            service = AgentbotService(paths)
            output = io.StringIO()
            with mock.patch("src.service.run_skills_install", return_value=[]), \
                 mock.patch.object(service, "refresh_agent_outputs", return_value=(0, 0, 0)), \
                 mock.patch.object(service, "doctor_issues", return_value=[]), \
                 mock.patch.object(service, "skills_doctor_issues", return_value=[]), \
                 contextlib.redirect_stdout(output):
                service.run_bootstrap()
            self.assertIn("Agentbot › Install Agentbot", output.getvalue())


if __name__ == "__main__":
    unittest.main()
