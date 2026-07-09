from __future__ import annotations

from pathlib import Path

from .claude_bridge import bridge_claude_skills as link_claude_skills
from .models import DoctorIssue
from .paths import BootstrapPaths
from .render import render_global_outputs
from .skills_installer import (
    doctor_skills,
    install_skills as run_skills_install,
    list_installed_skills,
    update_skills as run_skills_update,
)
from .ui import print_bridge_summary, print_doctor_summary, print_header, print_skills_report


class BootstrapService:
    def __init__(self, paths: BootstrapPaths) -> None:
        self.paths = paths

    def render_global(self) -> None:
        render_global_outputs(self.paths)

    def install_skills(self) -> list:
        return run_skills_install(self.paths)

    def apply_claude_bridge(self) -> None:
        bridge = link_claude_skills(
            agents_home=self.paths.agents_skills_home,
            claude_home=self.paths.claude_skills_home,
        )
        already = sum(1 for action in bridge.actions if action.action == "already_linked")
        updated = sum(1 for action in bridge.actions if action.action == "updated")
        linked = sum(1 for action in bridge.actions if action.action == "linked")
        skipped = sum(1 for action in bridge.actions if action.action == "skip_existing")
        print_bridge_summary(linked=already + linked, skipped=skipped, updated=updated)

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
        self.apply_claude_bridge()

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

        return issues

    def status_summary(self) -> dict[str, object]:
        return {
            "installed_skills": len(self.list_skills()),
            "global_agents_exists": self.paths.global_agents.exists(),
            "skills_sources_exists": self.paths.skills_sources_file.exists(),
        }
