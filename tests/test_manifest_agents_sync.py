import re
import unittest
from pathlib import Path


class ManifestAgentsSyncTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[1]
        cls.manifest_path = cls.repo_root / "skills.sources.yaml"
        cls.agents_paths = (cls.repo_root / "base" / "AGENTS.md", cls.repo_root / "AGENTS.md")

    def _enabled_manifest_skills(self) -> set[str]:
        from src.skills_sources import load_skills_sources

        config = load_skills_sources(self.manifest_path)
        skills: set[str] = set()
        for source in config.active_sources():
            # `skills: all` expands to the Skills CLI wildcard. Its evolving
            # upstream inventory must not require a hand-maintained table row.
            skills.update(skill for skill in source.skills if skill != "*")
        return skills

    def _advertised_skills(self, path: Path) -> set[str]:
        content = path.read_text(encoding="utf-8")
        table_lines = "\n".join(line for line in content.splitlines() if "|" in line)
        return set(re.findall(r"`([a-z0-9][a-z0-9-]*)`", table_lines))

    def test_enabled_manifest_skills_appear_in_base_agents_tables(self) -> None:
        manifest_skills = self._enabled_manifest_skills()
        self.assertGreater(len(manifest_skills), 0, "expected enabled skills in manifest")
        for path in self.agents_paths:
            advertised = self._advertised_skills(path)
            missing = sorted(skill for skill in manifest_skills if skill not in advertised)
            self.assertEqual([], missing, f"{path} is missing enabled manifest skills: {', '.join(missing)}")

    def test_disabled_manifest_skills_are_not_advertised(self) -> None:
        from src.skills_sources import load_skills_sources

        config = load_skills_sources(self.manifest_path)
        disabled_skills: set[str] = set()
        for source in config.sources:
            if not source.enabled and source.skills:
                disabled_skills.update(source.skills)

        for path in self.agents_paths:
            advertised = self._advertised_skills(path)
            leaked = sorted(skill for skill in disabled_skills if skill in advertised)
            self.assertEqual([], leaked, f"{path} advertises disabled manifest skills: {', '.join(leaked)}")


if __name__ == "__main__":
    unittest.main()
