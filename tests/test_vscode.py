"""VS Code host detection, extension planning, and JSONC settings merging."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from src.vscode import (
    apply_settings,
    installed_extensions,
    merge_settings_text,
    plan_extensions,
    plan_settings,
    read_settings,
    strip_jsonc,
    windows_host,
    wsl_host,
)


class VSCodeHostTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def _server_with_cli(self, *builds: str) -> Path:
        server = self.root / ".vscode-server"
        (server / "extensions").mkdir(parents=True)
        for build in builds:
            cli = server / "bin" / build / "bin" / "remote-cli" / "code"
            cli.parent.mkdir(parents=True)
            cli.write_text("#!/bin/sh\n", encoding="utf-8")
        return server

    def test_the_wsl_host_uses_its_own_cli_not_the_one_on_path(self) -> None:
        """`code` on PATH inside WSL is the Windows binary reached through
        interop. Driving the WSL host with it installs into the other host
        while reporting success for this one."""
        server = self._server_with_cli("abc123")

        host = wsl_host(self.root)

        self.assertEqual(host.cli, server / "bin/abc123/bin/remote-cli/code")
        self.assertEqual(host.settings_path, server / "data/Machine/settings.json")
        self.assertTrue(host.available)

    def test_the_wsl_host_picks_the_most_recent_server_build(self) -> None:
        """Server builds accumulate; the newest is the one in use."""
        server = self._server_with_cli("old", "new")
        older = server / "bin/old/bin/remote-cli/code"
        newer = server / "bin/new/bin/remote-cli/code"
        os.utime(older, (1_000, 1_000))
        os.utime(newer, (2_000, 2_000))

        self.assertEqual(wsl_host(self.root).cli, newer)

    def test_a_missing_wsl_server_is_unavailable_not_an_error(self) -> None:
        host = wsl_host(self.root)

        self.assertFalse(host.available)
        self.assertFalse(host.can_install)

    def test_several_windows_profiles_refuse_to_guess(self) -> None:
        """Writing into one of several Windows accounts on a coin flip is worse
        than reporting that the host cannot be resolved."""
        for user in ("alice", "bob"):
            (self.root / "Users" / user / "AppData/Roaming/Code/User").mkdir(parents=True)

        host = windows_host(self.root)

        self.assertFalse(host.can_install)
        self.assertIn("cannot choose one", host.detail)

    def test_no_windows_profile_is_a_reported_skip(self) -> None:
        host = windows_host(self.root)

        self.assertFalse(host.can_install)
        self.assertIn("no Windows VS Code profile", host.detail)

    def test_a_single_windows_profile_resolves_both_paths(self) -> None:
        user_dir = self.root / "Users/pamud/AppData/Roaming/Code/User"
        user_dir.mkdir(parents=True)
        extensions = self.root / "Users/pamud/.vscode/extensions"
        extensions.mkdir(parents=True)
        cli = self.root / "Program Files/Microsoft VS Code/bin/code"
        cli.parent.mkdir(parents=True)
        cli.write_text("", encoding="utf-8")

        host = windows_host(self.root)

        self.assertEqual(host.settings_path, user_dir / "settings.json")
        self.assertEqual(host.extensions_dir, extensions)
        self.assertEqual(host.cli, cli)
        self.assertTrue(host.can_install)


class ExtensionPlanTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.extensions = self.root / "extensions"
        self.extensions.mkdir()

    def _host(self):
        return replace(wsl_host(self.root), extensions_dir=self.extensions)

    def _install(self, name: str) -> None:
        (self.extensions / name).mkdir()

    def test_identifiers_drop_versions_and_platform_suffixes(self) -> None:
        self._install("charliermarsh.ruff-2026.78.0-linux-x64")
        self._install("davidanson.vscode-markdownlint-0.62.1")
        (self.extensions / "extensions.json").write_text("[]", encoding="utf-8")

        self.assertEqual(
            installed_extensions(self._host()),
            ("charliermarsh.ruff", "davidanson.vscode-markdownlint"),
        )

    def test_an_unmanaged_extension_is_reported_never_removed(self) -> None:
        """Absence from the manifest is not a request to uninstall."""
        self._install("keepme.tool-1.0.0")

        plan = plan_extensions(self._host(), ["wanted.thing"])

        self.assertEqual(plan.missing, ("wanted.thing",))
        self.assertEqual(plan.unmanaged, ("keepme.tool",))

    def test_an_installed_desired_extension_is_not_reinstalled(self) -> None:
        self._install("keepme.tool-1.0.0")

        plan = plan_extensions(self._host(), ["keepme.tool"])

        self.assertTrue(plan.is_noop)

    def test_an_unavailable_host_is_a_skip_not_a_failure(self) -> None:
        plan = plan_extensions(wsl_host(self.root), ["wanted.thing"])

        self.assertIsNotNone(plan.skipped)
        self.assertEqual(plan.missing, ())


class SettingsMergeTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.settings = Path(temporary.name) / "settings.json"

    def test_comments_and_trailing_commas_parse(self) -> None:
        self.settings.write_text(
            '{\n  // a line comment\n  "editor.fontSize": 13, /* inline */\n'
            '  "files.autoSave": "off",\n}\n',
            encoding="utf-8",
        )

        parsed, error = read_settings(self.settings)

        self.assertIsNone(error)
        self.assertEqual(parsed, {"editor.fontSize": 13, "files.autoSave": "off"})

    def test_a_url_inside_a_string_is_not_a_comment(self) -> None:
        """`//` inside a string starts no comment. Treating it as one truncates
        the value and makes the rest of the file unparseable."""
        text = '{"a": "https://example.com/x", "b": 1}'

        self.assertEqual(
            json.loads(strip_jsonc(text)),
            {"a": "https://example.com/x", "b": 1},
        )

    def test_merging_preserves_comments_and_unrelated_keys(self) -> None:
        """The reason the merge edits text rather than re-serialising a parsed
        object: re-serialising deletes every comment the operator wrote."""
        original = '{\n  // keep me\n  "editor.fontSize": 13,\n  "other": true\n}\n'

        merged = merge_settings_text(original, {"editor.fontSize": 15})

        self.assertIn("// keep me", merged)
        self.assertIn('"other": true', merged)
        self.assertEqual(json.loads(strip_jsonc(merged))["editor.fontSize"], 15)

    def test_a_key_that_is_absent_is_appended(self) -> None:
        merged = merge_settings_text('{\n  "a": 1\n}\n', {"b": "two"})

        self.assertEqual(json.loads(strip_jsonc(merged)), {"a": 1, "b": "two"})

    def test_merging_into_an_empty_object_stays_valid(self) -> None:
        merged = merge_settings_text("{}", {"a": 1})

        self.assertEqual(json.loads(strip_jsonc(merged)), {"a": 1})

    def test_an_object_value_is_replaced_whole(self) -> None:
        original = '{\n  "nested": {"keep": 1, "drop": 2},\n  "after": true\n}\n'

        merged = merge_settings_text(original, {"nested": {"only": 3}})

        parsed = json.loads(strip_jsonc(merged))
        self.assertEqual(parsed["nested"], {"only": 3})
        self.assertIs(parsed["after"], True)

    def test_a_nested_key_of_the_same_name_is_left_alone(self) -> None:
        """Depth matters: replacing the inner "a" would corrupt an unrelated
        block and leave the top-level setting untouched."""
        original = '{\n  "outer": {"a": 1},\n  "a": 2\n}\n'

        merged = merge_settings_text(original, {"a": 99})

        self.assertEqual(json.loads(strip_jsonc(merged)), {"outer": {"a": 1}, "a": 99})

    def test_a_key_named_inside_a_comment_is_not_matched(self) -> None:
        original = '{\n  // "a": 1 is what we used to do\n  "a": 2\n}\n'

        merged = merge_settings_text(original, {"a": 3})

        self.assertEqual(json.loads(strip_jsonc(merged)), {"a": 3})
        self.assertIn("is what we used to do", merged)

    def test_an_existing_trailing_comma_does_not_become_two(self) -> None:
        """A trailing comma before the closing brace is legal JSONC and common
        in hand-written settings. A second one is legal nowhere -- this broke
        every real settings file that had one."""
        original = '{\n  "a": 1,\n}\n'

        merged = merge_settings_text(original, {"b": 2})

        self.assertNotIn(",,", merged)
        self.assertEqual(json.loads(strip_jsonc(merged)), {"a": 1, "b": 2})

    def test_appending_matches_the_file_s_line_endings(self) -> None:
        """Settings written on the Windows side are CRLF; appending LF would
        leave one mixed line in a file the operator maintains by hand."""
        original = '{\r\n  "a": 1\r\n}\r\n'

        merged = merge_settings_text(original, {"b": 2})

        self.assertNotIn("\n  \"b\"", merged.replace("\r\n", "\r"))
        self.assertEqual(json.loads(strip_jsonc(merged)), {"a": 1, "b": 2})

    def test_the_plan_separates_additions_from_changes(self) -> None:
        self.settings.write_text('{"same": 1, "differs": 2}', encoding="utf-8")

        plan = plan_settings(self.settings, {"same": 1, "differs": 3, "new": 4})

        self.assertEqual(plan.additions, {"new": 4})
        self.assertEqual(plan.changes, {"differs": (2, 3)})

    def test_an_unparseable_file_is_never_written(self) -> None:
        """A file we cannot read is a file we must not replace."""
        broken = '{"a": '
        self.settings.write_text(broken, encoding="utf-8")

        plan = apply_settings(self.settings, {"a": 1})

        self.assertIsNotNone(plan.unreadable)
        self.assertEqual(self.settings.read_text(encoding="utf-8"), broken)

    def test_applying_backs_up_the_original(self) -> None:
        self.settings.write_text('{"a": 1}\n', encoding="utf-8")

        apply_settings(self.settings, {"a": 2})

        backup = self.settings.with_name(self.settings.name + ".agentbot-backup")
        self.assertEqual(json.loads(backup.read_text(encoding="utf-8")), {"a": 1})

    def test_applying_is_idempotent_and_keeps_comments(self) -> None:
        self.settings.write_text('{\n  // hi\n  "a": 1\n}\n', encoding="utf-8")

        self.assertTrue(apply_settings(self.settings, {"a": 1}).is_noop)
        apply_settings(self.settings, {"a": 2})
        after_first = self.settings.read_text(encoding="utf-8")

        self.assertTrue(apply_settings(self.settings, {"a": 2}).is_noop)
        self.assertEqual(self.settings.read_text(encoding="utf-8"), after_first)
        self.assertIn("// hi", after_first)


if __name__ == "__main__":
    unittest.main()
