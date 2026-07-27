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

    def test_canonical_policies_define_the_safe_graphify_gate(self) -> None:
        required = (
            "graphify-out/graph.json",
            "active harness exposes",
            "Fall back to `rg`",
            "Never install Graphify",
            "derived evidence",
        )
        for path in (
            self.repo_root / "base" / "AGENTS.md",
            self.repo_root / "global" / "AGENTS.md",
            self.repo_root / "AGENTS.md",
        ):
            content = path.read_text(encoding="utf-8")
            for phrase in required:
                self.assertIn(phrase, content, msg=f"{phrase!r} missing from {path}")

    def test_graphify_policy_is_not_added_to_unmarked_user_files(self) -> None:
        from src.workspace_render import build_workspace_render_plan

        plan = build_workspace_render_plan(
            "# AGENTS.md\n\n## Project\n\n# User policy\n",
            {"AGENTS.md": "# User-owned policy\n"},
            ("agents",),
        )
        self.assertNotIn("graphify-out/graph.json", plan.action_for("AGENTS.md").content or "")


if __name__ == "__main__":
    unittest.main()
