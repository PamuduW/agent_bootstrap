import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


class ReconcileApplyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "global").mkdir()
        (self.root / "base").mkdir()
        (self.root / "global" / "AGENTS.md").write_text("# global\n", encoding="utf-8")
        (self.root / "base" / "AGENTS.md").write_text(
            "| `gone` | old |\n| `keep` | keep |\n", encoding="utf-8"
        )
        (self.root / "AGENTS.md").write_text(
            "| `gone` | old |\n| `keep` | keep |\n", encoding="utf-8"
        )
        (self.root / "skills.sources.yaml").write_text(
            "version: 1\nagents: [codex]\nscope: global\nsources:\n"
            "  - id: explicit\n    repo: owner/repo\n    skills: [gone, keep]\n"
            "  - id: wildcard\n    repo: owner/all\n    skills: all\n",
            encoding="utf-8",
        )
        self.home = self.root / "home"
        self.agents = self.home / ".agents" / "skills"
        self.codex = self.home / ".codex"
        self.claude = self.home / ".claude"
        self.agents.mkdir(parents=True)
        self._skill("gone")
        self._skill("keep")
        self._skill("manual")
        self.lock = self.home / ".agents" / ".skill-lock.json"
        self.lock.write_text(json.dumps({"version": 3, "skills": {
            "gone": {"source": "owner/repo"},
            "keep": {"source": "owner/repo"},
            "manual": {"source": "manual/repo"},
            "old": {"source": "owner/all"},
        }}), encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _skill(self, name: str) -> Path:
        path = self.agents / name
        path.mkdir(parents=True, exist_ok=True)
        (path / "SKILL.md").write_text(f"# {name}\n", encoding="utf-8")
        return path

    def _paths(self):
        from src.paths import AgentbotPaths

        paths = AgentbotPaths(
            root=self.root,
            codex_home=self.codex,
            claude_home=self.claude,
            cursor_home=self.root / "cursor",
        )
        patches = (
            mock.patch.object(type(paths), "agents_skills_home", new_callable=lambda: property(lambda _self: self.agents)),
            mock.patch.object(type(paths), "global_skill_lock", new_callable=lambda: property(lambda _self: self.lock)),
        )
        return paths, patches

    def test_wildcard_apply_mirrors_owned_catalog_and_preserves_manual(self) -> None:
        from src.skill_reconcile import apply_reconcile_plan, build_reconcile_plan
        from src.skills_sources import load_skills_sources

        checkout = self.root / "checkout"
        self._skill_from(checkout, "new")
        self._skill_from(checkout, "keep-all")
        config = load_skills_sources(self.root / "skills.sources.yaml")
        plan = build_reconcile_plan(
            config,
            discovered={"explicit": ("gone", "keep"), "wildcard": ("new", "keep-all")},
            lock=json.loads(self.lock.read_text(encoding="utf-8")),
        )
        paths, patches = self._paths()
        with patches[0], patches[1]:
            result = apply_reconcile_plan(paths, config, plan, checkouts={"wildcard": checkout}, confirm=True)
        self.assertEqual("applied", result.status)
        self.assertTrue((self.agents / "new").is_dir())
        self.assertFalse((self.agents / "old").exists())
        self.assertTrue((self.agents / "manual").exists())
        lock = json.loads(self.lock.read_text(encoding="utf-8"))["skills"]
        self.assertEqual("owner/all", lock["new"]["source"])
        self.assertNotIn("old", lock)

    def _skill_from(self, checkout: Path, name: str) -> None:
        path = checkout / name
        path.mkdir(parents=True, exist_ok=True)
        (path / "SKILL.md").write_text(f"# {name}\n", encoding="utf-8")

    def test_explicit_removal_updates_manifest_and_canonical_tables(self) -> None:
        from src.skill_reconcile import apply_reconcile_plan, build_reconcile_plan
        from src.skills_sources import load_skills_sources

        config = load_skills_sources(self.root / "skills.sources.yaml")
        plan = build_reconcile_plan(
            config,
            discovered={"explicit": ("keep",), "wildcard": ()},
            lock=json.loads(self.lock.read_text(encoding="utf-8")),
        )
        paths, patches = self._paths()
        with patches[0], patches[1]:
            result = apply_reconcile_plan(paths, config, plan, confirm=True)
        self.assertEqual("applied", result.status)
        self.assertFalse((self.agents / "gone").exists())
        self.assertNotIn("`gone`", (self.root / "base" / "AGENTS.md").read_text(encoding="utf-8"))
        self.assertNotIn("gone", (self.root / "skills.sources.yaml").read_text(encoding="utf-8"))

    def test_unconfirmed_plan_is_preview_only(self) -> None:
        from src.skill_reconcile import apply_reconcile_plan, build_reconcile_plan
        from src.skills_sources import load_skills_sources

        config = load_skills_sources(self.root / "skills.sources.yaml")
        plan = build_reconcile_plan(config, discovered={"explicit": ("gone",), "wildcard": ("new",)}, lock={"skills": {}})
        paths, patches = self._paths()
        with patches[0], patches[1]:
            result = apply_reconcile_plan(paths, config, plan)
        self.assertEqual("confirmation_required", result.status)
        self.assertTrue((self.agents / "gone").exists())

    def test_noop_dry_run_reports_no_changed_paths(self) -> None:
        from src.skill_reconcile import apply_reconcile_plan, build_reconcile_plan
        from src.skills_sources import load_skills_sources

        config = load_skills_sources(self.root / "skills.sources.yaml")
        lock = json.loads(self.lock.read_text(encoding="utf-8"))
        plan = build_reconcile_plan(
            config,
            discovered={"explicit": ("gone", "keep"), "wildcard": ("old",)},
            lock=lock,
        )
        paths, patches = self._paths()
        with patches[0], patches[1]:
            result = apply_reconcile_plan(paths, config, plan, confirm=True, dry_run=True)

        self.assertEqual("preview", result.status)
        self.assertEqual((), result.changed_paths)

    def test_noop_apply_preserves_global_lock_bytes_and_mtime(self) -> None:
        from src.skill_reconcile import apply_reconcile_plan, build_reconcile_plan
        from src.skills_sources import load_skills_sources

        original = '{"version":3,"skills":{"gone":{"source":"owner/repo"},"keep":{"source":"owner/repo"},"manual":{"source":"manual/repo"},"old":{"source":"owner/all"}}}\n'
        self.lock.write_text(original, encoding="utf-8")
        os.utime(self.lock, (1_000_000_000, 1_000_000_000))
        before_mtime = self.lock.stat().st_mtime_ns
        config = load_skills_sources(self.root / "skills.sources.yaml")
        plan = build_reconcile_plan(
            config,
            discovered={"explicit": ("gone", "keep"), "wildcard": ("old",)},
            lock=json.loads(original),
        )
        paths, patches = self._paths()
        with patches[0], patches[1]:
            result = apply_reconcile_plan(paths, config, plan, confirm=True)

        self.assertEqual("applied", result.status)
        self.assertEqual((), result.changed_paths)
        self.assertEqual(original, self.lock.read_text(encoding="utf-8"))
        self.assertEqual(before_mtime, self.lock.stat().st_mtime_ns)

    def test_failure_restores_files_and_keeps_backup(self) -> None:
        from src.skill_reconcile import apply_reconcile_plan, build_reconcile_plan
        from src.skills_sources import load_skills_sources

        (self.root / "AGENTS.md").write_text("| `keep` | keep |\n", encoding="utf-8")
        config = load_skills_sources(self.root / "skills.sources.yaml")
        plan = build_reconcile_plan(config, discovered={"explicit": ("keep",), "wildcard": ()}, lock=json.loads(self.lock.read_text(encoding="utf-8")))
        paths, patches = self._paths()
        before = (self.root / "skills.sources.yaml").read_text(encoding="utf-8")
        with patches[0], patches[1]:
            result = apply_reconcile_plan(paths, config, plan, confirm=True)
        self.assertEqual("failed", result.status)
        self.assertIsNotNone(result.backup_path)
        self.assertEqual(before, (self.root / "skills.sources.yaml").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
