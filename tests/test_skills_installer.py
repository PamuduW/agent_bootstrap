import json
import os
import subprocess
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
        from src.paths import BootstrapPaths

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
        from src.skills_installer import InstallResult

        return InstallResult(
            source_id=source_id,
            command=command,
            returncode=0,
            stdout="",
            stderr="",
        )

    @patch("src.skills_installer._clone_github_source")
    @patch("src.skills_installer.run_install_command")
    def test_install_skills_runs_npx_for_active_sources(self, mock_run, mock_clone) -> None:
        from src.skills_installer import build_add_argv, install_skills
        from src.skills_sources import SkillSourceEntry

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
        self.assertEqual("superpowers", Path(command[3]).name)
        self.assertIn("--skill", command)
        self.assertIn("brainstorming", command)
        self.assertIn("-a", command)
        self.assertIn("claude-code", command)
        self.assertEqual(1, len(results))
        self.assertEqual("superpowers", results[0].source_id)
        mock_clone.assert_called_once()

    @patch("src.skills_installer.subprocess.run")
    def test_install_source_clones_github_sources_before_invoking_npx(self, mock_run) -> None:
        from src.skills_installer import InstallResult, install_source
        from src.skills_sources import SkillSourceEntry

        source = SkillSourceEntry(
            id="superpowers",
            repo="obra/superpowers",
            skills=["brainstorming"],
        )
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="", stderr=""),
            MagicMock(returncode=0, stdout="ok", stderr=""),
        ]

        result = install_source(source, agents=["codex"])

        self.assertIsInstance(result, InstallResult)
        self.assertEqual(2, mock_run.call_count)
        clone_command = mock_run.call_args_list[0].args[0]
        install_command = mock_run.call_args_list[1].args[0]
        self.assertEqual(
            ["git", "clone", "--depth=1", "https://github.com/obra/superpowers.git"],
            clone_command[:4],
        )
        self.assertEqual("npx", install_command[0])
        self.assertNotEqual("obra/superpowers", install_command[3])

    @patch("src.skills_installer.run_install_command")
    def test_update_skills_runs_npx_update(self, mock_run) -> None:
        from src.skills_installer import build_update_argv, update_skills

        expected_argv = build_update_argv()
        mock_run.return_value = self._success_result("update", expected_argv)

        result = update_skills(self._paths())

        self.assertEqual(1, mock_run.call_count)
        command = mock_run.call_args.args[0]
        self.assertEqual(["npx", "skills", "update", "-g", "-y"], command)
        self.assertEqual("update", result.source_id)

    def test_list_installed_skills_reads_agents_home(self) -> None:
        from src.skills_installer import list_installed_skills

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

    @patch("src.skills_installer.shutil.which", return_value="/usr/bin/npx")
    def test_doctor_skills_reports_missing_sources_file(self, _mock_which) -> None:
        from src.skills_installer import doctor_skills

        paths = self._paths()
        (self.root / "skills.sources.yaml").unlink()

        issues = doctor_skills(paths)
        messages = [issue.message for issue in issues]

        self.assertTrue(any("Missing skills sources file" in message for message in messages))

    @patch("src.skills_installer.shutil.which", return_value=None)
    def test_doctor_skills_reports_missing_npx(self, _mock_which) -> None:
        from src.skills_installer import doctor_skills

        issues = doctor_skills(self._paths())
        messages = [issue.message for issue in issues]

        self.assertTrue(any("npx is not available" in message for message in messages))

    @patch("src.skills_installer.shutil.which", return_value="/usr/bin/npx")
    def test_doctor_skills_warns_on_unreadable_lockfile(self, _mock_which) -> None:
        from src.skills_installer import doctor_skills

        lock_file = self.root / "skills-lock.json"
        lock_file.write_text(json.dumps({"version": 1}), encoding="utf-8")
        lock_file.chmod(0o000)

        try:
            issues = doctor_skills(self._paths())
        finally:
            lock_file.chmod(0o644)

        messages = [issue.message for issue in issues]
        self.assertTrue(any("Unable to read project skills lock file" in message for message in messages))

    def test_run_install_command_uses_subprocess(self) -> None:
        from src.skills_installer import run_install_command

        completed = MagicMock(returncode=0, stdout="ok", stderr="")
        with patch("src.skills_installer.subprocess.run", return_value=completed) as mock_run:
            result = run_install_command(["npx", "skills", "update"], source_id="update")

        mock_run.assert_called_once()
        self.assertEqual(0, result.returncode)
        self.assertEqual("ok", result.stdout)
        self.assertEqual("update", result.source_id)

    @patch("src.skills_installer.shutil.which", return_value="/usr/bin/npx")
    def test_doctor_reports_manifest_skills_missing_from_global_lock(self, _mock_which) -> None:
        from src.skills_installer import doctor_skills

        paths = self._paths()
        global_lock = self.root / "home" / ".agents" / ".skill-lock.json"
        global_lock.parent.mkdir(parents=True)
        global_lock.write_text(json.dumps({"skills": {}}), encoding="utf-8")

        with patch.object(
            type(paths),
            "global_skill_lock",
            new_callable=lambda: property(lambda self: self.root / "home" / ".agents" / ".skill-lock.json"),
        ):
            messages = [issue.message for issue in doctor_skills(paths)]

        self.assertTrue(any("brainstorming" in message and "absent" in message for message in messages))

    @patch("src.skills_installer.shutil.which", return_value="/usr/bin/npx")
    def test_doctor_ignores_global_lock_skills_not_declared_by_manifest(self, _mock_which) -> None:
        from src.skills_installer import doctor_skills

        paths = self._paths()
        global_lock = self.root / "home" / ".agents" / ".skill-lock.json"
        global_lock.parent.mkdir(parents=True)
        global_lock.write_text(json.dumps({"skills": {"brainstorming": {}, "personal": {}}}), encoding="utf-8")

        with patch.object(
            type(paths),
            "global_skill_lock",
            new_callable=lambda: property(lambda self: self.root / "home" / ".agents" / ".skill-lock.json"),
        ):
            messages = [issue.message for issue in doctor_skills(paths)]

        self.assertFalse(any("personal" in message and "not declared" in message for message in messages))

    @patch("src.skills_installer.shutil.which", return_value="/usr/bin/npx")
    def test_doctor_treats_lock_entries_from_an_all_source_as_managed(self, _mock_which) -> None:
        from src.skills_installer import doctor_skills

        (self.root / "skills.sources.yaml").write_text(
            """\
version: 1
agents:
  - codex
scope: global
sources:
  - id: all-source
    repo: owner/all-skills
    skills: all
""",
            encoding="utf-8",
        )
        paths = self._paths()
        global_lock = self.root / "home" / ".agents" / ".skill-lock.json"
        global_lock.parent.mkdir(parents=True)
        global_lock.write_text(
            json.dumps({"skills": {"upstream-skill": {"source": "owner/all-skills"}}}),
            encoding="utf-8",
        )

        with patch.object(
            type(paths),
            "global_skill_lock",
            new_callable=lambda: property(lambda self: self.root / "home" / ".agents" / ".skill-lock.json"),
        ):
            messages = [issue.message for issue in doctor_skills(paths)]

        self.assertFalse(any("'*'" in message for message in messages))
        self.assertFalse(any("upstream-skill" in message and "not declared" in message for message in messages))

    def test_run_install_command_uses_a_timeout(self) -> None:
        from src.skills_installer import run_install_command

        completed = MagicMock(returncode=0, stdout="ok", stderr="")
        with patch("src.skills_installer.subprocess.run", return_value=completed) as mock_run:
            run_install_command(["npx", "skills", "update"], source_id="update")

        self.assertIn("timeout", mock_run.call_args.kwargs)

    def test_run_install_command_allows_a_longer_timeout_for_fresh_machine_installs(self) -> None:
        from src.skills_installer import run_install_command

        completed = MagicMock(returncode=0, stdout="ok", stderr="")
        with patch.dict(os.environ, {"AGENT_BOOTSTRAP_NPX_TIMEOUT_SECONDS": "1200"}), patch(
            "src.skills_installer.subprocess.run", return_value=completed
        ) as mock_run:
            run_install_command(["npx", "skills", "add"], source_id="superpowers")

        self.assertEqual(1200, mock_run.call_args.kwargs["timeout"])

    def test_run_install_command_reports_timeouts_with_source_context(self) -> None:
        from src.skills_installer import SkillsInstallError, run_install_command

        with patch(
            "src.skills_installer.subprocess.run",
            side_effect=subprocess.TimeoutExpired(["npx", "skills"], 1),
        ):
            with self.assertRaisesRegex(SkillsInstallError, "superpowers.*timed out"):
                run_install_command(["npx", "skills", "add"], source_id="superpowers")


if __name__ == "__main__":
    unittest.main()
