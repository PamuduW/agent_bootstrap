from __future__ import annotations

import json
from pathlib import Path

from .claude_bridge import bridge_claude_skills as link_claude_skills
from .models import DoctorIssue
from .paths import BootstrapPaths
from .render import installed_skill_dirs, managed_skill_names, render_global_outputs
from .skills_installer import (
    doctor_skills,
    install_skills as run_skills_install,
    list_installed_skills,
    update_skills as run_skills_update,
)
from .skills_sources import load_skills_sources
from .ui import print_bridge_summary, print_doctor_summary, print_header, print_skills_report


class BootstrapService:
    def __init__(self, paths: BootstrapPaths) -> None:
        self.paths = paths

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
        print_header("Bootstrap", str(self.paths.root))
        results = run_skills_install(self.paths)
        skills_rc = print_skills_report(results, title="Skills install")
        self.apply_claude_bridge()
        self.render_global()
        issues = self.doctor_issues() + self.skills_doctor_issues()
        doctor_rc = print_doctor_summary(issues)
        if skills_rc != 0:
            return skills_rc
        return doctor_rc

    def update_skills(self) -> None:
        run_skills_update(self.paths)

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
                if not source.is_dir() or not (source / "SKILL.md").is_file() or source.name in managed_names:
                    continue
                target = codex_skills / source.name
                if not target.is_symlink() or not target.exists() or target.resolve() != source.resolve():
                    issues.append(
                        DoctorIssue(
                            level="warning",
                            scope="codex",
                            message=(
                                f"Manual skill {source.name!r} is not linked into Codex; a copied folder is not a managed "
                                "install. Add it through a skill source or create and maintain an explicit link."
                            ),
                        )
                    )

        return issues

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
            "claude_bridge_links": claude_bridge_links,
            "doctor_issue_count": len(doctor_issues),
        }

    @staticmethod
    def _count_global_lock_skills(paths: BootstrapPaths) -> int:
        lock_path = paths.global_skill_lock
        if not lock_path.exists():
            return 0
        try:
            data = json.loads(lock_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return -1
        skills = data.get("skills")
        if isinstance(skills, dict):
            return len(skills)
        if isinstance(skills, list):
            return len(skills)
        return 0
