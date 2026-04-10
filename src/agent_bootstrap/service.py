from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from .catalog import load_catalog, save_catalog
from .discovery import cache_version_dir, merge_discovery, scan_cursor_cache, scan_managed_packages
from .models import ArtifactSummary, Overview, PackageCatalogEntry, PackageRow
from .paths import BootstrapPaths
from .render import render_global_outputs, render_workspace_outputs
from .state import StateSnapshot, append_audit, load_state, save_state


class BootstrapService:
    def __init__(self, paths: BootstrapPaths) -> None:
        self.paths = paths
        self.catalog = load_catalog(paths.catalog_file)
        self.state = self._load_state()

    def build_overview(self) -> Overview:
        discovery = self._discovery()
        package_ids = sorted(set(self.catalog.keys()) | set(discovery.keys()))
        rows = []
        for package_id in package_ids:
            catalog_entry = self.catalog.get(package_id)
            record = discovery.get(package_id)
            enabled = self._is_enabled(package_id, catalog_entry is not None)
            rows.append(
                PackageRow(
                    package_id=package_id,
                    display_name=catalog_entry.display_name if catalog_entry else package_id,
                    managed=catalog_entry is not None,
                    detected_local=record.detected_local if record else False,
                    detected_repo=record.detected_repo if record else False,
                    enabled=enabled,
                    applied=enabled and (catalog_entry is not None),
                    source=record.source if record else (catalog_entry.origin if catalog_entry else "unknown"),
                    artifacts=record.artifact_summary if record else ArtifactSummary(),
                    mcp_keys=catalog_entry.mcp_keys if catalog_entry else [],
                )
            )
        return Overview(package_rows=rows)

    def set_package_enabled(self, package_id: str, enabled: bool) -> None:
        self.state.enabled_packages[package_id] = enabled
        save_state(self.paths.state_file, self.state)
        append_audit(self.paths.audit_log, "package-selection", f"{package_id}={enabled}")

    def import_from_local(self, package_id: str) -> None:
        cache_dir = cache_version_dir(self.paths.cursor_plugin_cache, package_id)
        if cache_dir is None:
            raise ValueError(f"Local package not found: {package_id}")

        self._copy_cache_artifacts(package_id, cache_dir)
        mcp_keys = self._merge_mcp_from_cache(cache_dir)
        entry = self.catalog.get(package_id)
        if entry is None:
            entry = PackageCatalogEntry(
                id=package_id,
                display_name=package_id.replace("-", " ").title(),
                origin="cursor-cache-import",
                dedupe_group=package_id,
                supported_surfaces=["codex", "claude", "cursor", "copilot"],
                mcp_keys=mcp_keys,
            )
        else:
            entry = PackageCatalogEntry(
                id=entry.id,
                display_name=entry.display_name,
                origin=entry.origin,
                dedupe_group=entry.dedupe_group,
                supported_surfaces=entry.supported_surfaces,
                mcp_keys=sorted(set(entry.mcp_keys) | set(mcp_keys)),
            )
        self.catalog[package_id] = entry
        self.state.enabled_packages[package_id] = True
        save_catalog(self.paths.catalog_file, self.catalog)
        save_state(self.paths.state_file, self.state)
        append_audit(self.paths.audit_log, "package-import", f"{package_id} from {cache_dir}")

    def remove_managed_package(self, package_id: str) -> None:
        entry = self.catalog.pop(package_id, None)
        if entry is None:
            return

        self._remove_repo_artifacts(package_id)
        if entry.mcp_keys:
            self._remove_mcp_keys(entry.mcp_keys)
        self.state.enabled_packages.pop(package_id, None)
        save_catalog(self.paths.catalog_file, self.catalog)
        save_state(self.paths.state_file, self.state)
        append_audit(self.paths.audit_log, "package-remove-managed", package_id)

    def delete_local_package(self, package_id: str) -> None:
        plugin_dir = self.paths.cursor_plugin_cache / package_id
        if plugin_dir.exists():
            shutil.rmtree(plugin_dir)
            append_audit(self.paths.audit_log, "package-delete-local", package_id)

    def render_workspace(self, workspace: Path) -> None:
        self.record_instruction_change_audit()
        discovery = self._discovery()
        render_workspace_outputs(
            self.paths,
            workspace,
            self.enabled_package_ids(discovery.keys()),
            self.catalog,
            discovery,
        )
        append_audit(self.paths.audit_log, "render-workspace", str(workspace))

    def render_global(self) -> None:
        self.record_instruction_change_audit()
        render_global_outputs(self.paths, self.enabled_package_ids(self.catalog.keys()), self.catalog)
        append_audit(self.paths.audit_log, "render-global", str(self.paths.root))

    def enabled_package_ids(self, package_ids) -> list[str]:
        return sorted(package_id for package_id in package_ids if self._is_enabled(package_id, package_id in self.catalog))

    def track_workspace(self, workspace: Path) -> None:
        resolved = str(workspace.resolve())
        if resolved not in self.state.tracked_workspaces:
            self.state.tracked_workspaces.append(resolved)
            self.state.tracked_workspaces.sort()
            save_state(self.paths.state_file, self.state)
            append_audit(self.paths.audit_log, "workspace-add", resolved)

    def untrack_workspace(self, workspace: Path) -> None:
        resolved = str(workspace.resolve())
        if resolved in self.state.tracked_workspaces:
            self.state.tracked_workspaces.remove(resolved)
            save_state(self.paths.state_file, self.state)
            append_audit(self.paths.audit_log, "workspace-remove", resolved)

    def apply_all(self) -> None:
        self.render_global()
        for workspace in self.state.tracked_workspaces:
            self.render_workspace(Path(workspace))

    def record_instruction_change_audit(self) -> None:
        candidates = [self.paths.global_agents]
        candidates.extend(Path(path) / "AGENTS.md" for path in self.state.tracked_workspaces)

        changed = False
        for agents_file in candidates:
            if not agents_file.exists():
                continue
            digest = hashlib.sha256(agents_file.read_bytes()).hexdigest()
            key = str(agents_file.resolve())
            previous = self.state.instruction_hashes.get(key)
            if previous is None:
                self.state.instruction_hashes[key] = digest
                changed = True
                append_audit(self.paths.audit_log, "agents-baseline", f"{key} {digest}")
                continue
            if previous != digest:
                self.state.instruction_hashes[key] = digest
                changed = True
                append_audit(self.paths.audit_log, "agents-changed", f"{key} {digest}")

        if changed:
            save_state(self.paths.state_file, self.state)

    def _discovery(self):
        return merge_discovery(
            scan_managed_packages(self.paths.root, self.catalog),
            scan_cursor_cache(self.paths.cursor_plugin_cache),
        )

    def _load_state(self) -> StateSnapshot:
        state = load_state(self.paths.state_file)
        for package_id in self.catalog:
            state.enabled_packages.setdefault(package_id, True)
        return state

    def _is_enabled(self, package_id: str, managed_default: bool) -> bool:
        if package_id in self.state.enabled_packages:
            return self.state.enabled_packages[package_id]
        return managed_default

    def _copy_cache_artifacts(self, package_id: str, cache_dir: Path) -> None:
        self.paths.skills_dir.mkdir(parents=True, exist_ok=True)
        self.paths.rules_dir.mkdir(parents=True, exist_ok=True)
        self.paths.commands_dir.mkdir(parents=True, exist_ok=True)
        self.paths.agents_dir.mkdir(parents=True, exist_ok=True)
        self.paths.hooks_dir.mkdir(parents=True, exist_ok=True)

        def replace_dir(source: Path, target: Path) -> None:
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(source, target)

        for skill_dir in sorted((cache_dir / "skills").glob("*")) if (cache_dir / "skills").exists() else []:
            if skill_dir.is_dir():
                replace_dir(skill_dir, self.paths.skills_dir / f"{package_id}-{skill_dir.name}")

        for rule_file in sorted((cache_dir / "rules").glob("*.mdc")) if (cache_dir / "rules").exists() else []:
            shutil.copy2(rule_file, self.paths.rules_dir / f"{package_id}-{rule_file.name}")

        for command_file in sorted((cache_dir / "commands").glob("*.md")) if (cache_dir / "commands").exists() else []:
            shutil.copy2(command_file, self.paths.commands_dir / f"{package_id}-{command_file.name}")

        for agent_file in sorted((cache_dir / "agents").glob("*.md")) if (cache_dir / "agents").exists() else []:
            shutil.copy2(agent_file, self.paths.agents_dir / f"{package_id}-{agent_file.name}")

        hooks_dir = cache_dir / "hooks"
        if hooks_dir.exists():
            target = self.paths.hooks_dir / package_id
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(hooks_dir, target)

    def _merge_mcp_from_cache(self, cache_dir: Path) -> list[str]:
        mcp_file = None
        for candidate in (cache_dir / ".mcp.json", cache_dir / "mcp.json"):
            if candidate.exists():
                mcp_file = candidate
                break
        if mcp_file is None:
            return []

        source = json.loads(mcp_file.read_text(encoding="utf-8"))
        source_servers = source.get("mcpServers", source)

        repo_payload = {"mcpServers": {}}
        if self.paths.mcp_catalog.exists():
            repo_payload = json.loads(self.paths.mcp_catalog.read_text(encoding="utf-8"))
        repo_servers = repo_payload.setdefault("mcpServers", {})
        repo_servers.update(source_servers)
        self.paths.mcp_catalog.write_text(json.dumps(repo_payload, indent=2) + "\n", encoding="utf-8")
        return sorted(source_servers.keys())

    def _remove_mcp_keys(self, keys: list[str]) -> None:
        if not self.paths.mcp_catalog.exists():
            return
        payload = json.loads(self.paths.mcp_catalog.read_text(encoding="utf-8"))
        servers = payload.setdefault("mcpServers", {})
        for key in keys:
            servers.pop(key, None)
        self.paths.mcp_catalog.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def _remove_repo_artifacts(self, package_id: str) -> None:
        for skill_dir in self.paths.skills_dir.glob(f"{package_id}-*"):
            if skill_dir.is_dir():
                shutil.rmtree(skill_dir)

        for base, pattern in (
            (self.paths.rules_dir, f"{package_id}-*.mdc"),
            (self.paths.commands_dir, f"{package_id}-*.md"),
            (self.paths.agents_dir, f"{package_id}-*.md"),
        ):
            for file_path in base.glob(pattern):
                if file_path.is_file():
                    file_path.unlink()

        hooks_dir = self.paths.hooks_dir / package_id
        if hooks_dir.exists():
            shutil.rmtree(hooks_dir)
