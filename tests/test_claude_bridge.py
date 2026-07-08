import tempfile
import unittest
from pathlib import Path


class ClaudeBridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.agents_home = self.root / "agents" / "skills"
        self.claude_home = self.root / "claude" / "skills"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _write_skill(self, name: str) -> Path:
        skill_dir = self.agents_home / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(f"# {name}\n", encoding="utf-8")
        return skill_dir

    def test_bridge_creates_symlinks_for_each_skill(self) -> None:
        from src.agent_bootstrap.claude_bridge import bridge_claude_skills

        self._write_skill("alpha")
        self._write_skill("beta")

        result = bridge_claude_skills(self.agents_home, self.claude_home)

        self.assertEqual(2, result.linked)
        self.assertEqual(0, result.skipped)
        alpha_target = self.claude_home / "alpha"
        beta_target = self.claude_home / "beta"
        self.assertTrue(alpha_target.is_symlink())
        self.assertTrue(beta_target.is_symlink())
        self.assertEqual(
            (self.agents_home / "alpha").resolve(),
            alpha_target.resolve(),
        )

    def test_bridge_is_idempotent_when_already_linked(self) -> None:
        from src.agent_bootstrap.claude_bridge import bridge_claude_skills

        source = self._write_skill("alpha")

        first = bridge_claude_skills(self.agents_home, self.claude_home)
        second = bridge_claude_skills(self.agents_home, self.claude_home)

        self.assertEqual(1, first.linked)
        self.assertEqual(0, first.skipped)
        self.assertEqual(0, second.linked)
        self.assertEqual(1, second.skipped)
        self.assertEqual("already_linked", second.actions[0].action)
        self.assertEqual(source.resolve(), (self.claude_home / "alpha").resolve())

    def test_bridge_skips_existing_non_symlink_target(self) -> None:
        from src.agent_bootstrap.claude_bridge import bridge_claude_skills

        self._write_skill("alpha")
        existing = self.claude_home / "alpha"
        existing.parent.mkdir(parents=True, exist_ok=True)
        existing.mkdir()

        result = bridge_claude_skills(self.agents_home, self.claude_home)

        self.assertEqual(0, result.linked)
        self.assertEqual(1, result.skipped)
        self.assertEqual("skip_existing", result.actions[0].action)
        self.assertTrue(existing.is_dir())
        self.assertFalse(existing.is_symlink())

    def test_bridge_skips_conflicting_symlink_target(self) -> None:
        from src.agent_bootstrap.claude_bridge import bridge_claude_skills

        self._write_skill("alpha")
        other_source = self.root / "other" / "alpha"
        other_source.mkdir(parents=True)
        (other_source / "SKILL.md").write_text("# other\n", encoding="utf-8")

        self.claude_home.mkdir(parents=True, exist_ok=True)
        (self.claude_home / "alpha").symlink_to(other_source)

        result = bridge_claude_skills(self.agents_home, self.claude_home)

        self.assertEqual(0, result.linked)
        self.assertEqual(1, result.skipped)
        self.assertEqual("skip_existing", result.actions[0].action)
        self.assertEqual(other_source.resolve(), (self.claude_home / "alpha").resolve())

    def test_bridge_dry_run_reports_without_writing(self) -> None:
        from src.agent_bootstrap.claude_bridge import bridge_claude_skills

        self._write_skill("alpha")

        result = bridge_claude_skills(self.agents_home, self.claude_home, dry_run=True)

        self.assertEqual(1, result.linked)
        self.assertFalse(self.claude_home.exists())
        self.assertEqual("linked", result.actions[0].action)

    def test_bridge_returns_empty_result_when_agents_home_missing(self) -> None:
        from src.agent_bootstrap.claude_bridge import bridge_claude_skills

        missing = self.root / "missing" / "skills"
        result = bridge_claude_skills(missing, self.claude_home)

        self.assertEqual([], result.actions)
        self.assertEqual(0, result.linked)
        self.assertEqual(0, result.skipped)


if __name__ == "__main__":
    unittest.main()
