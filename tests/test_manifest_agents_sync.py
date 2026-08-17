import unittest
from pathlib import Path


class ManifestAgentsSyncTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[1]
        cls.agents_paths = (cls.repo_root / "base" / "AGENTS.md", cls.repo_root / "AGENTS.md")
        cls.global_agents = cls.repo_root / "global" / "AGENTS.md"

    def test_global_baseline_requires_runtime_harness_discovery(self) -> None:
        # Harness and skill discovery is machine scope, so it lives in the global
        # baseline only. Repeating it in base/AGENTS.md would double-load it.
        content = self.global_agents.read_text(encoding="utf-8")
        self.assertIn(
            "Discover the active harness's tools, skills, agents, permissions, and sandbox",
            content,
        )
        self.assertIn(
            "A skill written for one harness is not portable to another.",
            content,
        )
        for path in self.agents_paths:
            self.assertNotIn("Managed identifiers", path.read_text(encoding="utf-8"))

    def test_repo_policy_does_not_restate_the_global_baseline(self) -> None:
        global_lines = {
            line.strip()
            for line in self.global_agents.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        for path in self.agents_paths:
            repo_lines = {
                line.strip()
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.lstrip().startswith("#")
            }
            overlap = global_lines & repo_lines
            self.assertEqual(set(), overlap, msg=f"{path} duplicates global baseline: {overlap}")

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
        # The gate lives in the global baseline only; Graphify is a machine-level
        # optional tool, not repository policy.
        content = self.global_agents.read_text(encoding="utf-8")
        for phrase in required:
            self.assertIn(phrase, content, msg=f"{phrase!r} missing from {self.global_agents}")
        for path in self.agents_paths:
            self.assertNotIn("graphify-out/graph.json", path.read_text(encoding="utf-8"))

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
