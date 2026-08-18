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
            "Discover available tools, skills, agents, permissions, and sandboxing",
            content,
        )
        # Agent Skills are a portable format; the harness-specific parts are not.
        self.assertIn("Agent Skills may be portable", content)
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

    def test_canonical_policies_keep_the_tool_gate_generic(self) -> None:
        # Graphify usage guidance belongs to its skill. The baseline keeps only
        # the generic gate a skill description cannot supply: do not install
        # tooling or build/purge generated artifacts unasked.
        content = self.global_agents.read_text(encoding="utf-8")
        for phrase in ("install or uninstall software", "build, purge, or commit"):
            self.assertIn(phrase, content, msg=f"{phrase!r} missing from {self.global_agents}")
        for path in (self.global_agents, *self.agents_paths):
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
