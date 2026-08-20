from __future__ import annotations

import os
import re
import tempfile
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from .command_runner import CommandRunner
from .skills_sources import SkillsSourcesConfig

_COMMAND_RUNNER = CommandRunner()


@dataclass(frozen=True)
class SourceCatalog:
    source_id: str
    repo: str
    revision: str
    skills: tuple[str, ...]


class StaleSourceCatalogError(RuntimeError):
    """Raised before mutation when a source changed after update preview."""


CloneSource = Callable[[str, Path], None]
RevisionReader = Callable[[Path], str]


def discover_remote_catalogs(
    config: SkillsSourcesConfig,
    *,
    clone_source: CloneSource | None = None,
    revision_reader: RevisionReader | None = None,
) -> tuple[SourceCatalog, ...]:
    clone = clone_source or _clone_source
    revision = revision_reader or _revision
    catalogs: list[SourceCatalog] = []
    with tempfile.TemporaryDirectory(prefix="agentbot-update-plan-") as temporary:
        root = Path(temporary)
        for source in config.active_sources():
            if source.repo is None:
                continue
            checkout = root / source.id
            clone(source.repo, checkout)
            catalogs.append(
                SourceCatalog(
                    source.id,
                    source.repo,
                    revision(checkout),
                    discover_checkout_skills(checkout),
                )
            )
    return tuple(catalogs)


@contextmanager
def verified_source_checkouts(
    config: SkillsSourcesConfig,
    expected: tuple[SourceCatalog, ...],
    *,
    clone_source: CloneSource | None = None,
    revision_reader: RevisionReader | None = None,
):
    clone = clone_source or _clone_source
    revision = revision_reader or _revision
    expected_by_id = {catalog.source_id: catalog for catalog in expected}
    with tempfile.TemporaryDirectory(prefix="agentbot-update-apply-") as temporary:
        root = Path(temporary)
        checkouts: dict[str, Path] = {}
        current: list[SourceCatalog] = []
        for source in config.active_sources():
            if source.repo is None:
                continue
            checkout = root / source.id
            clone(source.repo, checkout)
            catalog = SourceCatalog(
                source.id,
                source.repo,
                revision(checkout),
                discover_checkout_skills(checkout),
            )
            current.append(catalog)
            checkouts[source.id] = checkout
        current_tuple = tuple(current)
        if current_tuple != expected or set(checkouts) != set(expected_by_id):
            raise StaleSourceCatalogError(
                "Upstream skill sources changed after preview; preview again before applying."
            )
        yield checkouts


def _clone_source(repo: str, destination: Path) -> None:
    if repo.count("/") != 1 or any(char.isspace() for char in repo):
        raise ValueError(f"not a GitHub owner/repository source: {repo!r}")
    timeout = int(os.environ.get("AGENTBOT_GITHUB_CLONE_TIMEOUT_SECONDS", "300"))
    completed = _COMMAND_RUNNER.run(
        ["git", "clone", "--depth=1", f"https://github.com/{repo}.git", str(destination)],
        timeout_seconds=timeout,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"failed to inspect skill source {repo!r}: {completed.detail()}"
        )


def _revision(checkout: Path) -> str:
    completed = _COMMAND_RUNNER.run(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"],
        timeout_seconds=30,
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        raise RuntimeError(f"unable to read source revision for {checkout.name!r}")
    return completed.stdout.strip()


def skill_name_from_file(skill_file: Path) -> str:
    content = skill_file.read_text(encoding="utf-8")
    if content.startswith("---"):
        closing = content.find("\n---", 3)
        if closing != -1:
            frontmatter = content[3:closing]
            match = re.search(
                r"^name:\s*([^#\n]+)", frontmatter, flags=re.MULTILINE
            )
            if match:
                return match.group(1).strip().strip("\"'")
    return skill_file.parent.name


def discover_checkout_skills(checkout: Path) -> tuple[str, ...]:
    if not checkout.is_dir():
        return ()
    names = {
        skill_name_from_file(path)
        for path in checkout.rglob("SKILL.md")
        if path.is_file()
    }
    return tuple(sorted(name for name in names if name))
