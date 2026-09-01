"""Find and remove installed skills that the manifest does not want.

Two things put a skill in ``~/.agents/skills`` that you did not ask for:

* a ``skills: all`` source whose upstream repository ships more than its
  catalog -- its own CLI test fixtures, for example;
* a source that was removed or disabled after its skills were installed.

Neither is visible to Doctor's manual-skill check, because that check treats
anything present in the lock as managed. The lock records what *was* installed;
the manifest declares what *should* be. This module reconciles the two.

Classification, in order:

``excluded``   the owning source installs it but the manifest excludes it
``orphaned``   pinned to a source that is no longer active in the manifest
``stale-pin``  in the lock with no directory on disk
``manual``     a directory with no lock entry -- user-placed, never removed
               unless explicitly requested
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from .paths import AgentbotPaths
from .skills_sources import SkillsSourcesConfig

REMOVABLE_BY_DEFAULT = frozenset({"excluded", "orphaned", "stale-pin"})


@dataclass(frozen=True)
class PruneCandidate:
    name: str
    reason: str
    detail: str
    directory: Path | None
    locked: bool

    @property
    def removable_by_default(self) -> bool:
        return self.reason in REMOVABLE_BY_DEFAULT


@dataclass(frozen=True)
class PruneReport:
    candidates: tuple[PruneCandidate, ...]
    removed: tuple[str, ...] = ()
    applied: bool = False

    @property
    def removable(self) -> tuple[PruneCandidate, ...]:
        return tuple(item for item in self.candidates if item.removable_by_default)

    @property
    def manual(self) -> tuple[PruneCandidate, ...]:
        return tuple(item for item in self.candidates if item.reason == "manual")


def _read_lock(lock_file: Path) -> dict[str, dict]:
    if not lock_file.is_file():
        return {}
    try:
        payload = json.loads(lock_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    skills = payload.get("skills")
    if not isinstance(skills, dict):
        return {}
    return {name: entry for name, entry in skills.items() if isinstance(entry, dict)}


def _installed_skill_dirs(skills_home: Path) -> dict[str, Path]:
    if not skills_home.is_dir():
        return {}
    return {
        entry.name: entry
        for entry in sorted(skills_home.iterdir())
        if entry.is_dir() and (entry / "SKILL.md").is_file()
    }


def plan_prune(paths: AgentbotPaths, config: SkillsSourcesConfig) -> PruneReport:
    """Classify every installed skill and lock pin against the manifest."""
    lock = _read_lock(paths.global_skill_lock)
    installed = _installed_skill_dirs(paths.agents_skills_home)

    active_repos = {source.repo: source for source in config.active_sources() if source.repo}
    declared_names = {
        name
        for source in config.active_sources()
        for name in source.skills
        if name != "*"
    }
    candidates: list[PruneCandidate] = []

    for name, directory in installed.items():
        entry = lock.get(name)
        if entry is None:
            if name in declared_names:
                continue
            if name == "graphify" and (directory / ".graphify_version").is_file():
                continue
            candidates.append(
                PruneCandidate(
                    name=name,
                    reason="manual",
                    detail="on disk, not in the lock; user-placed",
                    directory=directory,
                    locked=False,
                )
            )
            continue

        repo = entry.get("source")
        source = active_repos.get(repo) if isinstance(repo, str) else None
        if source is None:
            candidates.append(
                PruneCandidate(
                    name=name,
                    reason="orphaned",
                    detail=f"pinned to {repo or 'an unknown source'}, no active manifest source",
                    directory=directory,
                    locked=True,
                )
            )
            continue

        if source.excludes(name):
            candidates.append(
                PruneCandidate(
                    name=name,
                    reason="excluded",
                    detail=f"{source.id} installs it, manifest excludes it",
                    directory=directory,
                    locked=True,
                )
            )

    for name in sorted(set(lock) - set(installed)):
        repo = lock[name].get("source")
        candidates.append(
            PruneCandidate(
                name=name,
                reason="stale-pin",
                detail=f"pinned to {repo or 'an unknown source'}, no directory on disk",
                directory=None,
                locked=True,
            )
        )

    candidates.sort(key=lambda item: (item.reason, item.name))
    return PruneReport(candidates=tuple(candidates))


def enforce_exclusions(paths: AgentbotPaths, config: SkillsSourcesConfig) -> tuple[str, ...]:
    """Remove skills the manifest excludes, right after an install.

    `exclude:` has to mean "never present", not "prunable later". The Skills
    CLI installs everything a `skills: all` source publishes and has no
    exclusion flag, so the exclusion is applied here instead: immediately after
    install, before the Claude and Codex bridges ever see the directory.

    Without this, `exclude:` was a treadmill -- every install re-added and
    re-pinned the excluded skills, and only a separate `skills prune` removed
    them again.
    """
    report = plan_prune(paths, config)
    excluded = PruneReport(
        candidates=tuple(item for item in report.candidates if item.reason == "excluded")
    )
    if not excluded.candidates:
        return ()
    return apply_prune(paths, excluded).removed


def _unlink_bridge(link: Path, owned_root: Path) -> None:
    """Remove a bridge symlink, but only one that points into our own store."""
    if not link.is_symlink():
        return
    try:
        target = link.resolve()
    except OSError:
        return
    try:
        target.relative_to(owned_root.resolve())
    except ValueError:
        # Points somewhere else: belongs to the user or another installer.
        return
    link.unlink()


def apply_prune(
    paths: AgentbotPaths,
    report: PruneReport,
    *,
    include_manual: bool = False,
    manual_names: tuple[str, ...] | None = None,
    candidate_names: tuple[str, ...] | None = None,
) -> PruneReport:
    """Remove the classified skills: directory, lock pin, and bridge links."""
    selectors = sum(value is not None for value in (manual_names, candidate_names)) + int(
        include_manual
    )
    if selectors > 1:
        raise ValueError(
            "include_manual, manual_names, and candidate_names cannot be combined"
        )

    if candidate_names is not None:
        candidates_by_name = {item.name: item for item in report.candidates}
        invalid = sorted(set(candidate_names) - set(candidates_by_name))
        if invalid:
            raise ValueError(f"not prune candidates: {', '.join(invalid)}")
        targets = [candidates_by_name[name] for name in dict.fromkeys(candidate_names)]
    elif manual_names is not None:
        manual_by_name = {item.name: item for item in report.manual}
        invalid = sorted(set(manual_names) - set(manual_by_name))
        if invalid:
            raise ValueError(f"not removable manual skills: {', '.join(invalid)}")
        targets = [manual_by_name[name] for name in dict.fromkeys(manual_names)]
    else:
        targets = [item for item in report.candidates if item.removable_by_default]
    if include_manual:
        targets.extend(report.manual)
    if not targets:
        return PruneReport(candidates=report.candidates, removed=(), applied=True)

    store = paths.agents_skills_home
    removed: list[str] = []
    for item in targets:
        if item.directory is not None and item.directory.is_dir():
            shutil.rmtree(item.directory)
        _unlink_bridge(paths.claude_skills_home / item.name, store)
        _unlink_bridge(paths.codex_home / "skills" / item.name, store)
        removed.append(item.name)

    lock_file = paths.global_skill_lock
    if lock_file.is_file():
        try:
            payload = json.loads(lock_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = None
        if isinstance(payload, dict) and isinstance(payload.get("skills"), dict):
            for name in removed:
                payload["skills"].pop(name, None)
            lock_file.write_text(
                json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )

    return PruneReport(
        candidates=report.candidates, removed=tuple(sorted(removed)), applied=True
    )
