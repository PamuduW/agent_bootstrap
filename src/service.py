from __future__ import annotations

import json
import re
import stat
from pathlib import Path
from typing import Callable, Mapping

from .claude_bridge import bridge_claude_skills as link_claude_skills
from .models import DoctorIssue
from .paths import AgentbotPaths
from .render import installed_skill_dirs, managed_skill_names, render_global_outputs
from .skills_installer import (
    doctor_skills,
    install_skills as run_skills_install,
    list_installed_skills,
    update_skills as run_skills_update,
)
from .skills_sources import load_skills_sources
from .skill_reconcile import (
    ReconcileResult,
    apply_reconcile_plan,
    build_reconcile_plan,
)
from .ui import print_bridge_summary, print_doctor_summary, print_header, print_skills_report
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
        self.refresh_agent_outputs()
        issues = self.doctor_issues() + self.skills_doctor_issues()
        doctor_rc = print_doctor_summary(issues)
        if skills_rc != 0:
            return skills_rc
        return doctor_rc

    def update_skills(self) -> None:
        run_skills_update(self.paths)

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
        return self.workspace_service.resync(apply=apply, paths=paths)

    def list_workspaces(self) -> tuple[WorkspaceRecord, ...]:
        return self.workspace_service.store.load()

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

    def run_reconciliation_update(self, *, dry_run: bool = False, confirm: bool = False) -> ReconcileResult:
        """Refresh upstream pins, then reconcile source-owned runtime state."""
        if not dry_run:
            self.update_skills()
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

        result = self.reconcile_skills(
            confirm=confirm,
            dry_run=dry_run,
            validate=None if dry_run else validate,
        )
        if result.status in {"applied", "applied-with-local-changes"}:
            self.refresh_agent_outputs()
        return result

    def refresh_agent_outputs(self) -> tuple[int, int, int]:
        linked, skipped, updated = self.apply_claude_bridge(print_summary=False)
        self.render_global()
        return linked, skipped, updated

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

        managed_names = managed_skill_names(self.paths)
        declared_names = self._manifest_declared_skill_names()
        managed_dirs = {skill_dir.name: skill_dir for skill_dir in installed_skill_dirs(self.paths)}
        codex_skills = self.paths.codex_home / "skills"

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
            for source in sorted(self.paths.agents_skills_home.iterdir()):
                if (
                    not source.is_dir()
                    or not (source / "SKILL.md").is_file()
                    or source.name in managed_names
                    or source.name in declared_names
                ):
                    continue
                target = codex_skills / source.name
                if not target.is_symlink() or not target.exists() or target.resolve() != source.resolve():
                    issues.append(
                        DoctorIssue(
                            level="warning",
                            scope="reproducibility",
                            message=(
                                f"Manual skill {source.name!r} is outside the global lock and has no Codex link yet; "
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
                                f"Manual skill {source.name!r} is available to Codex but outside the global lock; "
                                "add a manifest source to make it reproducible"
                            ),
                        )
                    )

        return issues

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
        local_names = {skill_dir.name for skill_dir in installed_skill_dirs(self.paths)}
        claude_bridge_links = 0
        if self.paths.claude_skills_home.is_dir():
            claude_bridge_links = sum(
                1 for entry in self.paths.claude_skills_home.iterdir() if entry.is_symlink()
            )

        doctor_issues = self.doctor_issues() + self.skills_doctor_issues()

        return {
            "installed_skills": len(self.list_skills()),
            "enabled_sources": enabled_sources,
            "global_agents_exists": self.paths.global_agents.exists(),
            "skills_sources_exists": self.paths.skills_sources_file.exists(),
            "global_lock_exists": self.paths.global_skill_lock.exists(),
            "global_lock_skills": global_lock_skills,
            "managed_skill_count": len(managed_names),
            "manual_skill_count": len(local_names - managed_names),
            "claude_bridge_links": claude_bridge_links,
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
