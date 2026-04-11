import json
import hashlib
import io
import tempfile
import unittest
from pathlib import Path
from contextlib import redirect_stdout


class BootstrapEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

        (self.root / "catalog").mkdir()
        (self.root / "skills").mkdir()
        (self.root / "mcp").mkdir()
        (self.root / "global").mkdir()
        (self.root / "state").mkdir()
        (self.root / "templates").mkdir()

        packages = {
            "packages": [
                {
                    "id": "alpha",
                    "display_name": "Alpha",
                    "origin": "internal",
                    "dedupe_group": "alpha",
                    "supported_surfaces": ["codex", "claude", "cursor", "copilot"],
                    "mcp_keys": ["alpha-mcp"],
                },
                {
                    "id": "beta",
                    "display_name": "Beta",
                    "origin": "internal",
                    "dedupe_group": "beta",
                    "supported_surfaces": ["codex", "claude"],
                    "mcp_keys": [],
                },
            ]
        }
        (self.root / "catalog" / "packages.json").write_text(
            json.dumps(packages, indent=2), encoding="utf-8"
        )

        (self.root / "mcp" / "mcp.json").write_text(
            json.dumps(
                {
                    "mcpServers": {
                        "alpha-mcp": {"command": "alpha"},
                        "unused-mcp": {"command": "unused"},
                    }
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        (self.root / "global" / "AGENTS.md").write_text(
            "# Global Baseline\n\nShared global instructions.\n",
            encoding="utf-8",
        )
        (self.root / "templates" / "AGENTS.md").write_text(
            "# Project Overlay\n\nRepo-specific instructions.\n",
            encoding="utf-8",
        )

        alpha_skill = self.root / "skills" / "alpha-skill"
        alpha_skill.mkdir()
        (alpha_skill / "SKILL.md").write_text("# Alpha Skill\n", encoding="utf-8")
        beta_skill = self.root / "skills" / "beta-skill"
        beta_skill.mkdir()
        (beta_skill / "SKILL.md").write_text("# Beta Skill\n", encoding="utf-8")

        self.cursor_cache = self.root / "cursor-cache"
        (self.cursor_cache / "gamma" / "hash123").mkdir(parents=True)
        (self.cursor_cache / "gamma" / "hash123" / "README.md").write_text(
            "gamma plugin", encoding="utf-8"
        )
        (self.cursor_cache / "gamma" / "hash123" / "skills" / "plan").mkdir(parents=True)
        (self.cursor_cache / "gamma" / "hash123" / "skills" / "plan" / "SKILL.md").write_text(
            "# Gamma Plan\n", encoding="utf-8"
        )
        (self.cursor_cache / "gamma" / "hash123" / "rules").mkdir(parents=True)
        (self.cursor_cache / "gamma" / "hash123" / "rules" / "workflow.mdc").write_text(
            "gamma rule\n", encoding="utf-8"
        )
        (self.cursor_cache / "gamma" / "hash123" / "commands").mkdir(parents=True)
        (self.cursor_cache / "gamma" / "hash123" / "commands" / "triage.md").write_text(
            "gamma command\n", encoding="utf-8"
        )
        (self.cursor_cache / "gamma" / "hash123" / "agents").mkdir(parents=True)
        (self.cursor_cache / "gamma" / "hash123" / "agents" / "helper.md").write_text(
            "gamma agent\n", encoding="utf-8"
        )
        (self.cursor_cache / "gamma" / "hash123" / "hooks").mkdir(parents=True)
        (self.cursor_cache / "gamma" / "hash123" / "hooks" / "run.sh").write_text(
            "#!/usr/bin/env bash\n", encoding="utf-8"
        )
        (self.cursor_cache / "gamma" / "hash123" / "mcp.json").write_text(
            json.dumps({"mcpServers": {"gamma-mcp": {"command": "gamma"}}}, indent=2),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _engine(self):
        from src.agent_bootstrap.paths import BootstrapPaths
        from src.agent_bootstrap.service import BootstrapService

        paths = BootstrapPaths(
            root=self.root,
            cursor_plugin_cache=self.cursor_cache,
            codex_home=self.root / "home" / ".codex",
            claude_home=self.root / "home" / ".claude",
            cursor_home=self.root / "home" / ".cursor",
        )
        return BootstrapService(paths)

    def test_package_rows_preserve_managed_and_detected_state_separately(self):
        service = self._engine()

        overview = service.build_overview()
        rows = {row.package_id: row for row in overview.package_rows}

        self.assertIn("alpha", rows)
        self.assertTrue(rows["alpha"].managed)
        self.assertFalse(rows["alpha"].detected_local)
        self.assertTrue(rows["alpha"].enabled)

        self.assertIn("beta", rows)
        self.assertTrue(rows["beta"].managed)
        self.assertFalse(rows["beta"].detected_local)
        self.assertTrue(rows["beta"].enabled)

        self.assertIn("gamma", rows)
        self.assertFalse(rows["gamma"].managed)
        self.assertTrue(rows["gamma"].detected_local)
        self.assertFalse(rows["gamma"].enabled)

    def test_disabled_detected_package_stays_visible(self):
        service = self._engine()
        service.set_package_enabled("gamma", False)

        overview = service.build_overview()
        rows = {row.package_id: row for row in overview.package_rows}

        self.assertIn("gamma", rows)
        self.assertTrue(rows["gamma"].detected_local)
        self.assertFalse(rows["gamma"].enabled)

    def test_render_workspace_outputs_merge_global_and_repo_agents(self):
        service = self._engine()

        workspace = self.root / "workspace"
        workspace.mkdir()
        (workspace / "AGENTS.md").write_text(
            "# Repo Overlay\n\nProject-specific instructions.\n",
            encoding="utf-8",
        )

        service.render_workspace(workspace)

        claude_md = (workspace / "CLAUDE.md").read_text(encoding="utf-8")
        copilot_md = (workspace / ".github" / "copilot-instructions.md").read_text(
            encoding="utf-8"
        )
        cursor_rule = (workspace / ".cursor" / "rules" / "bootstrap-skills.mdc").read_text(
            encoding="utf-8"
        )
        cursor_mcp = json.loads((workspace / ".cursor" / "mcp.json").read_text(encoding="utf-8"))
        gitignore = (workspace / ".gitignore").read_text(encoding="utf-8")

        self.assertIn("Global Baseline", claude_md)
        self.assertIn("Repo Overlay", claude_md)
        self.assertIn("Global Baseline", copilot_md)
        self.assertIn("Repo Overlay", copilot_md)
        self.assertIn("alpha-skill", cursor_rule)
        self.assertNotIn("beta-skill", cursor_rule)
        self.assertEqual({"alpha-mcp"}, set(cursor_mcp["mcpServers"].keys()))
        self.assertIn("CLAUDE.md", gitignore)
        self.assertIn(".github/copilot-instructions.md", gitignore)
        self.assertIn(".cursor/rules/bootstrap-skills.mdc", gitignore)
        self.assertIn(".cursor/mcp.json", gitignore)

    def test_render_workspace_updates_gitignore_without_duplicate_block(self):
        service = self._engine()

        workspace = self.root / "workspace"
        workspace.mkdir()
        (workspace / ".gitignore").write_text("node_modules/\n", encoding="utf-8")

        service.render_workspace(workspace)
        service.render_workspace(workspace)

        gitignore = (workspace / ".gitignore").read_text(encoding="utf-8")

        self.assertIn("node_modules/", gitignore)
        self.assertNotIn("# agent_bootstrap generated outputs", gitignore)
        self.assertEqual(1, gitignore.count("CLAUDE.md"))

    def test_render_workspace_gitignore_migrates_old_marker_block(self):
        service = self._engine()

        workspace = self.root / "workspace"
        workspace.mkdir()
        (workspace / ".gitignore").write_text(
            "node_modules/\n\n"
            "# agent_bootstrap generated outputs\n"
            "CLAUDE.md\n"
            ".github/copilot-instructions.md\n"
            ".cursor/rules/bootstrap-skills.mdc\n"
            ".cursor/mcp.json\n"
            "# /agent_bootstrap generated outputs\n",
            encoding="utf-8",
        )

        service.render_workspace(workspace)

        gitignore = (workspace / ".gitignore").read_text(encoding="utf-8")

        self.assertIn("node_modules/", gitignore)
        self.assertNotIn("# agent_bootstrap generated outputs", gitignore)
        self.assertNotIn("# /agent_bootstrap generated outputs", gitignore)
        self.assertEqual(1, gitignore.count("CLAUDE.md"))

    def test_render_workspace_rejects_stale_generated_workspace_agents(self):
        service = self._engine()

        workspace = self.root / "workspace"
        workspace.mkdir()
        (workspace / "AGENTS.md").write_text(
            "<!-- Generated by agent_bootstrap. Edit canonical AGENTS.md files instead. -->\n\n"
            "# Old Generated Copy\n\nDo not reuse this.\n",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "looks generated"):
            service.render_workspace(workspace)

    def test_render_workspace_rejects_symlinked_agents_file(self):
        service = self._engine()

        workspace = self.root / "workspace"
        workspace.mkdir()
        (workspace / "CLAUDE.md").write_text("generated\n", encoding="utf-8")
        (workspace / "AGENTS.md").symlink_to("CLAUDE.md")

        with self.assertRaisesRegex(ValueError, "must be a real authored file, not a symlink"):
            service.render_workspace(workspace)

    def test_render_global_outputs_syncs_codex_skill_links(self):
        service = self._engine()

        service.render_global()

        codex_agents = (self.root / "home" / ".codex" / "AGENTS.md").read_text(
            encoding="utf-8"
        )
        codex_skill_link = self.root / "home" / ".codex" / "skills" / "alpha-skill"

        self.assertIn("Global Baseline", codex_agents)
        self.assertTrue(codex_skill_link.is_symlink())
        self.assertEqual(
            (self.root / "skills" / "alpha-skill").resolve(),
            codex_skill_link.resolve(),
        )
        self.assertTrue((self.root / "home" / ".codex" / "skills" / "beta-skill").is_symlink())

    def test_track_workspace_only_persists_after_successful_render(self):
        service = self._engine()

        workspace = self.root / "workspace"
        workspace.mkdir()
        (workspace / "CLAUDE.md").write_text("generated\n", encoding="utf-8")
        (workspace / "AGENTS.md").symlink_to("CLAUDE.md")

        with self.assertRaises(ValueError):
            service.track_and_render_workspace(workspace)

        self.assertNotIn(str(workspace.resolve()), service.state.tracked_workspaces)

    def test_track_workspace_requires_git_repository_root(self):
        service = self._engine()

        workspace = self.root / "workspace"
        workspace.mkdir()
        (workspace / "AGENTS.md").write_text("# Repo Overlay\n", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "git repository root"):
            service.track_and_render_workspace(workspace)

        self.assertNotIn(str(workspace.resolve()), service.state.tracked_workspaces)

    def test_cache_discovery_prefers_newest_version_directory(self):
        from src.agent_bootstrap.discovery import cache_version_dir, scan_cursor_cache

        package_root = self.cursor_cache / "delta"
        older = package_root / "aaa"
        newer = package_root / "zzz"
        older.mkdir(parents=True)
        newer.mkdir(parents=True)
        older.touch()
        newer.touch()

        self.assertEqual("zzz", cache_version_dir(self.cursor_cache, "delta").name)
        self.assertEqual("zzz", scan_cursor_cache(self.cursor_cache)["delta"].hash_value)

    def test_doctor_reports_workspace_agent_problems(self):
        service = self._engine()

        missing = self.root / "missing-workspace"
        service.track_workspace(missing)

        linked = self.root / "linked-workspace"
        linked.mkdir()
        (linked / ".git").mkdir()
        (linked / "CLAUDE.md").write_text("generated\n", encoding="utf-8")
        (linked / "AGENTS.md").symlink_to("CLAUDE.md")
        service.track_workspace(linked)

        generated = self.root / "generated-workspace"
        generated.mkdir()
        (generated / ".git").mkdir()
        (generated / "AGENTS.md").write_text(
            "<!-- Generated by agent_bootstrap. Edit canonical AGENTS.md files instead. -->\n",
            encoding="utf-8",
        )
        service.track_workspace(generated)

        issues = service.doctor_issues()
        messages = [issue.message for issue in issues]

        self.assertTrue(any("does not exist" in message for message in messages))
        self.assertTrue(any("symlink" in message for message in messages))
        self.assertTrue(any("looks generated" in message for message in messages))

    def test_doctor_reports_duplicate_mcp_ownership(self):
        from src.agent_bootstrap.paths import BootstrapPaths
        from src.agent_bootstrap.service import BootstrapService

        packages = {
            "packages": [
                {
                    "id": "alpha",
                    "display_name": "Alpha",
                    "origin": "internal",
                    "dedupe_group": "alpha",
                    "supported_surfaces": ["codex", "claude", "cursor"],
                    "mcp_keys": ["shared-mcp"],
                },
                {
                    "id": "beta",
                    "display_name": "Beta",
                    "origin": "internal",
                    "dedupe_group": "beta",
                    "supported_surfaces": ["codex", "claude"],
                    "mcp_keys": ["shared-mcp"],
                },
            ]
        }
        (self.root / "catalog" / "packages.json").write_text(
            json.dumps(packages, indent=2), encoding="utf-8"
        )

        paths = BootstrapPaths(
            root=self.root,
            cursor_plugin_cache=self.cursor_cache,
            codex_home=self.root / "home" / ".codex",
            claude_home=self.root / "home" / ".claude",
            cursor_home=self.root / "home" / ".cursor",
        )
        service = BootstrapService(paths)

        issues = service.doctor_issues()
        messages = [issue.message for issue in issues]

        self.assertTrue(any("shared-mcp" in message and "owned by multiple packages" in message for message in messages))

    def test_print_doctor_returns_nonzero_when_issues_exist(self):
        from src.agent_bootstrap.cli import print_doctor

        service = self._engine()
        missing = self.root / "missing-workspace"
        service.track_workspace(missing)

        with redirect_stdout(io.StringIO()):
            self.assertEqual(1, print_doctor(service))

    def test_agents_edit_audit_logs_canonical_instruction_changes(self):
        service = self._engine()

        service.record_instruction_change_audit()
        original_log = (self.root / "state" / "audit.log").read_text(encoding="utf-8")

        updated = "# Global Baseline\n\nChanged instructions.\n"
        (self.root / "global" / "AGENTS.md").write_text(updated, encoding="utf-8")

        service.record_instruction_change_audit()
        audit_log = (self.root / "state" / "audit.log").read_text(encoding="utf-8")

        self.assertIn("agents-changed", audit_log)
        self.assertNotEqual(original_log, audit_log)
        self.assertIn(hashlib.sha256(updated.encode("utf-8")).hexdigest(), audit_log)

    def test_menu_cursor_wraps_with_arrow_navigation(self):
        from src.agent_bootstrap.cli import move_cursor

        self.assertEqual(0, move_cursor(0, "up", 5))
        self.assertEqual(4, move_cursor(4, "down", 5))
        self.assertEqual(1, move_cursor(0, "down", 5))
        self.assertEqual(3, move_cursor(4, "up", 5))

    def test_workspace_menu_rows_include_actions(self):
        from src.agent_bootstrap.cli import resolve_workspace_target, workspace_menu_rows

        rows = workspace_menu_rows(
            ["/tmp/repo-one", "/tmp/repo-two"],
        )

        self.assertEqual("/tmp/repo-one", rows[0]["label"])
        self.assertEqual("/tmp/repo-two", rows[1]["label"])
        self.assertEqual("action:add", rows[2]["id"])
        self.assertEqual("action:remove", rows[3]["id"])
        self.assertEqual("action:back", rows[4]["id"])
        self.assertEqual("/tmp/repo-two", resolve_workspace_target(rows, 1, 0))
        self.assertEqual("/tmp/repo-two", resolve_workspace_target(rows, 3, 1))

    def test_package_menu_rows_show_local_and_repo_detection_independently(self):
        from src.agent_bootstrap.cli import package_menu_rows

        alpha_cache = self.cursor_cache / "alpha" / "hash999"
        alpha_cache.mkdir(parents=True)
        (alpha_cache / "README.md").write_text("alpha plugin", encoding="utf-8")

        service = self._engine()
        rows = {row["id"]: row["label"] for row in package_menu_rows(service)}

        self.assertIn("[M] [L] [R] [x] alpha", rows["package:alpha"])
        self.assertIn("[ ] [L] [ ] [ ] gamma", rows["package:gamma"])

    def test_package_action_rows_follow_package_state(self):
        from src.agent_bootstrap.cli import package_action_rows

        service = self._engine()
        rows = {row.package_id: row for row in service.build_overview().package_rows}

        managed_actions = package_action_rows(rows["alpha"])
        detected_actions = package_action_rows(rows["gamma"])

        self.assertEqual("action:toggle", managed_actions[0]["id"])
        self.assertIn("action:remove-managed", {row["id"] for row in managed_actions})
        self.assertNotIn("action:delete-local", {row["id"] for row in managed_actions})

        self.assertIn("action:import-local", {row["id"] for row in detected_actions})
        self.assertIn("action:delete-local", {row["id"] for row in detected_actions})

    def test_import_local_package_creates_managed_repo_copy(self):
        service = self._engine()

        service.import_from_local("gamma")

        overview = service.build_overview()
        rows = {row.package_id: row for row in overview.package_rows}
        catalog = json.loads((self.root / "catalog" / "packages.json").read_text(encoding="utf-8"))
        mcp = json.loads((self.root / "mcp" / "mcp.json").read_text(encoding="utf-8"))

        self.assertTrue(rows["gamma"].managed)
        self.assertTrue((self.root / "skills" / "gamma-plan" / "SKILL.md").exists())
        self.assertTrue((self.root / "rules" / "gamma-workflow.mdc").exists())
        self.assertTrue((self.root / "commands" / "gamma-triage.md").exists())
        self.assertTrue((self.root / "agents" / "gamma-helper.md").exists())
        self.assertTrue((self.root / "hooks" / "gamma").exists())
        self.assertIn("gamma-mcp", mcp["mcpServers"])
        self.assertIn("gamma", {item["id"] for item in catalog["packages"]})

    def test_remove_managed_package_clears_catalog_repo_and_mcp(self):
        service = self._engine()

        service.remove_managed_package("alpha")

        overview = service.build_overview()
        rows = {row.package_id: row for row in overview.package_rows}
        catalog = json.loads((self.root / "catalog" / "packages.json").read_text(encoding="utf-8"))
        mcp = json.loads((self.root / "mcp" / "mcp.json").read_text(encoding="utf-8"))

        self.assertNotIn("alpha", {item["id"] for item in catalog["packages"]})
        self.assertFalse((self.root / "skills" / "alpha-skill").exists())
        self.assertNotIn("alpha-mcp", mcp["mcpServers"])
        self.assertNotIn("alpha", rows)

    def test_delete_local_package_removes_cache_detection(self):
        service = self._engine()

        service.delete_local_package("gamma")

        overview = service.build_overview()
        rows = {row.package_id: row for row in overview.package_rows}

        self.assertFalse((self.cursor_cache / "gamma").exists())
        self.assertNotIn("gamma", rows)


if __name__ == "__main__":
    unittest.main()
