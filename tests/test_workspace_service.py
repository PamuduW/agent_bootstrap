from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from src.paths import AgentbotPaths
from src.workspace_service import WorkspaceService
from src.workspace_state import WorkspaceRecord


class WorkspaceServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.product_root = Path(__file__).parents[1]
        self.config_home = self.root / "config"
        self.paths = AgentbotPaths(
            root=self.product_root,
            codex_home=self.root / "codex",
            claude_home=self.root / "claude",
            cursor_home=self.root / "cursor",
            config_home=self.config_home,
        )
        self.workspace_service = WorkspaceService(self.paths)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _git_repo(self, name: str) -> Path:
        path = self.root / name
        path.mkdir()
        subprocess.run(["git", "init", "-q", str(path)], check=True)
        return path

    def test_apply_registers_a_successful_folder_render(self) -> None:
        repo = self._git_repo("good-repo")

        result = self.workspace_service.apply(
            repo,
            profile_name=None,
            targets=("agents", "claude"),
            register=True,
        )

        self.assertEqual("applied", result.status)
        self.assertTrue((repo / "AGENTS.md").is_file())
        self.assertTrue((repo / "CLAUDE.md").is_file())
        records = self.workspace_service.store.load()
        self.assertEqual([str(repo.resolve())], [item.path for item in records])
        self.assertEqual("git", records[0].kind)
        self.assertEqual(("agents", "claude"), records[0].targets)

    def test_custom_agents_are_preserved_and_recorded(self) -> None:
        custom = self.root / "custom-folder"
        custom.mkdir()
        (custom / "AGENTS.md").write_text("# User policy\n", encoding="utf-8")

        result = self.workspace_service.apply(
            custom,
            profile_name=None,
            targets=("claude",),
            register=True,
        )

        self.assertEqual("applied", result.status)
        self.assertEqual("# User policy\n", (custom / "AGENTS.md").read_text(encoding="utf-8"))
        record = self.workspace_service.store.load()[0]
        self.assertEqual("directory", record.kind)
        self.assertEqual("custom", record.policy_mode)
        self.assertEqual(("agents", "claude"), record.targets)

    def test_batch_continues_after_one_workspace_review_template(self) -> None:
        good = self._git_repo("good")
        conflict = self.root / "conflict"
        conflict.mkdir()
        (conflict / "AGENTS.md").write_text("# User policy\n", encoding="utf-8")
        (conflict / "CLAUDE.md").write_text("# User instructions\n", encoding="utf-8")

        self.workspace_service.store.replace(
            (
                WorkspaceRecord(
                    path=str(good.resolve()),
                    kind="git",
                    policy_mode="managed",
                    profile="safe-default",
                    targets=("agents", "claude"),
                    enabled=True,
                    last_commit=None,
                    last_rendered_at=None,
                ),
                WorkspaceRecord(
                    path=str(conflict.resolve()),
                    kind="directory",
                    policy_mode="custom",
                    profile="safe-default",
                    targets=("agents", "claude"),
                    enabled=True,
                    last_commit=None,
                    last_rendered_at=None,
                ),
            )
        )

        report = self.workspace_service.resync(apply=False)

        self.assertEqual(2, len(report.results))
        statuses = {result.path.name: result.status for result in report.results}
        self.assertEqual("preview", statuses["good"])
        self.assertEqual("preview", statuses["conflict"])

    def test_recorded_git_workspace_that_loses_git_identity_fails(self) -> None:
        repo = self._git_repo("recorded")
        self.workspace_service.store.replace(
            (
                WorkspaceRecord(
                    path=str(repo.resolve()),
                    kind="git",
                    policy_mode="managed",
                    profile="safe-default",
                    targets=("agents",),
                    enabled=True,
                    last_commit=None,
                    last_rendered_at=None,
                ),
            )
        )
        (repo / ".git").rename(repo / ".git.saved")

        report = self.workspace_service.resync(apply=False)

        self.assertEqual("failed", report.results[0].status)
        self.assertIn("no longer resolves to the recorded Git root", report.results[0].message)

    def test_symlinked_output_is_reported_as_conflict(self) -> None:
        target = self.root / "symlinked"
        target.mkdir()
        outside = self.root / "outside-claude.md"
        outside.write_text("# User-owned\n", encoding="utf-8")
        (target / "CLAUDE.md").symlink_to(outside)

        result = self.workspace_service.preview(
            target,
            profile_name=None,
            targets=("claude",),
        )

        self.assertEqual("conflict", result.status)
        self.assertIn("symlink", result.message)

    def test_apply_preserves_user_file_and_writes_review_template(self) -> None:
        target = self.root / "review-apply"
        target.mkdir()
        claude = target / "CLAUDE.md"
        claude.write_text("# User-owned\n", encoding="utf-8")

        result = self.workspace_service.apply(
            target,
            profile_name=None,
            targets=("claude",),
            register=True,
        )

        self.assertEqual("applied", result.status)
        self.assertEqual("# User-owned\n", claude.read_text(encoding="utf-8"))
        review = target / "CLAUDE_temp.md"
        self.assertTrue(review.is_file())
        self.assertIn("sha256=", review.read_text(encoding="utf-8"))
        self.assertEqual(1, len(self.workspace_service.store.load()))

    def test_apply_does_not_overwrite_an_edited_current_review_template(self) -> None:
        target = self.root / "review-repeat"
        target.mkdir()
        claude = target / "CLAUDE.md"
        claude.write_text("# User-owned\n", encoding="utf-8")

        first = self.workspace_service.apply(
            target,
            profile_name=None,
            targets=("claude",),
            register=True,
        )
        self.assertEqual("applied", first.status)

        review = target / "CLAUDE_temp.md"
        review.write_text(review.read_text(encoding="utf-8") + "\nMy notes.\n", encoding="utf-8")

        second = self.workspace_service.apply(
            target,
            profile_name=None,
            targets=("claude",),
            register=True,
        )

        self.assertEqual("applied", second.status)
        self.assertIn("My notes.", review.read_text(encoding="utf-8"))
        self.assertFalse((target / "CLAUDE_temp_1.md").exists())


if __name__ == "__main__":
    unittest.main()
