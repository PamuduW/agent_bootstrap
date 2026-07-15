import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock


class ReconcileE2ETests(unittest.TestCase):
    def test_reconciliation_has_no_publish_operations(self) -> None:
        source = (Path(__file__).resolve().parents[1] / "src" / "skill_reconcile.py").read_text(encoding="utf-8")
        self.assertNotRegex(source, r"git\s+(add|commit|push)")

    def test_update_uses_fake_npx_and_only_writes_temp_home(self) -> None:
        from src.paths import AgentbotPaths
        from src.service import AgentbotService

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            home = Path(temporary) / "home"
            fake_bin = Path(temporary) / "bin"
            root.mkdir()
            home.mkdir()
            fake_bin.mkdir()
            (root / "global").mkdir()
            (root / "global" / "AGENTS.md").write_text("# baseline\n", encoding="utf-8")
            (root / "skills.sources.yaml").write_text(
                "version: 1\nagents: [codex]\nscope: global\nsources:\n"
                "  - id: explicit\n    repo: owner/repo\n    skills: [alpha]\n",
                encoding="utf-8",
            )
            skills = home / ".agents" / "skills" / "alpha"
            skills.mkdir(parents=True)
            (skills / "SKILL.md").write_text("# alpha\n", encoding="utf-8")
            lock = home / ".agents" / ".skill-lock.json"
            lock.write_text(json.dumps({"version": 3, "skills": {"alpha": {"source": "owner/repo"}}}), encoding="utf-8")
            log = Path(temporary) / "npx.log"
            fake_npx = fake_bin / "npx"
            fake_npx.write_text(
                "#!/usr/bin/env bash\nprintf '%s\\n' \"$*\" >>\"$NPX_LOG\"\n",
                encoding="utf-8",
            )
            fake_npx.chmod(stat.S_IRWXU)
            paths = AgentbotPaths(
                root,
                home / ".codex",
                home / ".claude",
                home / ".cursor",
                home / ".config" / "agentbot",
            )
            with mock.patch.dict(os.environ, {"HOME": str(home), "PATH": f"{fake_bin}:{os.environ['PATH']}", "NPX_LOG": str(log)}, clear=False), \
                 mock.patch.object(type(paths), "agents_skills_home", new_callable=lambda: property(lambda _self: home / ".agents" / "skills")), \
                 mock.patch.object(type(paths), "global_skill_lock", new_callable=lambda: property(lambda _self: lock)):
                result = AgentbotService(paths).run_reconciliation_update(confirm=True)

            self.assertIn(result.status, {"applied", "applied-with-local-changes"}, result.message)
            self.assertIn("skills update", log.read_text(encoding="utf-8"))
            self.assertFalse((Path.home() / ".agents" / ".skill-lock.json").resolve() == lock.resolve())
            self.assertTrue((home / ".codex" / "skills" / "alpha").is_symlink())
            self.assertTrue((home / ".claude" / "skills" / "alpha").is_symlink())


if __name__ == "__main__":
    unittest.main()
