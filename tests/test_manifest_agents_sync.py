import unittest
from pathlib import Path


class ManifestAgentsSyncTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[1]
        cls.agents_paths = (cls.repo_root / "base" / "AGENTS.md", cls.repo_root / "AGENTS.md")

    def test_templates_require_runtime_skill_discovery(self) -> None:
        for path in self.agents_paths:
            content = path.read_text(encoding="utf-8")
            self.assertIn(
                "Discover available compatible skills through the active harness before\n"
                "  selecting capabilities.",
                content,
            )
            self.assertIn(
                "Follow the active harness's skill discovery and invocation mechanism.",
                content,
            )
            self.assertNotIn("Managed identifiers", content)

    def test_root_agents_uses_the_canonical_base_baseline(self) -> None:
        from src.workspace_render import split_base_template

        base_baseline, _ = split_base_template(
            (self.repo_root / "base" / "AGENTS.md").read_text(encoding="utf-8")
        )
        root_baseline, _ = split_base_template(
            (self.repo_root / "AGENTS.md").read_text(encoding="utf-8")
        )
        self.assertEqual(base_baseline, root_baseline)


if __name__ == "__main__":
    unittest.main()
