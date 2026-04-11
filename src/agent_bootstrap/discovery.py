from __future__ import annotations

from pathlib import Path
from typing import Dict

from .catalog import collect_repo_artifacts
from .models import ArtifactSummary, DiscoveryRecord, PackageCatalogEntry


def scan_managed_packages(root: Path, catalog: Dict[str, PackageCatalogEntry]) -> Dict[str, DiscoveryRecord]:
    discovered: Dict[str, DiscoveryRecord] = {}
    for package_id, entry in catalog.items():
        artifacts = collect_repo_artifacts(root, package_id)
        if _has_artifacts(artifacts) or entry.mcp_keys:
            discovered[package_id] = DiscoveryRecord(
                package_id=package_id,
                source=entry.origin,
                detected_repo=_has_artifacts(artifacts) or bool(entry.mcp_keys),
                artifact_summary=artifacts,
            )
    return discovered


def scan_cursor_cache(cache_root: Path) -> Dict[str, DiscoveryRecord]:
    discovered: Dict[str, DiscoveryRecord] = {}
    if not cache_root.exists():
        return discovered

    for plugin_dir in sorted(path for path in cache_root.iterdir() if path.is_dir()):
        version_dir = _preferred_version_dir(plugin_dir)
        if version_dir is None:
            continue
        discovered[plugin_dir.name] = DiscoveryRecord(
            package_id=plugin_dir.name,
            source="cursor-cache",
            detected_local=True,
            hash_value=version_dir.name,
            artifact_summary=_collect_cache_artifacts(version_dir),
        )
    return discovered


def cache_version_dir(cache_root: Path, package_id: str) -> Path | None:
    plugin_dir = cache_root / package_id
    return _preferred_version_dir(plugin_dir)


def merge_discovery(
    managed: Dict[str, DiscoveryRecord], cache: Dict[str, DiscoveryRecord]
) -> Dict[str, DiscoveryRecord]:
    merged = dict(managed)
    for package_id, record in cache.items():
        if package_id in merged:
            current = merged[package_id]
            merged[package_id] = DiscoveryRecord(
                package_id=package_id,
                source=current.source,
                detected_local=record.detected_local,
                detected_repo=current.detected_repo,
                hash_value=record.hash_value,
                artifact_summary=current.artifact_summary if _has_artifacts(current.artifact_summary) else record.artifact_summary,
            )
        else:
            merged[package_id] = record
    return merged


def _collect_cache_artifacts(version_dir: Path) -> ArtifactSummary:
    def count_dirs(base: Path) -> list[str]:
        if not base.exists():
            return []
        return sorted(path.name for path in base.iterdir() if path.is_dir())

    def count_files(base: Path, suffix: str) -> list[str]:
        if not base.exists():
            return []
        return sorted(path.name for path in base.glob(f"*{suffix}") if path.is_file())

    return ArtifactSummary(
        skills=count_dirs(version_dir / "skills"),
        rules=count_files(version_dir / "rules", ".mdc"),
        commands=count_files(version_dir / "commands", ".md"),
        agents=count_files(version_dir / "agents", ".md"),
        hooks_present=(version_dir / "hooks").exists(),
    )


def _has_artifacts(artifacts: ArtifactSummary) -> bool:
    return any(
        [
            artifacts.skills,
            artifacts.rules,
            artifacts.commands,
            artifacts.agents,
            artifacts.hooks_present,
        ]
    )


def _preferred_version_dir(plugin_dir: Path) -> Path | None:
    if not plugin_dir.exists():
        return None
    versions = [path for path in plugin_dir.iterdir() if path.is_dir()]
    if not versions:
        return None
    return max(versions, key=lambda path: (path.stat().st_mtime_ns, path.name))
