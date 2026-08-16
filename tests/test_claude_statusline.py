import json
import os
import re
import subprocess
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

    def _run_real_statusline(
        self, payload: dict | str
    ) -> subprocess.CompletedProcess[str]:
        script = Path(__file__).resolve().parents[1] / "global/claude/statusline-command.sh"
        raw = payload if isinstance(payload, str) else json.dumps(payload)
        return subprocess.run(
            ["bash", str(script)],
            input=raw,
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "TZ": "UTC"},
        )

    @staticmethod
    def _plain_output(result: subprocess.CompletedProcess[str]) -> str:
        return re.sub(r"\033\[[0-9;]*m", "", result.stdout).strip()

    def test_real_statusline_preserves_sparse_fields(self) -> None:
        result = self._run_real_statusline(
            {
                "workspace": {"current_dir": str(self.root)},
                "model": {"display_name": "High"},
                "context_window": {"used_percentage": 42},
            }
        )

        self.assertEqual(0, result.returncode)
        self.assertEqual("", result.stderr)
        self.assertIn("High", result.stdout)
        self.assertIn("Context 42% used", self._plain_output(result))
        self.assertNotIn("High (42)", result.stdout)

    def test_real_statusline_accepts_null_pre_response_fields(self) -> None:
        result = self._run_real_statusline(
            {
                "workspace": {"current_dir": str(self.root)},
                "model": {"display_name": "Opus"},
                "output_style": None,
                "context_window": None,
                "effort": None,
                "thinking": None,
            }
        )

        self.assertEqual(0, result.returncode)
        self.assertEqual("", result.stderr)
        self.assertIn("Opus", result.stdout)

    def test_real_statusline_falls_back_for_malformed_json(self) -> None:
        result = self._run_real_statusline("{not-json")

        self.assertEqual(0, result.returncode)
        self.assertEqual("", result.stderr)
        self.assertEqual("Claude Code\n", result.stdout)

    def test_real_statusline_renders_complete_high_effort_payload(self) -> None:
        result = self._run_real_statusline(
            {
                "workspace": {"current_dir": str(self.root)},
                "model": {"display_name": "Opus 4.1 (1M context)"},
                "output_style": {"name": "default"},
                "context_window": {
                    "used_percentage": 42,
                    "remaining_percentage": 58,
                    "total_input_tokens": 420000,
                    "context_window_size": 1000000,
                },
                "effort": {"level": "high"},
                "thinking": {"enabled": True},
                "rate_limits": {
                    "five_hour": {
                        "used_percentage": 24,
                        "resets_at": 4102444800,
                    },
                    "seven_day": {
                        "used_percentage": 41,
                        "resets_at": 4102444800,
                    },
                },
            }
        )

        self.assertEqual(0, result.returncode)
        self.assertEqual("", result.stderr)
        self.assertEqual(
            f"Opus 4.1 High (1M context) · {self.root} · "
            "Context 42% used · 5h 76% left (reset Jan 1 00:00) · "
            "7d 59% left (reset Jan 1 00:00)",
            self._plain_output(result),
        )

    def test_real_statusline_hides_unavailable_rate_limits(self) -> None:
        result = self._run_real_statusline(
            {
                "workspace": {"current_dir": str(self.root)},
                "model": {"display_name": "Opus"},
                "context_window": {
                    "used_percentage": 10,
                    "remaining_percentage": 90,
                },
            }
        )

        self.assertEqual(0, result.returncode)
        self.assertEqual("", result.stderr)
        self.assertEqual(
            f"Opus · {self.root} · Context 10% used",
            self._plain_output(result),
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

    def test_install_only_replaces_exact_managed_statusline_commands(self) -> None:
        from src.claude_statusline import install_claude_statusline

        cases = {
            "~/.claude/statusline-command.sh": "~/.claude/statusline-command.sh",
            "bash ~/.claude/statusline-command.sh": "~/.claude/statusline-command.sh",
            "/usr/bin/bash ~/.claude/statusline-command.sh": "~/.claude/statusline-command.sh",
            "/tmp/custom/statusline-command.sh": "/tmp/custom/statusline-command.sh",
            "bash /tmp/custom/statusline-command.sh": "bash /tmp/custom/statusline-command.sh",
            "~/.claude/statusline-command.sh --compact": "~/.claude/statusline-command.sh --compact",
            "bash -c ~/.claude/statusline-command.sh": "bash -c ~/.claude/statusline-command.sh",
            "printf statusline-command.sh": "printf statusline-command.sh",
            "bash '~/.claude/statusline-command.sh": "bash '~/.claude/statusline-command.sh",
        }

        for command, expected in cases.items():
            with self.subTest(command=command):
                settings_path = self.claude_home / "settings.json"
                self.claude_home.mkdir(parents=True, exist_ok=True)
                settings_path.write_text(
                    json.dumps({"statusLine": {"type": "command", "command": command}})
                    + "\n",
                    encoding="utf-8",
                )

                install_claude_statusline(self._paths())

                settings = json.loads(settings_path.read_text(encoding="utf-8"))
                self.assertEqual(expected, settings["statusLine"]["command"])

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

    def test_doctor_reports_stale_and_missing_jq(self) -> None:
        from src.claude_statusline import doctor_claude_statusline, install_claude_statusline
        from unittest import mock

        paths = self._paths()
        install_claude_statusline(paths)
        destination = self.claude_home / "statusline-command.sh"
        destination.write_text(
            "#!/bin/bash\n# Managed by Agentbot.\necho stale\n",
            encoding="utf-8",
        )

        with mock.patch("src.claude_statusline.shutil.which", return_value=None):
            messages = [issue.message for issue in doctor_claude_statusline(paths)]

        self.assertTrue(any("stale" in message for message in messages))
        self.assertTrue(any("jq is not installed" in message for message in messages))

    def test_doctor_reports_missing_install(self) -> None:
        from src.claude_statusline import doctor_claude_statusline

        messages = [issue.message for issue in doctor_claude_statusline(self._paths())]
        self.assertTrue(any("not installed" in message for message in messages))


if __name__ == "__main__":
    unittest.main()
