from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import re

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
DEFAULT_NPX_TIMEOUT_SECONDS = 900
NPX_TIMEOUT_ENV = "AGENT_BOOTSTRAP_NPX_TIMEOUT_SECONDS"
GITHUB_CLONE_TIMEOUT_SECONDS = 120


def _npx_timeout_seconds() -> int:
    raw_timeout = os.environ.get(NPX_TIMEOUT_ENV)
    if raw_timeout is None:
        return DEFAULT_NPX_TIMEOUT_SECONDS
    try:
        timeout_seconds = int(raw_timeout)
    except ValueError as error:
        raise SkillsInstallError(
            f"{NPX_TIMEOUT_ENV} must be a positive integer, got {raw_timeout!r}"
        ) from error
    if timeout_seconds <= 0:
        raise SkillsInstallError(
            f"{NPX_TIMEOUT_ENV} must be a positive integer, got {raw_timeout!r}"
        )
    return timeout_seconds


def _github_clone_url(repo: str) -> str | None:
    if repo.count("/") != 1 or any(char.isspace() for char in repo):
        return None
    owner, name = repo.split("/", maxsplit=1)
    if not owner or not name:
        return None
    return f"https://github.com/{repo}.git"


def _clone_github_source(repo: str, destination: Path) -> None:
    clone_url = _github_clone_url(repo)
    if clone_url is None:
        raise ValueError(f"not a GitHub owner/repository source: {repo!r}")
    if shutil.which("git") is None:
        raise SkillsInstallError("git is required to install GitHub skill sources")

    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    try:
        completed = subprocess.run(
            ["git", "clone", "--depth=1", clone_url, str(destination)],
            capture_output=True,
            text=True,
            check=False,
            timeout=GITHUB_CLONE_TIMEOUT_SECONDS,
            env=env,
        )
    except subprocess.TimeoutExpired as error:
        raise SkillsInstallError(
            f"GitHub clone for source {repo!r} timed out after {GITHUB_CLONE_TIMEOUT_SECONDS} seconds"
        ) from error
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or f"exit code {completed.returncode}"
        raise SkillsInstallError(f"failed to clone GitHub source {repo!r}: {detail}")


def _checkout_skill_name(skill_file: Path) -> str:
    content = skill_file.read_text(encoding="utf-8")
    if content.startswith("---"):
        closing = content.find("\n---", 3)
        if closing != -1:
            match = re.search(r"^name:\s*([^#\n]+)", content[3:closing], flags=re.MULTILINE)
            if match:
                return match.group(1).strip().strip("\"'")
    return skill_file.parent.name


