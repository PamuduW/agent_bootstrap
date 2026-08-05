from __future__ import annotations

import json
import re
import stat
from dataclasses import replace
from pathlib import Path
from typing import Callable, Mapping

from .claude_bridge import bridge_claude_skills as link_claude_skills
from .claude_statusline import doctor_claude_statusline, inspect_claude_statusline
from .graphify import GraphifyIntegration, GraphifyStatus
from .models import DoctorIssue
from .paths import AgentbotPaths
from .render import installed_skill_dirs, managed_skill_names, render_global_outputs, resync_global_outputs
from .skills_installer import (
    InstallResult,
    SkillsUpdateReport,
    doctor_skills,
    install_skills as run_skills_install,
    list_installed_skills,
    parse_update_output,
    update_skills as run_skills_update,
)
from .skills_sources import load_skills_sources
from .skill_reconcile import (
    ReconcileResult,
    apply_reconcile_plan,
    build_reconcile_plan,
)
from .ui import (
    print_bridge_summary,
    print_doctor_summary,
    print_graphify_status,
    print_header,
    print_skills_report,
)
from .workspace_service import WorkspaceReport, WorkspaceResult, WorkspaceService
from .workspace_state import WorkspaceRecord


class AgentbotService:
    def __init__(self, paths: AgentbotPaths) -> None:
        self.paths = paths
        self.workspace_service = WorkspaceService(paths)

    def render_global(self) -> None:
        render_global_outputs(self.paths)

    def install_skills(self) -> list:
        return run_skills_install(self.paths)

    def apply_claude_bridge(self, *, print_summary: bool = True) -> tuple[int, int, int]:
        bridge = link_claude_skills(
            agents_home=self.paths.agents_skills_home,
            claude_home=self.paths.claude_skills_home,
        )
        already = sum(1 for action in bridge.actions if action.action == "already_linked")
        updated = sum(1 for action in bridge.actions if action.action == "updated")
        linked = sum(1 for action in bridge.actions if action.action == "linked")
        skipped = sum(1 for action in bridge.actions if action.action == "skip_existing")
        linked_total = already + linked
        if print_summary:
            print_bridge_summary(linked=linked_total, skipped=skipped, updated=updated)
        return linked_total, skipped, updated

    def run_bootstrap(self) -> int:
        print_header("Install Agentbot", "Agentbot › Install Agentbot")
        results = run_skills_install(self.paths)
        skills_rc = print_skills_report(results, title="Skills install")
        graphify_status = self.sync_graphify_if_cli_available(refresh_outputs=False)
        self.refresh_agent_outputs()
        if graphify_status.cli_path is not None or graphify_status.state == "broken":
            print_graphify_status(graphify_status)
        issues = self.doctor_issues() + self.skills_doctor_issues()
        doctor_rc = print_doctor_summary(issues)
        if skills_rc != 0:
            return skills_rc
        if graphify_status.state == "broken":
            return 1
        return doctor_rc

    def update_skills(self) -> InstallResult:
        return run_skills_update(self.paths)

    def preview_workspace(
        self,
        path: Path,
        *,
        profile: str | None,
        targets: tuple[str, ...] | None,
    ) -> WorkspaceResult:
        return self.workspace_service.preview(
            path,
            profile_name=profile,
            targets=targets,
        )

    def apply_workspace(
        self,
        path: Path,
        *,
        profile: str | None,
        targets: tuple[str, ...] | None,
        register: bool,
    ) -> WorkspaceResult:
        return self.workspace_service.apply(
            path,
            profile_name=profile,
            targets=targets,
            register=register,
        )

    def resync_workspaces(
        self,
        *,
        apply: bool,
        paths: tuple[Path, ...] = (),
    ) -> WorkspaceReport:
        report = self.workspace_service.resync(apply=apply, paths=paths)
        global_actions = resync_global_outputs(self.paths, apply=apply)
        return WorkspaceReport(results=report.results, global_actions=global_actions)

    def list_workspaces(self) -> tuple[WorkspaceRecord, ...]:
        return self.workspace_service.store.load()

    def remove_workspace(self, path: Path) -> WorkspaceRecord:
        return self.workspace_service.remove(path)

    def reconcile_skills(
        self,
        *,
        discovered: Mapping[str, list[str] | tuple[str, ...]] | None = None,
        checkouts: Mapping[str, Path] | None = None,
        confirm: bool | Callable = False,
        dry_run: bool = False,
        validate: Callable[[], None] | None = None,
    ) -> ReconcileResult:
        config = load_skills_sources(self.paths.skills_sources_file)
        lock: dict = {}
        if self.paths.global_skill_lock.exists():
            lock = json.loads(self.paths.global_skill_lock.read_text(encoding="utf-8"))
        if discovered is None:
            installed = set(self.list_skills())
            discovered = {}
            for source in config.active_sources():
                if source.skills == ["*"]:
                    owned = {
                        name
                        for name, entry in lock.get("skills", {}).items()
                        if isinstance(entry, dict) and entry.get("source") == source.repo and name in installed
                    }
                    discovered[source.id] = sorted(owned)
                else:
                    discovered[source.id] = sorted(installed & set(source.skills))
        plan = build_reconcile_plan(config, discovered=discovered, lock=lock)
        return apply_reconcile_plan(
            self.paths,
            config,
            plan,
            checkouts=checkouts,
            confirm=confirm,
            dry_run=dry_run,
            validate=validate,
        )

    def _installed_skill_catalog(self, config, lock: dict) -> dict[str, list[str]]:
        installed = set(self.list_skills())
        catalog: dict[str, list[str]] = {}
        for source in config.active_sources():
            if source.skills == ["*"]:
                owned = {
                    name
                    for name, entry in lock.get("skills", {}).items()
                    if isinstance(entry, dict) and entry.get("source") == source.repo and name in installed
                }
                catalog[source.id] = sorted(owned)
            else:
                catalog[source.id] = sorted(installed & set(source.skills))
        return catalog

    def _catalog_after_upstream_deletions(self, report: SkillsUpdateReport):
        if not report.deleted_by_source:
            return None

        config = load_skills_sources(self.paths.skills_sources_file)
        lock: dict = {}
        if self.paths.global_skill_lock.exists():
            lock = json.loads(self.paths.global_skill_lock.read_text(encoding="utf-8"))
        catalog = self._installed_skill_catalog(config, lock)
        for source_label, deleted_skills in report.deleted_by_source:
            source = next(
                (
                    candidate
                    for candidate in config.active_sources()
                    if candidate.id == source_label or candidate.repo == source_label
                ),
                None,
            )
            if source is None:
                continue
            deleted = set(deleted_skills)
            catalog[source.id] = [
                skill for skill in catalog.get(source.id, ()) if skill not in deleted
            ]
        return catalog

    @staticmethod
    def _confirm_reported_upstream_deletions(report: SkillsUpdateReport):
        reported = set(report.deleted_skills)

        def confirm(plan) -> bool:
            removed = set(plan.wildcard_removals) | {
                change.skill
                for change in plan.manifest_changes
                if change.action == "remove"
            }
            return bool(removed) and not plan.wildcard_additions and removed <= reported

        return confirm

    def run_reconciliation_update(self, *, dry_run: bool = False, confirm: bool = False) -> ReconcileResult:
        """Refresh upstream pins, reconcile skills, then resync workspaces + global outputs."""
        update_report = SkillsUpdateReport()
        discovered = None
        graphify_preview = self.graphify_status() if dry_run else None
        if not dry_run:
            update_result = self.update_skills()
            update_report = parse_update_output(update_result.stdout, update_result.stderr)
            discovered = self._catalog_after_upstream_deletions(update_report)
        def validate() -> None:
            errors = [
                issue for issue in self.doctor_issues() + self.skills_doctor_issues()
                if issue.level.lower() == "error"
            ]
            if errors:
                raise RuntimeError(
                    "post-reconciliation doctor found errors: "
                    + "; ".join(issue.message for issue in errors)
                )

        reconcile_confirm: bool | Callable = confirm
        if not confirm and update_report.deleted_by_source:
            reconcile_confirm = self._confirm_reported_upstream_deletions(update_report)
        result = self.reconcile_skills(
            discovered=discovered,
            confirm=reconcile_confirm,
            dry_run=dry_run,
            validate=None if dry_run else validate,
        )
        if graphify_preview is not None:
            preview_message = self._graphify_update_preview_message(graphify_preview)
            message = f"{result.message}; {preview_message}" if result.message else preview_message
            result = replace(result, message=message)

        workspace_report = None
        graphify_status = None
        if dry_run or result.status in {"applied", "applied-with-local-changes"}:
            if result.status in {"applied", "applied-with-local-changes"}:
                graphify_status = self.sync_graphify_if_cli_available(
                    refresh_outputs=False
                )
            # Preview or apply registered workspaces plus managed global outputs.
            workspace_report = self.resync_workspaces(apply=not dry_run)

        message = result.message
        if workspace_report is not None:
            surface_message = self._workspace_resync_summary(workspace_report, dry_run=dry_run)
            message = f"{message}; {surface_message}" if message else surface_message
        result_status = result.status
        if graphify_status is not None and graphify_status.state == "broken":
            detail = f"Graphify: {graphify_status.message}"
            message = f"{message}; {detail}" if message else detail
            result_status = "failed"
        elif (
            graphify_status is not None
            and graphify_status.skill_path.is_file()
            and graphify_status.state != "ready"
        ):
            detail = f"Graphify: {graphify_status.message}"
            message = f"{message}; {detail}" if message else detail
        return replace(
            result,
            status=result_status,
            updated_skills=update_report.updated_skills,
            message=message,
            workspace_report=workspace_report,
        )

    @staticmethod
    def _workspace_resync_summary(report, *, dry_run: bool) -> str:
        mutating_kinds = {"create", "update"}
        workspace_count = sum(
            1
            for result in report.results
            if any(action.kind in mutating_kinds for action in result.actions)
        )
        global_count = sum(
            1
            for action in (getattr(report, "global_actions", ()) or ())
            if action.kind in mutating_kinds
        )
        verb = "would refresh" if dry_run else "refreshed"
        return (
            f"surfaces: {verb} {workspace_count} workspace(s) and "
            f"{global_count} global output(s)"
        )
    @staticmethod
    def _graphify_update_preview_message(status: GraphifyStatus) -> str:
        if status.cli_path is None:
            return "Graphify: CLI is not installed; integration would be skipped."
        if not status.skill_path.is_file():
            return (
                "Graphify: the generic Agent Skills integration would be set up "
                "after reconciliation."
            )
        return (
            "Graphify: the generic Agent Skills integration would be refreshed "
            "after reconciliation."
        )

    def refresh_agent_outputs(self) -> tuple[int, int, int]:
        linked, skipped, updated = self.apply_claude_bridge(print_summary=False)
        self.render_global()
        return linked, skipped, updated

    def graphify_status(self) -> GraphifyStatus:
        return GraphifyIntegration(self.paths).status()

    def setup_graphify(self) -> GraphifyStatus:
        status = GraphifyIntegration(self.paths).setup()
        if status.cli_path is not None and status.skill_path.is_file() and status.state != "broken":
            self.refresh_agent_outputs()
            return GraphifyIntegration(self.paths).status()
        return status

    def sync_graphify_if_cli_available(
        self, *, refresh_outputs: bool = True
    ) -> GraphifyStatus:
        integration = GraphifyIntegration(self.paths)
        current = integration.status()
        if current.cli_path is None:
            return current
        status = integration.setup()
        if (
            refresh_outputs
            and status.skill_path.is_file()
            and status.state != "broken"
        ):
            self.refresh_agent_outputs()
        return status

    def list_skills(self) -> list[str]:
        return list_installed_skills(self.paths)

    def skills_doctor_issues(self) -> list[DoctorIssue]:
        return doctor_skills(self.paths)

    def doctor_issues(self) -> list[DoctorIssue]:
        issues: list[DoctorIssue] = []

        issues.extend(self._token_doctor_issues())

        if not self.paths.global_agents.exists():
            issues.append(
                DoctorIssue(
                    level="error",
                    scope="global",
                    message=f"Missing global baseline: {self.paths.global_agents}",
                )
            )

        if not self.paths.skills_sources_file.exists():
            issues.append(
                DoctorIssue(
                    level="error",
                    scope="skills",
                    message=f"Missing skills manifest: {self.paths.skills_sources_file}",
                )
            )

        issues.extend(doctor_claude_statusline(self.paths))

        managed_names = managed_skill_names(self.paths)
        declared_names = self._manifest_declared_skill_names()
        managed_dirs = {skill_dir.name: skill_dir for skill_dir in installed_skill_dirs(self.paths)}
        codex_skills = self.paths.codex_home / "skills"
        graphify = GraphifyIntegration(self.paths)
        graphify_status = self.graphify_status()
        graphify_official = graphify.version_path.is_file()

        if graphify_official and graphify_status.state != "ready":
            level = "error" if graphify_status.state == "broken" else "warning"
            issues.append(
                DoctorIssue(
                    level=level,
                    scope="graphify",
                    message=self._graphify_doctor_message(graphify_status),
                )
            )

        for name in managed_names:
            source = self.paths.agents_skills_home / name
            if name not in managed_dirs:
                issues.append(
                    DoctorIssue(
                        level="error",
                        scope="skills",
                        message=f"Managed skill {name!r} is missing from {source}",
                    )
                )
                continue

            target = codex_skills / name
            if not target.is_symlink() or not target.exists():
                issues.append(
                    DoctorIssue(
                        level="error",
                        scope="codex",
                        message=f"Managed Codex skill link for {name!r} is missing or broken: {target}",
                    )
                )
            elif target.resolve() != source.resolve():
                issues.append(
                    DoctorIssue(
                        level="warning",
                        scope="codex",
                        message=f"Managed Codex skill link for {name!r} points outside the managed source: {target}",
                    )
                )

        if self.paths.agents_skills_home.is_dir():
            for source in self._unmanaged_skill_dirs(managed_names, declared_names):
                target = codex_skills / source.name
                if not target.is_symlink() or not target.exists() or target.resolve() != source.resolve():
                    issues.append(
                        DoctorIssue(
                            level="warning",
                            scope="reproducibility",
                            message=(
                                f"Manual skill {source.name!r} is outside managed sources and has no Codex link yet; "
                                "run './install.sh global' to make the local skill available, then add a source to make it reproducible"
                            ),
                        )
                    )
                else:
                    issues.append(
                        DoctorIssue(
                            level="warning",
                            scope="reproducibility",
                            message=(
                                f"Manual skill {source.name!r} is available to Codex but outside managed sources; "
                                "add a manifest source to make it reproducible"
                            ),
                        )
                    )

        return issues

    def _unmanaged_skill_dirs(
        self,
        managed_names: set[str],
        declared_names: set[str],
    ) -> tuple[Path, ...]:
        if not self.paths.agents_skills_home.is_dir():
            return ()
        unmanaged: list[Path] = []
        for source in sorted(self.paths.agents_skills_home.iterdir()):
            if (
                not source.is_dir()
                or not (source / "SKILL.md").is_file()
                or source.name in managed_names
                or source.name in declared_names
            ):
                continue
            if source.name == "graphify" and (source / ".graphify_version").is_file():
                continue
            unmanaged.append(source)
        return tuple(unmanaged)

    @staticmethod
    def _graphify_doctor_message(status: GraphifyStatus) -> str:
        if status.state == "skill-without-cli":
            return (
                f"{status.message} Install it through Dotfiles or run: uv tool install graphifyy"
            )
        if status.state == "stale":
            return f"{status.message} Run `agentbot graphify setup` to refresh the skill."
        if status.state == "conflict":
            targets = [
                label
                for label, target_state in (("Codex", status.codex_state), ("Claude", status.claude_state))
                if target_state == "conflict"
            ]
            target_text = ", ".join(targets) or "an assistant"
            return f"{status.message} Preserved conflicting {target_text} target(s)."
        return status.message

    def _manifest_declared_skill_names(self) -> set[str]:
        """Return explicit manifest names before lock provenance is applied.

        A stale global lock must not make a skill that is explicitly declared
        in the manifest look like an unrelated manual install. The skills
        doctor separately reports the missing lock entry, so this prevents
        duplicate and misleading warnings without hiding the real drift.
        Wildcard sources are intentionally excluded because their membership is
        only knowable from the successful lock/install result.
        """
        try:
            config = load_skills_sources(self.paths.skills_sources_file)
        except (OSError, ValueError):
            return set()
        return {
            skill
            for source in config.active_sources()
            for skill in source.skills
            if skill != "*"
        }

    def _token_doctor_issues(self) -> list[DoctorIssue]:
        """Report unsafe optional token state without reading or printing its value."""
        token_file = self.paths.config_home / "github.env"
        if not token_file.exists() and not token_file.is_symlink():
            return []
        if token_file.is_symlink() or not token_file.is_file():
            return [DoctorIssue("warning", "token", f"saved GitHub token path is not a regular file: {token_file}")]
        try:
            mode = stat.S_IMODE(token_file.stat().st_mode)
            content = token_file.read_text(encoding="utf-8")
        except OSError as error:
            return [DoctorIssue("warning", "token", f"saved GitHub token cannot be read: {error}")]
        if mode != 0o600:
            return [DoctorIssue("warning", "token", f"saved GitHub token must have mode 600: {token_file}")]
        lines = content.splitlines(keepends=True)
        if len(lines) != 1 or not lines[0].endswith("\n") or not lines[0].startswith("GITHUB_TOKEN="):
            return [DoctorIssue("warning", "token", "saved GitHub token has malformed assignment")]
        value = lines[0][len("GITHUB_TOKEN=") : -1]
        if len(value) < 20 or re.fullmatch(r"[A-Za-z0-9_]+", value) is None:
            return [DoctorIssue("warning", "token", "saved GitHub token has an invalid value")]
        return []

    def status_summary(self) -> dict[str, object]:
        enabled_sources = 0
        if self.paths.skills_sources_file.exists():
            try:
                config = load_skills_sources(self.paths.skills_sources_file)
                enabled_sources = sum(
                    1
                    for source in config.sources
                    if source.enabled and source.repo and source.skills
                )
            except ValueError:
                enabled_sources = -1

        global_lock_skills = self._count_global_lock_skills(self.paths)
        managed_names = set(managed_skill_names(self.paths))
        declared_names = self._manifest_declared_skill_names()
        claude_bridge_links = 0
        if self.paths.claude_skills_home.is_dir():
            claude_bridge_links = sum(
                1 for entry in self.paths.claude_skills_home.iterdir() if entry.is_symlink()
            )

        doctor_issues = self.doctor_issues() + self.skills_doctor_issues()
        statusline = inspect_claude_statusline(self.paths)

        return {
            "installed_skills": len(self.list_skills()),
            "enabled_sources": enabled_sources,
            "global_agents_exists": self.paths.global_agents.exists(),
            "skills_sources_exists": self.paths.skills_sources_file.exists(),
            "global_lock_exists": self.paths.global_skill_lock.exists(),
            "global_lock_skills": global_lock_skills,
            "managed_skill_count": len(managed_names),
            "manual_skill_count": len(self._unmanaged_skill_dirs(managed_names, declared_names)),
            "claude_bridge_links": claude_bridge_links,
            "claude_statusline_state": statusline.status_label,
            "doctor_issue_count": len(doctor_issues),
        }

    @staticmethod
    def _count_global_lock_skills(paths: AgentbotPaths) -> int:
        lock_path = paths.global_skill_lock
        if not lock_path.exists():
            return 0
        try:
            data = json.loads(lock_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return -1
        if not isinstance(data, dict):
            return -1
        skills = data.get("skills")
        if isinstance(skills, dict):
            return len(skills)
        if isinstance(skills, list):
            return len(skills)
        return 0
