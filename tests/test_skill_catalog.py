import tempfile
import unittest
from pathlib import Path
from unittest import mock


class SkillCatalogTests(unittest.TestCase):
    def test_discovery_uses_frontmatter_name_and_folder_fallback_once(self) -> None:
        from src.skill_catalog import discover_checkout_skills, skill_name_from_file

        with tempfile.TemporaryDirectory() as temporary:
            checkout = Path(temporary)
            named = checkout / "nested" / "folder-name" / "SKILL.md"
            named.parent.mkdir(parents=True)
            named.write_text(
                "---\nname: canonical-name\ndescription: test\n---\n# Skill\n",
                encoding="utf-8",
            )
            fallback = checkout / "fallback-name" / "SKILL.md"
            fallback.parent.mkdir()
            fallback.write_text("# Skill\n", encoding="utf-8")

            self.assertEqual("canonical-name", skill_name_from_file(named))
            self.assertEqual(
                ("canonical-name", "fallback-name"),
                discover_checkout_skills(checkout),
            )

    def test_remote_discovery_removes_temporary_checkout_on_success(self) -> None:
        from src.skill_catalog import discover_remote_catalogs
        from src.skills_sources import SkillSourceEntry, SkillsSourcesConfig

        config = SkillsSourcesConfig(
            version=1,
            agents=["codex"],
            scope="global",
            sources=[SkillSourceEntry("source", "owner/repo", ["*"])],
        )
        destinations: list[Path] = []

        def clone(_repo: str, destination: Path) -> None:
            destinations.append(destination)
            skill = destination / "alpha" / "SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text("# alpha\n", encoding="utf-8")

        catalogs = discover_remote_catalogs(
            config,
            clone_source=clone,
            revision_reader=lambda _checkout: "revision-1",
        )

        self.assertEqual(("alpha",), catalogs[0].skills)
        self.assertTrue(destinations)
        self.assertTrue(all(not destination.exists() for destination in destinations))

    def test_verified_checkouts_reject_remote_drift_before_yielding(self) -> None:
        from src.skill_catalog import (
            SourceCatalog,
            StaleSourceCatalogError,
            discover_remote_catalogs,
            verified_source_checkouts,
        )
        from src.skills_sources import SkillSourceEntry, SkillsSourcesConfig

        config = SkillsSourcesConfig(
            1,
            ["codex"],
            "global",
            [SkillSourceEntry("source", "owner/repo", ["*"])],
        )
        expected = (SourceCatalog("source", "owner/repo", "old", ("alpha",)),)
        destinations: list[Path] = []

        def clone(_repo: str, destination: Path) -> None:
            destinations.append(destination)
            skill = destination / "alpha" / "SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text("# alpha\n", encoding="utf-8")

        with self.assertRaises(StaleSourceCatalogError):
            with verified_source_checkouts(
                config,
                expected,
                clone_source=clone,
                revision_reader=lambda _checkout: "new",
            ):
                self.fail("stale source checkout must not be exposed")

        self.assertTrue(all(not destination.exists() for destination in destinations))

        destinations.clear()

        def fail_clone(_repo: str, destination: Path) -> None:
            destinations.append(destination)
            raise RuntimeError("clone failed")

        with self.assertRaisesRegex(RuntimeError, "clone failed"):
            discover_remote_catalogs(
                config,
                clone_source=fail_clone,
                revision_reader=mock.Mock(),
            )
        self.assertTrue(all(not destination.exists() for destination in destinations))

    def test_default_clone_uses_the_bounded_command_runner(self) -> None:
        from src.command_runner import CommandResult
        from src.skill_catalog import _clone_source

        with tempfile.TemporaryDirectory() as temporary, mock.patch(
            "src.skill_catalog._COMMAND_RUNNER.run",
            return_value=CommandResult(0),
        ) as run:
            _clone_source("owner/repo", Path(temporary) / "checkout")

        self.assertEqual(300, run.call_args.kwargs["timeout_seconds"])
        self.assertEqual(
            ["git", "clone", "--depth=1", "https://github.com/owner/repo.git"],
            run.call_args.args[0][:4],
        )


if __name__ == "__main__":
    unittest.main()
