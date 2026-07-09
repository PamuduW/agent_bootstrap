import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


class SkillsInstallerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self._write_sources()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _paths(self):
        from src.agent_bootstrap.paths import BootstrapPaths

        return BootstrapPaths(
            root=self.root,
            codex_home=self.root / "home" / ".codex",
            claude_home=self.root / "home" / ".claude",
            cursor_home=self.root / "home" / ".cursor",
        )

    def _write_sources(self) -> None:
        (self.root / "skills.sources.yaml").write_text(
            """\
version: 1
agents:
  - cursor
  - codex
  - claude-code
  - github-copilot
scope: global
sources:
  - id: superpowers
    repo: obra/superpowers
    skills:
      - brainstorming
  - id: disabled-pack
    repo: owner/disabled
    skills:
      - ignored
    enabled: false
""",
            encoding="utf-8",
        )

    def _success_result(self, source_id: str, command: list[str]):
        from src.agent_bootstrap.skills_installer import InstallResult

        return InstallResult(
            source_id=source_id,
            command=command,
            returncode=0,
            stdout="",
            stderr="",
        )

    @patch("src.agent_bootstrap.skills_installer.run_install_command")
    def test_install_skills_runs_npx_for_active_sources(self, mock_run) -> None:
        from src.agent_bootstrap.skills_installer import build_add_argv, install_skills
        from src.agent_bootstrap.skills_sources import SkillSourceEntry

        source = SkillSourceEntry(
            id="superpowers",
            repo="obra/superpowers",
            skills=["brainstorming"],
        )
        expected_argv = build_add_argv(
            source,
            agents=["cursor", "codex", "claude-code", "github-copilot"],
        )
        mock_run.return_value = self._success_result("superpowers", expected_argv)

        results = install_skills(self._paths())

        self.assertEqual(1, mock_run.call_count)
        command = mock_run.call_args.args[0]
        self.assertEqual("npx", command[0])
        self.assertEqual("skills", command[1])
        self.assertEqual("add", command[2])
        self.assertEqual("obra/superpowers", command[3])
        self.assertIn("--skill", command)
        self.assertIn("brainstorming", command)
        self.assertIn("-a", command)
        self.assertIn("claude-code", command)
        self.assertEqual(1, len(results))
        self.assertEqual("superpowers", results[0].source_id)

    @patch("src.agent_bootstrap.skills_installer.run_install_command")
    def test_update_skills_runs_npx_update(self, mock_run) -> None:
        from src.agent_bootstrap.skills_installer import build_update_argv, update_skills

        expected_argv = build_update_argv()
        mock_run.return_value = self._success_result("update", expected_argv)

        result = update_skills(self._paths())

        self.assertEqual(1, mock_run.call_count)
        command = mock_run.call_args.args[0]
        self.assertEqual(["npx", "skills", "update", "-g", "-y"], command)
        self.assertEqual("update", result.source_id)

    def test_list_installed_skills_reads_agents_home(self) -> None:
        from src.agent_bootstrap.skills_installer import list_installed_skills

        paths = self._paths()
        agents_home = self.root / "agents-home"
        (agents_home / "alpha").mkdir(parents=True)
        (agents_home / "beta").mkdir(parents=True)

        with patch.object(
            type(paths),
            "agents_skills_home",
            new_callable=lambda: property(lambda self: agents_home),
        ):
            installed = list_installed_skills(paths)

        self.assertEqual(["alpha", "beta"], installed)

    @patch("src.agent_bootstrap.skills_installer.shutil.which", return_value="/usr/bin/npx")
    def test_doctor_skills_reports_missing_sources_file(self, _mock_which) -> None:
        from src.agent_bootstrap.skills_installer import doctor_skills

        paths = self._paths()
        (self.root / "skills.sources.yaml").unlink()

        issues = doctor_skills(paths)
        messages = [issue.message for issue in issues]

        self.assertTrue(any("Missing skills sources file" in message for message in messages))

    @patch("src.agent_bootstrap.skills_installer.shutil.which", return_value=None)
    def test_doctor_skills_reports_missing_npx(self, _mock_which) -> None:
        from src.agent_bootstrap.skills_installer import doctor_skills

        issues = doctor_skills(self._paths())
        messages = [issue.message for issue in issues]

        self.assertTrue(any("npx is not available" in message for message in messages))

    @patch("src.agent_bootstrap.skills_installer.shutil.which", return_value="/usr/bin/npx")
    def test_doctor_skills_warns_on_unreadable_lockfile(self, _mock_which) -> None:
        from src.agent_bootstrap.skills_installer import doctor_skills

        lock_file = self.root / "skills-lock.json"
        lock_file.write_text(json.dumps({"version": 1}), encoding="utf-8")
        lock_file.chmod(0o000)

        try:
            issues = doctor_skills(self._paths())
        finally:
            lock_file.chmod(0o644)

        messages = [issue.message for issue in issues]
        self.assertTrue(any("Unable to read skills lock file" in message for message in messages))

    def test_run_install_command_uses_subprocess(self) -> None:
        from src.agent_bootstrap.skills_installer import run_install_command

        completed = MagicMock(returncode=0, stdout="ok", stderr="")
        with patch("src.agent_bootstrap.skills_installer.subprocess.run", return_value=completed) as mock_run:
            result = run_install_command(["npx", "skills", "update"], source_id="update")

        mock_run.assert_called_once()
        self.assertEqual(0, result.returncode)
        self.assertEqual("ok", result.stdout)
        self.assertEqual("update", result.source_id)


if __name__ == "__main__":
    unittest.main()
