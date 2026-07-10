from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

SUPPORTED_VERSION = 1


class SkillsSourcesError(ValueError):
    """Raised when skills.sources.yaml is missing or invalid."""


@dataclass(frozen=True)
class SkillSourceEntry:
    id: str
    repo: str | None
    skills: list[str] = field(default_factory=list)
    enabled: bool = True


@dataclass(frozen=True)
class SkillsSourcesConfig:
    version: int
    agents: list[str]
    scope: str
    sources: list[SkillSourceEntry]

    def active_sources(self) -> list[SkillSourceEntry]:
        return [
            source
            for source in self.sources
            if source.enabled and source.repo and source.skills
        ]


def load_skills_sources(path: Path) -> SkillsSourcesConfig:
    if not path.is_file():
        raise SkillsSourcesError(f"skills sources file not found: {path}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise SkillsSourcesError(f"skills sources file must be a mapping: {path}")

    return validate_skills_sources(raw, path=path)


def validate_skills_sources(raw: dict[str, Any], *, path: Path | None = None) -> SkillsSourcesConfig:
    label = str(path) if path is not None else "skills.sources.yaml"

    version = raw.get("version")
    if version != SUPPORTED_VERSION:
        raise SkillsSourcesError(f"{label}: unsupported version {version!r} (expected {SUPPORTED_VERSION})")

    agents = _require_string_list(raw.get("agents"), field_name="agents", label=label)
    if not agents:
        raise SkillsSourcesError(f"{label}: agents must be a non-empty list")

    scope = raw.get("scope", "global")
    if not isinstance(scope, str) or not scope.strip():
        raise SkillsSourcesError(f"{label}: scope must be a non-empty string")

    sources_raw = raw.get("sources")
    if not isinstance(sources_raw, list):
        raise SkillsSourcesError(f"{label}: sources must be a list")

    sources: list[SkillSourceEntry] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(sources_raw):
        if not isinstance(item, dict):
            raise SkillsSourcesError(f"{label}: sources[{index}] must be a mapping")

        source_id = item.get("id")
        if not isinstance(source_id, str) or not source_id.strip():
            raise SkillsSourcesError(f"{label}: sources[{index}].id must be a non-empty string")
        if source_id in seen_ids:
            raise SkillsSourcesError(f"{label}: duplicate source id {source_id!r}")
        seen_ids.add(source_id)

        repo = item.get("repo")
        if repo is not None and not isinstance(repo, str):
            raise SkillsSourcesError(f"{label}: sources[{index}].repo must be a string or null")

        skills = _require_string_list(item.get("skills", []), field_name="skills", label=label, index=index)
        enabled = item.get("enabled", True)
        if not isinstance(enabled, bool):
            raise SkillsSourcesError(f"{label}: sources[{index}].enabled must be a boolean")

        sources.append(
            SkillSourceEntry(
                id=source_id,
                repo=repo.strip() if isinstance(repo, str) else None,
                skills=skills,
                enabled=enabled,
            )
        )

    return SkillsSourcesConfig(version=version, agents=agents, scope=scope.strip(), sources=sources)


def _require_string_list(
    value: Any,
    *,
    field_name: str,
    label: str,
    index: int | None = None,
) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        location = f"sources[{index}].{field_name}" if index is not None else field_name
        raise SkillsSourcesError(f"{label}: {location} must be a list")

    items: list[str] = []
    for item_index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            location = (
                f"sources[{index}].{field_name}[{item_index}]"
                if index is not None
                else f"{field_name}[{item_index}]"
            )
            raise SkillsSourcesError(f"{label}: {location} must be a non-empty string")
        items.append(item.strip())
    return items
