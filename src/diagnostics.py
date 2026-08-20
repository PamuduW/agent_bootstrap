from __future__ import annotations

import json
import re
import stat
from pathlib import Path

from .claude_statusline import doctor_claude_statusline, inspect_claude_statusline
from .graphify import GraphifyIntegration, GraphifyStatus
from .models import DiagnosticsSnapshot, DoctorIssue
from .paths import AgentbotPaths
from .render import installed_skill_dirs, managed_skill_names
from .skills_installer import doctor_skills, list_installed_skills
from .skills_sources import load_skills_sources


class Diagnostics:
    def __init__(self, paths: AgentbotPaths) -> None:
        self.paths = paths

    def collect(self) -> DiagnosticsSnapshot:
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

        installed_skills = tuple(self.list_skills())
        managed_names = set(managed_skill_names(self.paths))
        declared_names = self._manifest_declared_skill_names()
        claude_bridge_links = 0
        if self.paths.claude_skills_home.is_dir():
            claude_bridge_links = sum(
                1 for entry in self.paths.claude_skills_home.iterdir() if entry.is_symlink()
            )
        statusline = inspect_claude_statusline(self.paths)
        issues = tuple(self.doctor_issues()) + tuple(self.skills_doctor_issues())

        return DiagnosticsSnapshot(
            installed_skills=installed_skills,
            enabled_sources=enabled_sources,
            global_agents_exists=self.paths.global_agents.exists(),
            skills_sources_exists=self.paths.skills_sources_file.exists(),
            global_lock_exists=self.paths.global_skill_lock.exists(),
            global_lock_skills=self._count_global_lock_skills(self.paths),
            managed_skill_count=len(managed_names),
            manual_skill_count=len(
                self._unmanaged_skill_dirs(managed_names, declared_names)
            ),
            claude_bridge_links=claude_bridge_links,
            claude_statusline_state=statusline.status_label,
            issues=issues,
        )

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
        managed_dirs = {
            skill_dir.name: skill_dir for skill_dir in installed_skill_dirs(self.paths)
        }
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
                        message=(
                            f"Managed Codex skill link for {name!r} is missing or broken: "
                            f"{target}"
                        ),
                    )
                )
            elif target.resolve() != source.resolve():
                issues.append(
                    DoctorIssue(
                        level="warning",
                        scope="codex",
                        message=(
                            f"Managed Codex skill link for {name!r} points outside the "
                            f"managed source: {target}"
                        ),
                    )
                )

        for source in self._unmanaged_skill_dirs(managed_names, declared_names):
            target = codex_skills / source.name
            if (
                not target.is_symlink()
                or not target.exists()
                or target.resolve() != source.resolve()
            ):
                message = (
                    f"Manual skill {source.name!r} is outside managed sources and has no "
                    "Codex link yet; run './install.sh global' to make the local skill "
                    "available, then add a source to make it reproducible"
                )
            else:
                message = (
                    f"Manual skill {source.name!r} is available to Codex but outside "
                    "managed sources; add a manifest source to make it reproducible"
                )
            issues.append(DoctorIssue("warning", "reproducibility", message))
        return issues

    def graphify_status(self) -> GraphifyStatus:
        return GraphifyIntegration(self.paths).status()

    def status_summary(self) -> dict[str, object]:
        snapshot = self.collect()
        return {
            "installed_skills": len(snapshot.installed_skills),
            "enabled_sources": snapshot.enabled_sources,
            "global_agents_exists": snapshot.global_agents_exists,
            "skills_sources_exists": snapshot.skills_sources_exists,
            "global_lock_exists": snapshot.global_lock_exists,
            "global_lock_skills": snapshot.global_lock_skills,
            "managed_skill_count": snapshot.managed_skill_count,
            "manual_skill_count": snapshot.manual_skill_count,
            "claude_bridge_links": snapshot.claude_bridge_links,
            "claude_statusline_state": snapshot.claude_statusline_state,
            "doctor_issue_count": len(snapshot.issues),
        }

    def _unmanaged_skill_dirs(
        self, managed_names: set[str], declared_names: set[str]
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
                f"{status.message} Install it through Dotfiles or run: "
                "uv tool install graphifyy"
            )
        if status.state == "stale":
            return f"{status.message} Run `agentbot graphify setup` to refresh the skill."
        if status.state == "conflict":
            targets = [
                label
                for label, target_state in (
                    ("Codex", status.codex_state),
                    ("Claude", status.claude_state),
                )
                if target_state == "conflict"
            ]
            target_text = ", ".join(targets) or "an assistant"
            return f"{status.message} Preserved conflicting {target_text} target(s)."
        return status.message

    def _manifest_declared_skill_names(self) -> set[str]:
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
        token_file = self.paths.config_home / "github.env"
        if not token_file.exists() and not token_file.is_symlink():
            return []
        if token_file.is_symlink() or not token_file.is_file():
            return [
                DoctorIssue(
                    "warning",
                    "token",
                    f"saved GitHub token path is not a regular file: {token_file}",
                )
            ]
        try:
            mode = stat.S_IMODE(token_file.stat().st_mode)
            content = token_file.read_text(encoding="utf-8")
        except OSError as error:
            return [
                DoctorIssue(
                    "warning", "token", f"saved GitHub token cannot be read: {error}"
                )
            ]
        if mode != 0o600:
            return [
                DoctorIssue(
                    "warning",
                    "token",
                    f"saved GitHub token must have mode 600: {token_file}",
                )
            ]
        lines = content.splitlines(keepends=True)
        if (
            len(lines) != 1
            or not lines[0].endswith("\n")
            or not lines[0].startswith("GITHUB_TOKEN=")
        ):
            return [
                DoctorIssue(
                    "warning", "token", "saved GitHub token has malformed assignment"
                )
            ]
        value = lines[0][len("GITHUB_TOKEN=") : -1]
        if len(value) < 20 or re.fullmatch(r"[A-Za-z0-9_]+", value) is None:
            return [
                DoctorIssue(
                    "warning", "token", "saved GitHub token has an invalid value"
                )
            ]
        return []

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
        if isinstance(skills, (dict, list)):
            return len(skills)
        return 0
