import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


class SlimBootstrapEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

        (self.root / "global").mkdir()
        (self.root / "global" / "AGENTS.md").write_text(
            "# Global Baseline\n\nShared global instructions.\n",
            encoding="utf-8",
        )
        (self.root / "skills.sources.yaml").write_text(
            "version: 1\nagents: [cursor]\nscope: global\nsources: []\n",
            encoding="utf-8",
        )
        (self.root / "skills-lock.json").write_text(
            json.dumps({"skills": {"alpha-skill": {}, "beta-skill": {}}}, indent=2),
            encoding="utf-8",
        )

        agents_home = self.root / "home" / ".agents" / "skills"
        for name in ("alpha-skill", "beta-skill"):
            skill_dir = agents_home / name
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(f"# {name}\n", encoding="utf-8")

        self.codex_home = self.root / "home" / ".codex"
        self.claude_home = self.root / "home" / ".claude"
        self.agents_home = agents_home

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _paths(self):
        from src.paths import BootstrapPaths

        return BootstrapPaths(
            root=self.root,
            codex_home=self.codex_home,
            claude_home=self.claude_home,
            cursor_home=self.root / "home" / ".cursor",
        )

    def test_render_global_outputs_syncs_codex_skill_links(self) -> None:
        from src.render import render_global_outputs

        paths = self._paths()
        with mock.patch.object(
            type(paths),
            "agents_skills_home",
            new_callable=lambda: property(lambda self: self.root / "home" / ".agents" / "skills"),
        ), mock.patch.object(
            type(paths),
            "global_skill_lock",
            new_callable=lambda: property(lambda self: self.root / "home" / ".agents" / ".skill-lock.json"),
        ):
            render_global_outputs(paths)

        codex_agents = paths.codex_home / "AGENTS.md"
        self.assertTrue(codex_agents.exists())
        self.assertIn("Global Baseline", codex_agents.read_text(encoding="utf-8"))

        codex_skills = paths.codex_home / "skills"
        self.assertTrue((codex_skills / "alpha-skill").is_symlink())
        self.assertTrue((codex_skills / "beta-skill").is_symlink())

    def test_render_preserves_unmanaged_codex_skill_links(self) -> None:
        from src.render import render_global_outputs

        paths = self._paths()
        codex_skills = paths.codex_home / "skills"
        codex_skills.mkdir(parents=True)
        manual_source = self.root / "manual-skill"
        manual_source.mkdir()
        (manual_source / "SKILL.md").write_text("# manual\n", encoding="utf-8")
        (codex_skills / "manual-skill").symlink_to(manual_source)

        with mock.patch.object(
            type(paths),
            "agents_skills_home",
            new_callable=lambda: property(lambda self: self.root / "home" / ".agents" / "skills"),
        ), mock.patch.object(
            type(paths),
            "global_skill_lock",
            new_callable=lambda: property(lambda self: self.root / "home" / ".agents" / ".skill-lock.json"),
        ):
            render_global_outputs(paths)

        self.assertTrue((codex_skills / "manual-skill").is_symlink())
        self.assertEqual(manual_source.resolve(), (codex_skills / "manual-skill").resolve())

    def test_render_does_not_sync_manual_skills_when_global_lock_is_malformed(self) -> None:
        from src.render import render_global_outputs

        paths = self._paths()
        (self.root / "skills-lock.json").write_text('{"sources": []}', encoding="utf-8")
        global_lock = self.root / "home" / ".agents" / ".skill-lock.json"
        global_lock.parent.mkdir(parents=True, exist_ok=True)
        global_lock.write_text("not json", encoding="utf-8")
        manual = self.agents_home / "manual-skill"
        manual.mkdir()
        (manual / "SKILL.md").write_text("# manual\n", encoding="utf-8")

        with mock.patch.object(
            type(paths),
            "agents_skills_home",
            new_callable=lambda: property(lambda self: self.root / "home" / ".agents" / "skills"),
        ), mock.patch.object(
            type(paths),
            "global_skill_lock",
            new_callable=lambda: property(lambda self: self.root / "home" / ".agents" / ".skill-lock.json"),
        ):
            render_global_outputs(paths)

        self.assertTrue((paths.codex_home / "AGENTS.md").is_file())
        self.assertFalse((paths.codex_home / "skills" / "manual-skill").exists())

    def test_doctor_reports_missing_managed_link_and_unlinked_manual_skill(self) -> None:
        from src.service import BootstrapService

        paths = self._paths()
        manual = self.agents_home / "manual-skill"
        manual.mkdir()
        (manual / "SKILL.md").write_text("# manual\n", encoding="utf-8")
        service = BootstrapService(paths)

        with mock.patch.object(
            type(paths),
            "agents_skills_home",
            new_callable=lambda: property(lambda self: self.root / "home" / ".agents" / "skills"),
        ), mock.patch.object(
            type(paths),
            "global_skill_lock",
            new_callable=lambda: property(lambda self: self.root / "home" / ".agents" / ".skill-lock.json"),
        ):
            messages = [issue.message for issue in service.doctor_issues()]

        self.assertTrue(any("alpha-skill" in message and "missing" in message for message in messages))
        self.assertTrue(any("manual-skill" in message and "manual" in message for message in messages))

    def test_slim_doctor_reports_missing_global_agents(self) -> None:
        from src.service import BootstrapService

        paths = self._paths()
        (paths.global_agents).unlink()
        service = BootstrapService(paths)

        messages = [issue.message for issue in service.doctor_issues()]
        self.assertTrue(any("Missing global baseline" in message for message in messages))

    def test_slim_status_summary_counts_installed_skills(self) -> None:
        from src.service import BootstrapService

        paths = self._paths()
        service = BootstrapService(paths)

        with mock.patch.object(service, "list_skills", return_value=["alpha-skill", "beta-skill"]):
            summary = service.status_summary()

        self.assertEqual(2, summary["installed_skills"])
        self.assertTrue(summary["global_agents_exists"])
        self.assertTrue(summary["skills_sources_exists"])
        self.assertIn("enabled_sources", summary)
        self.assertIn("global_lock_skills", summary)
        self.assertIn("doctor_issue_count", summary)


if __name__ == "__main__":
    unittest.main()
