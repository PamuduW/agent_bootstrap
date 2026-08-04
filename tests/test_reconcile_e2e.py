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
            (root / "global" / "claude").mkdir()
            (root / "global" / "claude" / "statusline-command.sh").write_text(
                "#!/bin/bash\n# Managed by Agentbot.\necho statusline\n",
                encoding="utf-8",
            )
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

    def test_update_automatically_removes_upstream_deleted_owned_skill(self) -> None:
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
            (root / "global" / "claude").mkdir()
            (root / "global" / "claude" / "statusline-command.sh").write_text(
                "#!/bin/bash\n# Managed by Agentbot.\necho statusline\n",
                encoding="utf-8",
            )
            (root / "skills.sources.yaml").write_text(
                "version: 1\nagents: [codex]\nscope: global\nsources:\n"
                "  - id: wildcard\n    repo: owner/repo\n    skills: all\n",
                encoding="utf-8",
            )
            skills_home = home / ".agents" / "skills"
            deleted_skill = skills_home / "removed-skill"
            deleted_skill.mkdir(parents=True)
            (deleted_skill / "SKILL.md").write_text("# removed\n", encoding="utf-8")
            lock = home / ".agents" / ".skill-lock.json"
            lock.parent.mkdir(parents=True, exist_ok=True)
            lock.write_text(
                json.dumps(
                    {
                        "version": 3,
                        "skills": {
                            "removed-skill": {
                                "source": "owner/repo",
                                "skillPath": "skills/removed-skill/SKILL.md",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            fake_npx = fake_bin / "npx"
            fake_npx.write_text(
                "#!/usr/bin/env bash\n"
                "printf '%s\\n' 'Warning: The following skills from owner/repo appear to have been deleted upstream:'\n"
                "printf '%s\\n' '  • removed-skill'\n",
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
            with mock.patch.dict(
                os.environ,
                {"HOME": str(home), "PATH": f"{fake_bin}:{os.environ['PATH']}"},
                clear=False,
            ), mock.patch.object(
                type(paths),
                "agents_skills_home",
                new_callable=lambda: property(lambda _self: skills_home),
            ), mock.patch.object(
                type(paths),
                "global_skill_lock",
                new_callable=lambda: property(lambda _self: lock),
            ):
                result = AgentbotService(paths).run_reconciliation_update()

            self.assertEqual("applied", result.status)
            self.assertEqual(("removed-skill",), result.removed_skills)
            self.assertFalse(deleted_skill.exists())
            self.assertNotIn("removed-skill", json.loads(lock.read_text(encoding="utf-8"))["skills"])


if __name__ == "__main__":
    unittest.main()
