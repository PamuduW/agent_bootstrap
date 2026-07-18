from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.workspace_render import (
    GENERATED_HEADER,
    MANAGED_BEGIN,
    MANAGED_END,
    apply_workspace_render_plan,
    build_workspace_render_plan,
)


class WorkspaceRenderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.base_agents = (
            "# AGENTS.md\n\n"
            "## Environment\n\n"
            "- Shared environment.\n\n"
            "## Project\n\n"
            "<!-- Fill in project policy. -->\n"
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_missing_files_plan_the_selected_default_outputs(self) -> None:
        plan = build_workspace_render_plan(
            self.base_agents,
            {},
            ("agents", "claude", "copilot", "cursor"),
        )

        self.assertEqual(
            (
                "AGENTS.md",
                "CLAUDE.md",
                ".github/copilot-instructions.md",
                ".cursor/rules/agentbot-policy.mdc",
            ),
            plan.paths(),
        )
        self.assertTrue(all(action.kind == "create" for action in plan.actions))
        self.assertEqual("managed", plan.policy_mode)

    def test_resync_replaces_only_the_managed_region(self) -> None:
        agents = (
            "custom heading\n"
            f"{MANAGED_BEGIN}\nold base\n{MANAGED_END}\n\n"
            "## Project\nKeep this project rule.\n"
        )
        newer_base = self.base_agents.replace("Shared environment.", "new shared base")

        plan = build_workspace_render_plan(newer_base, {"AGENTS.md": agents}, ("agents",))
        action = plan.actions[0]

        self.assertEqual("update", action.kind)
        self.assertIn("new shared base", action.content or "")
        self.assertIn("custom heading\n", action.content or "")
        self.assertIn("Keep this project rule.", action.content or "")
        self.assertNotIn("old base", action.content or "")

    def test_unmarked_custom_agents_file_is_preserved(self) -> None:
        plan = build_workspace_render_plan(
            self.base_agents,
            {"AGENTS.md": "# My policy\n"},
            ("claude",),
        )

        self.assertEqual("custom", plan.policy_mode)
        self.assertEqual("unchanged", plan.action_for("AGENTS.md").kind)
        self.assertEqual("create", plan.action_for("CLAUDE.md").kind)
        self.assertEqual("# My policy\n", plan.action_for("AGENTS.md").content)

    def test_every_custom_selection_still_plans_agents(self) -> None:
        plan = build_workspace_render_plan(self.base_agents, {}, ("copilot",))

        self.assertEqual(
            ("AGENTS.md", ".github/copilot-instructions.md"),
            plan.paths(),
        )

    def test_legacy_phase_one_agents_are_migrated(self) -> None:
        legacy = self.base_agents.replace(
            "<!-- Fill in project policy. -->",
            "Keep this legacy project policy.",
        )

        plan = build_workspace_render_plan(self.base_agents, {"AGENTS.md": legacy}, ("agents",))
        content = plan.action_for("AGENTS.md").content or ""

        self.assertEqual("managed", plan.policy_mode)
        self.assertEqual("update", plan.action_for("AGENTS.md").kind)
        self.assertIn(MANAGED_BEGIN, content)
        self.assertIn("Keep this legacy project policy.", content)

    def test_existing_unowned_compatibility_file_is_a_conflict(self) -> None:
        plan = build_workspace_render_plan(
            self.base_agents,
            {"CLAUDE.md": "# User-owned instructions\n"},
            ("claude",),
        )

        self.assertEqual("conflict", plan.action_for("CLAUDE.md").kind)
        self.assertIsNone(plan.action_for("CLAUDE.md").content)

    def test_legacy_claude_template_is_migrated_as_agentbot_owned(self) -> None:
        legacy = (
            "IMPORTANT: Read and follow all instructions in AGENTS.md before starting any task.\n\n"
            "@AGENTS.md\n"
        )

        plan = build_workspace_render_plan(self.base_agents, {"CLAUDE.md": legacy}, ("claude",))

        self.assertEqual("update", plan.action_for("CLAUDE.md").kind)
        self.assertIn(GENERATED_HEADER, plan.action_for("CLAUDE.md").content or "")

    def test_second_plan_after_apply_has_no_changes(self) -> None:
        first = build_workspace_render_plan(
            self.base_agents,
            {},
            ("agents", "claude", "copilot", "cursor"),
        )
        apply_workspace_render_plan(
            self.root,
            first,
        )
        current = {
            path: (self.root / path).read_text(encoding="utf-8")
            for path in first.paths()
        }

        second = build_workspace_render_plan(
            self.base_agents,
            current,
            ("agents", "claude", "copilot", "cursor"),
        )

        self.assertTrue(all(action.kind == "unchanged" for action in second.actions))

    def test_path_traversal_is_rejected_before_rendering(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported workspace target"):
            build_workspace_render_plan(self.base_agents, {}, ("../AGENTS.md",))


if __name__ == "__main__":
    unittest.main()
