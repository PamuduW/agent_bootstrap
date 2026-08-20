import unittest
from unittest import mock

from tests.support import isolated_agentbot_paths


class DiagnosticsTests(unittest.TestCase):
    def test_collect_reuses_one_issue_collection_for_summary_and_doctor(self) -> None:
        from src.diagnostics import Diagnostics
        from src.models import DoctorIssue
        with isolated_agentbot_paths() as (root, paths):
            diagnostics = Diagnostics(paths)
            general = (DoctorIssue("warning", "token", "unsafe"),)
            skills = (DoctorIssue("error", "skills", "broken"),)
            statusline = mock.Mock(status_label="ready")

            with mock.patch.object(
                diagnostics, "doctor_issues", return_value=list(general)
            ) as doctor, mock.patch.object(
                diagnostics, "skills_doctor_issues", return_value=list(skills)
            ) as skills_doctor, mock.patch.object(
                diagnostics, "list_skills", return_value=["alpha", "beta"]
            ) as list_skills, mock.patch(
                "src.diagnostics.managed_skill_names", return_value={"alpha"}
            ), mock.patch.object(
                diagnostics, "_manifest_declared_skill_names", return_value=set()
            ), mock.patch.object(
                diagnostics, "_unmanaged_skill_dirs", return_value=(root / "manual",)
            ), mock.patch(
                "src.diagnostics.inspect_claude_statusline", return_value=statusline
            ):
                snapshot = diagnostics.collect()

            self.assertEqual(("alpha", "beta"), snapshot.installed_skills)
            self.assertEqual(general + skills, snapshot.issues)
            self.assertEqual(1, snapshot.managed_skill_count)
            self.assertEqual(1, snapshot.manual_skill_count)
            self.assertEqual("ready", snapshot.claude_statusline_state)
            doctor.assert_called_once_with()
            skills_doctor.assert_called_once_with()
            list_skills.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
