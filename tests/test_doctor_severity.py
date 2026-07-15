import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


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


if __name__ == "__main__":
    unittest.main()
