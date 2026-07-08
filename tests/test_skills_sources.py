import tempfile
import unittest
from pathlib import Path


class SkillsSourcesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _write_sources(self, content: str) -> Path:
        path = self.root / "skills.sources.yaml"
        path.write_text(content, encoding="utf-8")
        return path

    def test_load_skills_sources_parses_seed_file(self) -> None:
        from src.agent_bootstrap.skills_sources import load_skills_sources

        repo_root = Path(__file__).resolve().parents[1]
        config = load_skills_sources(repo_root / "skills.sources.yaml")

        self.assertEqual(1, config.version)
        self.assertEqual("global", config.scope)
        self.assertIn("cursor", config.agents)
        self.assertIn("claude-code", config.agents)
        self.assertGreaterEqual(len(config.sources), 1)

        superpowers = next(source for source in config.sources if source.id == "superpowers")
        self.assertEqual("obra/superpowers", superpowers.repo)
        self.assertIn("brainstorming", superpowers.skills)

        personal = next(source for source in config.sources if source.id == "personal-pack")
        self.assertFalse(personal.enabled)

    def test_active_sources_skips_disabled_empty_or_missing_repo(self) -> None:
        from src.agent_bootstrap.skills_sources import load_skills_sources

        path = self._write_sources(
            """\
version: 1
agents:
  - cursor
  - codex
scope: global
sources:
  - id: enabled
    repo: owner/repo
    skills:
      - alpha
  - id: disabled
    repo: owner/disabled
    skills:
      - beta
    enabled: false
  - id: empty-skills
    repo: owner/empty
    skills: []
  - id: missing-repo
    repo: null
    skills:
      - gamma
"""
        )
        config = load_skills_sources(path)
        active = config.active_sources()

        self.assertEqual(1, len(active))
        self.assertEqual("enabled", active[0].id)

    def test_load_skills_sources_raises_for_missing_file(self) -> None:
        from src.agent_bootstrap.skills_sources import SkillsSourcesError, load_skills_sources

        with self.assertRaises(SkillsSourcesError):
            load_skills_sources(self.root / "missing.yaml")

    def test_build_add_argv_includes_repo_skills_and_agents(self) -> None:
        from src.agent_bootstrap.skills_installer import build_add_argv
        from src.agent_bootstrap.skills_sources import SkillSourceEntry

        source = SkillSourceEntry(
            id="superpowers",
            repo="obra/superpowers",
            skills=["brainstorming", "writing-plans"],
        )
        argv = build_add_argv(
            source,
            agents=["cursor", "codex", "claude-code", "github-copilot"],
        )

        self.assertEqual(
            [
                "npx",
                "skills",
                "add",
                "obra/superpowers",
                "--skill",
                "brainstorming",
                "--skill",
                "writing-plans",
                "-a",
                "cursor",
                "-a",
                "codex",
                "-a",
                "claude-code",
                "-a",
                "github-copilot",
                "-g",
                "-y",
            ],
            argv,
        )


if __name__ == "__main__":
    unittest.main()
