from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.workspace_profiles import load_workspace_profiles, select_workspace_profile


class WorkspaceProfilesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.config = self.root / "agentos.yaml"
        self.config.write_text(
            (Path(__file__).parents[1] / "agentos.yaml").read_text(encoding="utf-8"),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_safe_default_uses_complete_boot_targets(self) -> None:
        config = load_workspace_profiles(self.config)
        profile = select_workspace_profile(config, None)

        self.assertEqual("safe-default", profile.name)
        self.assertEqual(
            ("agents", "claude", "copilot", "cursor"),
            profile.default_targets,
        )
        self.assertEqual(
            ("agents", "claude", "copilot", "cursor"),
            profile.allowed_targets,
        )
        self.assertFalse(profile.allow_community_skill_scripts)

    def test_unknown_target_is_rejected(self) -> None:
        path = self.root / "agentos.yaml"
        path.write_text(
            "version: 1\n"
            "active_profile: unsafe\n"
            "profiles:\n"
            "  unsafe:\n"
            "    default_targets: [mcp]\n"
            "    allowed_targets: [mcp]\n"
            "    allow_community_skill_scripts: false\n",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "unsupported workspace target: mcp"):
            load_workspace_profiles(path)

    def test_unknown_profile_is_rejected(self) -> None:
        config = load_workspace_profiles(self.config)

        with self.assertRaisesRegex(ValueError, "unknown workspace profile: missing"):
            select_workspace_profile(config, "missing")

    def test_duplicate_targets_and_empty_defaults_are_rejected(self) -> None:
        duplicate = self.root / "duplicate.yaml"
        duplicate.write_text(
            "version: 1\n"
            "active_profile: default\n"
            "profiles:\n"
            "  default:\n"
            "    default_targets: [agents, agents]\n"
            "    allowed_targets: [agents]\n"
            "    allow_community_skill_scripts: false\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "duplicate workspace target"):
            load_workspace_profiles(duplicate)

        empty = self.root / "empty.yaml"
        empty.write_text(
            "version: 1\n"
            "active_profile: default\n"
            "profiles:\n"
            "  default:\n"
            "    default_targets: []\n"
            "    allowed_targets: [agents]\n"
            "    allow_community_skill_scripts: false\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "default_targets must not be empty"):
            load_workspace_profiles(empty)


if __name__ == "__main__":
    unittest.main()