def _skill_folder_hash(skill_dir: Path) -> str:
    digest = sha256()
    for path in sorted(
        (path for path in skill_dir.rglob("*") if path.is_file() and ".git" not in path.parts),
        key=lambda path: path.relative_to(skill_dir).as_posix(),
    ):
        digest.update(path.relative_to(skill_dir).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _record_github_checkout_lock(source: SkillSourceEntry, checkout: Path, lock_file: Path) -> None:
    try:
        import json

        lock = json.loads(lock_file.read_text(encoding="utf-8")) if lock_file.is_file() else {}
    except (OSError, ValueError) as error:
        raise SkillsInstallError(f"unable to read global skill lock {lock_file}: {error}") from error
    if not isinstance(lock, dict):
        raise SkillsInstallError(f"global skill lock {lock_file} must be a JSON object")
    skills = lock.setdefault("skills", {})
    if not isinstance(skills, dict):
        raise SkillsInstallError(f"global skill lock {lock_file} has an invalid skills section")

    wanted = None if source.skills == ["*"] else set(source.skills)
    now = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    for skill_file in checkout.rglob("SKILL.md"):
        name = _checkout_skill_name(skill_file)
        if wanted is not None and name not in wanted:
            continue
        relative_path = skill_file.relative_to(checkout).as_posix()
        existing = skills.get(name)
        skills[name] = {
            "source": source.repo,
            "sourceType": "github",
            "sourceUrl": _github_clone_url(source.repo),
            "skillPath": relative_path,
            "skillFolderHash": _skill_folder_hash(skill_file.parent),
            "installedAt": existing.get("installedAt", now) if isinstance(existing, dict) else now,
            "updatedAt": now,
        }
    lock["version"] = 3
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    lock_file.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")


def _lock_skill_names(lock_file: Path) -> set[str] | None:
    """Return names from a readable lock; None means unreadable or malformed."""
    if not lock_file.is_file():
        return set()
    try:
        import json

        data = json.loads(lock_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    skills = data.get("skills")
    if isinstance(skills, dict):
        return set(skills)
    if isinstance(skills, list):
        return {str(skill) for skill in skills}
    return set()


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
    timeout_seconds: int | None = None,
) -> InstallResult:
    if dry_run:
        return InstallResult(
            source_id=source_id,
            command=argv,
            returncode=0,
            stdout="",
            stderr="",
        )

    if timeout_seconds is None:
        timeout_seconds = _npx_timeout_seconds()

    try:
        completed = subprocess.run(
            argv,
            cwd=str(cwd) if cwd is not None else None,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as error:
        source = f" source {source_id!r}" if source_id else ""
        raise SkillsInstallError(
            f"npx skills{source} timed out after {timeout_seconds} seconds: {' '.join(argv)}"
        ) from error
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
    global_lock_file: Path | None = None,
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
    clone_url = _github_clone_url(source.repo)
    if dry_run or clone_url is None:
        result = run_install_command(argv, source_id=source.id, dry_run=dry_run, cwd=cwd)
    else:
        with tempfile.TemporaryDirectory(prefix="agent-bootstrap-skill-") as temp_dir:
            checkout = Path(temp_dir) / source.id
            _clone_github_source(source.repo, checkout)
            argv[3] = str(checkout)
            result = run_install_command(argv, source_id=source.id, cwd=cwd)
            if result.returncode == 0 and global_scope:
                _record_github_checkout_lock(
                    source,
                    checkout,
                    global_lock_file or Path.home() / ".agents" / ".skill-lock.json",
                )
            result = InstallResult(
                source_id=result.source_id,
                command=build_add_argv(source, agents=agents, global_scope=global_scope, npx=npx),
                returncode=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                skipped=result.skipped,
            )
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
    global_lock_file: Path | None = None,
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
            global_lock_file=global_lock_file,
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
    return install_all(
        config,
        dry_run=dry_run,
        cwd=paths.root,
        global_lock_file=paths.global_skill_lock,
    )


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
    config: SkillsSourcesConfig | None = None

    if not paths.skills_sources_file.is_file():
        issues.append(
            DoctorIssue(
                level="error",
                scope="skills",
                message=f"Missing skills sources file: {paths.skills_sources_file}",
            )
        )
    else:
        try:
            config = load_skills_sources(paths.skills_sources_file)
        except ValueError as error:
            issues.append(
                DoctorIssue(level="error", scope="skills", message=f"Invalid skills sources file: {error}")
            )

    if shutil.which("npx") is None:
        issues.append(
            DoctorIssue(
                level="error",
                scope="skills",
                message="npx is not available in PATH",
            )
        )

    for label, lock_file in (("project", paths.skills_lock_file), ("global", paths.global_skill_lock)):
        if not lock_file.is_file():
            continue
        try:
            import json

            lock_root = json.loads(lock_file.read_text(encoding="utf-8"))
            if not isinstance(lock_root, dict):
                raise ValueError("lock root must be a JSON object")
        except (OSError, ValueError) as error:
            issues.append(
                DoctorIssue(
                    level="warning",
                    scope="skills",
                    message=f"Unable to read {label} skills lock file: {error}",
                )
            )

    if config is not None and config.scope == "global":
        locked = _lock_skill_names(paths.global_skill_lock)
        if locked is not None and paths.global_skill_lock.is_file():
            declared = {
                skill
                for source in config.active_sources()
                for skill in source.skills
            }
            declared.discard("*")
            for skill in sorted(declared - locked):
                issues.append(
                    DoctorIssue(
                        level="warning",
                        scope="skills",
                        message=f"Manifest skill {skill!r} is absent from the global skill lock",
                    )
                )

    return issues
