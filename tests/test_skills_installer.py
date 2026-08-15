import io
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
        from src.paths import AgentbotPaths

        return AgentbotPaths(
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

    def test_build_add_argv_enables_full_depth_skill_discovery(self) -> None:
        from src.skills_installer import build_add_argv
        from src.skills_sources import SkillSourceEntry

        source = SkillSourceEntry(
            id="deslop",
            repo="brycewang-stanford/Auto-Empirical-Research-Skills",
            skills=["deslop"],
        )

        command = build_add_argv(source, agents=["codex"])

        self.assertIn("--full-depth", command)

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

        paths = self._paths()
        global_lock = self.root / "home" / ".agents" / ".skill-lock.json"
        with patch.object(
            type(paths),
            "global_skill_lock",
            new_callable=lambda: property(lambda _self: global_lock),
        ):
            results = install_skills(paths)

        self.assertEqual(1, mock_run.call_count)
        command = mock_run.call_args.args[0]
        self.assertEqual("npx", command[0])
        self.assertEqual("--yes", command[1])
        self.assertEqual("skills", command[2])
        self.assertEqual("add", command[3])
        self.assertEqual("superpowers", Path(command[4]).name)
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
        lock_file = self.root / "home" / ".agents" / ".skill-lock.json"

        result = install_source(source, agents=["codex"], global_lock_file=lock_file)

        self.assertIsInstance(result, InstallResult)
        self.assertEqual(2, mock_run.call_count)
        clone_command = mock_run.call_args_list[0].args[0]
        install_command = mock_run.call_args_list[1].args[0]
        self.assertEqual(
            ["git", "clone", "--depth=1", "https://github.com/obra/superpowers.git"],
            clone_command[:4],
        )
        self.assertEqual("npx", install_command[0])
        self.assertNotEqual("obra/superpowers", install_command[4])

    @patch("src.skills_installer.run_install_command")
    def test_install_source_records_remote_provenance_after_local_checkout(self, mock_install) -> None:
        from src.skills_installer import install_source
        from src.skills_sources import SkillSourceEntry

        source = SkillSourceEntry(
            id="superpowers",
            repo="obra/superpowers",
            skills=["brainstorming"],
        )
        mock_install.return_value = self._success_result("superpowers", ["npx", "skills", "add", "local"])
        lock_file = self.root / "home" / ".agents" / ".skill-lock.json"
        installed_skill = lock_file.parent / "skills" / "brainstorming"
        installed_skill.mkdir(parents=True)
        (installed_skill / "SKILL.md").write_text("# brainstorming\n", encoding="utf-8")

        def clone_with_skill(_repo: str, destination: Path) -> None:
            skill_dir = destination / "skills" / "brainstorming"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("---\nname: brainstorming\n---\n", encoding="utf-8")

        with patch("src.skills_installer._clone_github_source", side_effect=clone_with_skill):
            install_source(source, agents=["codex"], global_lock_file=lock_file)

        lock = json.loads(lock_file.read_text(encoding="utf-8"))
        self.assertEqual("obra/superpowers", lock["skills"]["brainstorming"]["source"])
        self.assertEqual("github", lock["skills"]["brainstorming"]["sourceType"])

    @patch("src.skills_installer.run_install_command")
    def test_install_source_wildcard_does_not_lock_checkout_test_fixtures(self, mock_install) -> None:
        from src.skills_installer import install_source
        from src.skills_sources import SkillSourceEntry

        source = SkillSourceEntry(
            id="wildcard-source",
            repo="owner/skills",
            skills=["*"],
        )
        mock_install.return_value = self._success_result("wildcard-source", ["npx", "skills", "add", "local"])
        lock_file = self.root / "home" / ".agents" / ".skill-lock.json"
        lock_file.parent.mkdir(parents=True)
        lock_file.write_text(
            json.dumps({"version": 3, "skills": {"stale": {"source": "owner/skills"}}}),
            encoding="utf-8",
        )
        installed_skill = lock_file.parent / "skills" / "real-skill"
        installed_skill.mkdir(parents=True)
        (installed_skill / "SKILL.md").write_text("# real skill\n", encoding="utf-8")

        def clone_with_skill_and_fixture(_repo: str, destination: Path) -> None:
            real_skill = destination / "skills" / "real-skill"
            real_skill.mkdir(parents=True)
            (real_skill / "SKILL.md").write_text("---\nname: real-skill\n---\n", encoding="utf-8")
            fixture_skill = destination / "tests" / "fixtures" / "skills" / "alpha"
            fixture_skill.mkdir(parents=True)
            (fixture_skill / "SKILL.md").write_text("---\nname: alpha\n---\n", encoding="utf-8")

        with patch("src.skills_installer._clone_github_source", side_effect=clone_with_skill_and_fixture):
            install_source(source, agents=["codex"], global_lock_file=lock_file)

        lock = json.loads(lock_file.read_text(encoding="utf-8"))
        self.assertIn("real-skill", lock["skills"])
        self.assertNotIn("alpha", lock["skills"])
        self.assertNotIn("stale", lock["skills"])

    @patch("src.skills_installer.run_install_command")
    def test_update_skills_runs_npx_update(self, mock_run) -> None:
        from src.skills_installer import build_update_argv, update_skills

        expected_argv = build_update_argv()
        mock_run.return_value = self._success_result("update", expected_argv)

        result = update_skills(self._paths())

        self.assertEqual(1, mock_run.call_count)
        command = mock_run.call_args.args[0]
        self.assertEqual(["npx", "--yes", "skills", "update", "-g", "-y"], command)
        self.assertEqual("update", result.source_id)

    def test_parse_update_output_reports_updated_and_deleted_skills(self) -> None:
        from src.skills_installer import parse_update_output

        output = (
            "\x1b[38;5;145mChecking skills from source: owner/repo\x1b[0m\n"
            "\x1b[38;5;145mWarning:\x1b[0m The following skills from owner/repo appear to have been deleted upstream:\n"
            "  \x1b[38;5;145m•\x1b[0m removed-skill\n"
            "  \x1b[38;5;145m•\x1b[0m another-removed-skill\n"
            "  \x1b[38;5;145m✓\x1b[0m Updated changed-skill\n"
            "\x1b[38;5;145m✓ Updated 1 skill(s)\x1b[0m\n"
        )

        report = parse_update_output(output)

        self.assertEqual(("changed-skill",), report.updated_skills)
        self.assertEqual(
            (("owner/repo", ("another-removed-skill", "removed-skill")),),
            report.deleted_by_source,
        )

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

    @patch("src.skills_installer.subprocess.Popen")
    def test_tui_install_command_streams_child_output(self, mock_popen) -> None:
        from src.skills_installer import run_install_command

        process = MagicMock(returncode=0)
        process.stdout = iter(("checking source\n", "installed skills\n"))
        process.wait.return_value = 0
        mock_popen.return_value = process
        output = io.StringIO()

        with patch.dict(os.environ, {"AGENTBOT_TUI": "1"}, clear=False), patch(
            "sys.stdout", output
        ):
            result = run_install_command(["npx", "skills", "add", "owner/repo"], source_id="repo")

        mock_popen.assert_called_once()
        self.assertEqual(0, result.returncode)
        self.assertIn("checking source", output.getvalue())
        self.assertIn("installed skills", output.getvalue())
        self.assertIn("installed skills", result.stdout)

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
        with patch.dict(os.environ, {"AGENTBOT_NPX_TIMEOUT_SECONDS": "1200"}), patch(
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
