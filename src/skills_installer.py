from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .models import DoctorIssue
from .paths import BootstrapPaths
from .skills_sources import SkillSourceEntry, SkillsSourcesConfig, load_skills_sources


class SkillsInstallError(RuntimeError):
    """Raised when an npx skills subprocess fails."""


@dataclass(frozen=True)
class InstallResult:
    source_id: str
    command: list[str]
    returncode: int
    stdout: str
    stderr: str
    skipped: bool = False


@dataclass(frozen=True)
class InstallSummary:
    ok: int
    failed: int
    skipped: int


def summarize_install_results(results: list[InstallResult]) -> InstallSummary:
    ok = failed = skipped = 0
    for result in results:
        if result.skipped:
            skipped += 1
        elif result.returncode == 0:
            ok += 1
        else:
            failed += 1
    return InstallSummary(ok=ok, failed=failed, skipped=skipped)


DEFAULT_NPX = "npx"


def build_add_argv(
    source: SkillSourceEntry,
    *,
    agents: list[str],
    global_scope: bool = True,
    npx: str = DEFAULT_NPX,
) -> list[str]:
    if not source.repo:
        raise ValueError(f"source {source.id!r} has no repo")

    argv = [npx, "skills", "add", source.repo]
    for skill in source.skills:
        argv.extend(["--skill", skill])
    for agent in agents:
        argv.extend(["-a", agent])
    if global_scope:
        argv.append("-g")
    argv.append("-y")
    return argv


def build_update_argv(*, npx: str = DEFAULT_NPX, global_scope: bool = True) -> list[str]:
    argv = [npx, "skills", "update"]
    if global_scope:
        argv.append("-g")
    argv.append("-y")
    return argv


def run_install_command(
    argv: list[str],
    *,
    source_id: str = "",
    dry_run: bool = False,
    cwd: Path | None = None,
) -> InstallResult:
    if dry_run:
        return InstallResult(
            source_id=source_id,
            command=argv,
            returncode=0,
            stdout="",
            stderr="",
        )

    completed = subprocess.run(
        argv,
        cwd=str(cwd) if cwd is not None else None,
        capture_output=True,
        text=True,
        check=False,
    )
    return InstallResult(
        source_id=source_id,
        command=argv,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def install_source(
    source: SkillSourceEntry,
    *,
    agents: list[str],
    global_scope: bool = True,
    dry_run: bool = False,
    npx: str = DEFAULT_NPX,
    cwd: Path | None = None,
) -> InstallResult:
    if not source.enabled or not source.repo or not source.skills:
        return InstallResult(
            source_id=source.id,
            command=[],
            returncode=0,
            stdout="",
            stderr="",
            skipped=True,
        )

    argv = build_add_argv(source, agents=agents, global_scope=global_scope, npx=npx)
    result = run_install_command(argv, source_id=source.id, dry_run=dry_run, cwd=cwd)
    if not dry_run and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}"
        raise SkillsInstallError(f"failed to install source {source.id!r}: {detail}")
    return result


def install_all(
    config: SkillsSourcesConfig,
    *,
    dry_run: bool = False,
    npx: str = DEFAULT_NPX,
    cwd: Path | None = None,
) -> list[InstallResult]:
    global_scope = config.scope == "global"
    return [
        install_source(
            source,
            agents=config.agents,
            global_scope=global_scope,
            dry_run=dry_run,
            npx=npx,
            cwd=cwd,
        )
        for source in config.active_sources()
    ]


def update_all(
    config: SkillsSourcesConfig,
    *,
    dry_run: bool = False,
    npx: str = DEFAULT_NPX,
    cwd: Path | None = None,
) -> InstallResult:
    argv = build_update_argv(npx=npx, global_scope=config.scope == "global")
    result = run_install_command(argv, source_id="update", dry_run=dry_run, cwd=cwd)
    if not dry_run and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}"
        raise SkillsInstallError(f"failed to update skills: {detail}")
    return result


def install_skills(paths: BootstrapPaths, *, dry_run: bool = False) -> list[InstallResult]:
    config = load_skills_sources(paths.skills_sources_file)
    return install_all(config, dry_run=dry_run, cwd=paths.root)


def update_skills(paths: BootstrapPaths, *, dry_run: bool = False) -> InstallResult:
    config = load_skills_sources(paths.skills_sources_file)
    return update_all(config, dry_run=dry_run, cwd=paths.root)


def list_installed_skills(paths: BootstrapPaths) -> list[str]:
    home = paths.agents_skills_home
    if not home.is_dir():
        return []
    return sorted(skill_dir.name for skill_dir in home.iterdir() if skill_dir.is_dir())


def doctor_skills(paths: BootstrapPaths) -> list[DoctorIssue]:
    issues: list[DoctorIssue] = []

    if not paths.skills_sources_file.is_file():
        issues.append(
            DoctorIssue(
                level="error",
                scope="skills",
                message=f"Missing skills sources file: {paths.skills_sources_file}",
            )
        )

    if shutil.which("npx") is None:
        issues.append(
            DoctorIssue(
                level="error",
                scope="skills",
                message="npx is not available in PATH",
            )
        )

    if paths.skills_lock_file.is_file():
        try:
            paths.skills_lock_file.read_text(encoding="utf-8")
        except OSError as error:
            issues.append(
                DoctorIssue(
                    level="warning",
                    scope="skills",
                    message=f"Unable to read skills lock file: {error}",
                )
            )

    return issues
