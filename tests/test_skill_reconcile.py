import subprocess
import tempfile
import unittest
from pathlib import Path


class SkillReconcileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _config(self):
        from src.skills_sources import validate_skills_sources

        return validate_skills_sources(
            {
                "version": 1,
                "agents": ["codex"],
                "scope": "global",
                "sources": [
                    {"id": "explicit", "repo": "owner/explicit", "skills": ["alpha", "gone"]},
                    {"id": "wildcard", "repo": "owner/wildcard", "skills": "all"},
                ],
            }
        )

    def test_discover_checkout_skill_names_uses_frontmatter_or_directory(self) -> None:
        from src.skill_reconcile import discover_checkout_skills

        checkout = self.root / "checkout"
        (checkout / "nested" / "alpha").mkdir(parents=True)
        (checkout / "nested" / "alpha" / "SKILL.md").write_text(
            "---\nname: alpha-renamed\n---\n", encoding="utf-8"
        )
        (checkout / "beta").mkdir()
        (checkout / "beta" / "SKILL.md").write_text("# beta\n", encoding="utf-8")

        self.assertEqual(("alpha-renamed", "beta"), discover_checkout_skills(checkout))

    def test_build_plan_tracks_explicit_and_wildcard_deltas_stably(self) -> None:
        from src.skill_reconcile import build_reconcile_plan

        lock = {
            "skills": {
                "wild-old": {"source": "owner/wildcard"},
                "manual": {"source": "other/repo"},
            }
        }
        plan = build_reconcile_plan(
            self._config(),
            discovered={
                "explicit": ("alpha", "newly-discovered"),
                "wildcard": ("wild-new",),
            },
            lock=lock,
        )

        self.assertEqual(("explicit", "wildcard"), plan.updates)
        self.assertEqual(("wild-new",), plan.wildcard_additions)
        self.assertEqual(("wild-old",), plan.wildcard_removals)
        self.assertEqual(("gone",), plan.explicit_missing)
        self.assertEqual(("newly-discovered",), plan.explicit_discovered)
        self.assertEqual(("explicit:gone:remove",), tuple(change.key for change in plan.manifest_changes))
        self.assertNotIn("manual", plan.wildcard_removals)

    def test_unchanged_sources_produce_empty_plan(self) -> None:
        from src.skill_reconcile import build_reconcile_plan

        plan = build_reconcile_plan(
            self._config(),
            discovered={"explicit": ("alpha", "gone"), "wildcard": ("wild-live",)},
            lock={"skills": {"wild-live": {"source": "owner/wildcard"}}},
        )
        self.assertEqual((), plan.updates)
        self.assertEqual((), plan.wildcard_additions)
        self.assertEqual((), plan.wildcard_removals)
        self.assertEqual((), plan.explicit_missing)
        self.assertEqual((), plan.explicit_discovered)
        self.assertEqual((), plan.manifest_changes)

    def test_bash_fallback_parser_preserves_scalar_all(self) -> None:
        fixture = self.root / "skills.sources.yaml"
        fixture.write_text(
            """version: 1\nagents: [codex]\nscope: global\nsources:\n  - id: all\n    repo: owner/all\n    skills: all\n""",
            encoding="utf-8",
        )
        command = "script=\"$1\"; fixture=\"$2\"; set -- help; source \"$script\" >/dev/null; SOURCES_FILE=\"$fixture\" parse_sources"
        result = subprocess.run(
            ["bash", "-c", command, "_", str(Path(__file__).resolve().parents[1] / "bin/skills-install.sh"), str(fixture)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("owner/all\t*\n", result.stdout)


if __name__ == "__main__":
    unittest.main()
