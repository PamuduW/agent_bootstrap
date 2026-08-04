import json
import tempfile
import unittest
from pathlib import Path


class ClaudeStatuslineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.claude_home = self.root / "home" / ".claude"
        source_dir = self.root / "global" / "claude"
        source_dir.mkdir(parents=True)
        self.source = source_dir / "statusline-command.sh"
        self.source.write_text(
            "#!/bin/bash\n"
            "# Managed by Agentbot. Edit global/claude/statusline-command.sh, then run ./install.sh global.\n"
            "echo statusline\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _paths(self):
        from src.paths import AgentbotPaths

        return AgentbotPaths(
            root=self.root,
            codex_home=self.root / "home" / ".codex",
            claude_home=self.claude_home,
            cursor_home=self.root / "home" / ".cursor",
        )

    def test_install_creates_executable_script_and_settings(self) -> None:
        from src.claude_statusline import install_claude_statusline

        install_claude_statusline(self._paths())

        destination = self.claude_home / "statusline-command.sh"
        self.assertTrue(destination.is_file())
        self.assertTrue(destination.stat().st_mode & 0o111)
        self.assertIn("Managed by Agentbot", destination.read_text(encoding="utf-8"))

        settings = json.loads((self.claude_home / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual(
            {"type": "command", "command": "~/.claude/statusline-command.sh"},
            settings["statusLine"],
        )

    def test_install_merges_settings_without_clobbering_other_keys(self) -> None:
        from src.claude_statusline import install_claude_statusline

        self.claude_home.mkdir(parents=True)
        (self.claude_home / "settings.json").write_text(
            json.dumps({"theme": "dark", "model": "opus"}, indent=2) + "\n",
            encoding="utf-8",
        )

        install_claude_statusline(self._paths())

        settings = json.loads((self.claude_home / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual("dark", settings["theme"])
        self.assertEqual("opus", settings["model"])
        self.assertEqual("~/.claude/statusline-command.sh", settings["statusLine"]["command"])

    def test_install_preserves_foreign_statusline_command(self) -> None:
        from src.claude_statusline import install_claude_statusline

        self.claude_home.mkdir(parents=True)
        (self.claude_home / "settings.json").write_text(
            json.dumps(
                {
                    "statusLine": {
                        "type": "command",
                        "command": "~/.claude/custom-statusline.sh",
                        "padding": 2,
                    }
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        install_claude_statusline(self._paths())

        settings = json.loads((self.claude_home / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual("~/.claude/custom-statusline.sh", settings["statusLine"]["command"])
        self.assertEqual(2, settings["statusLine"]["padding"])

    def test_install_preserves_user_authored_script(self) -> None:
        from src.claude_statusline import install_claude_statusline

        self.claude_home.mkdir(parents=True)
        destination = self.claude_home / "statusline-command.sh"
        custom = "#!/bin/bash\necho custom-user-statusline\n"
        destination.write_text(custom, encoding="utf-8")

        install_claude_statusline(self._paths())

        self.assertEqual(custom, destination.read_text(encoding="utf-8"))
        self.assertTrue(destination.stat().st_mode & 0o111)

    def test_install_refreshes_managed_script(self) -> None:
        from src.claude_statusline import install_claude_statusline

        self.claude_home.mkdir(parents=True)
        destination = self.claude_home / "statusline-command.sh"
        destination.write_text(
            "#!/bin/bash\n# Managed by Agentbot.\necho old\n",
            encoding="utf-8",
        )

        install_claude_statusline(self._paths())

        refreshed = destination.read_text(encoding="utf-8")
        self.assertIn("echo statusline", refreshed)
        self.assertNotIn("echo old", refreshed)

    def test_render_global_outputs_installs_statusline(self) -> None:
        from src.render import render_global_outputs
        from unittest import mock

        (self.root / "global").mkdir(exist_ok=True)
        (self.root / "global" / "AGENTS.md").write_text("# Global\n", encoding="utf-8")
        agents_home = self.root / "home" / ".agents" / "skills"
        agents_home.mkdir(parents=True)

        paths = self._paths()
        with mock.patch.object(
            type(paths),
            "agents_skills_home",
            new_callable=lambda: property(lambda self: agents_home),
        ):
            render_global_outputs(paths)

        self.assertTrue((self.claude_home / "statusline-command.sh").is_file())
        settings = json.loads((self.claude_home / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual("~/.claude/statusline-command.sh", settings["statusLine"]["command"])


if __name__ == "__main__":
    unittest.main()
