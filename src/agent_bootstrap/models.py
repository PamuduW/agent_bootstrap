from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class PackageCatalogEntry:
    id: str
    display_name: str
    origin: str
    dedupe_group: str
    supported_surfaces: List[str]
    mcp_keys: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class ArtifactSummary:
    skills: List[str] = field(default_factory=list)
    rules: List[str] = field(default_factory=list)
    commands: List[str] = field(default_factory=list)
    agents: List[str] = field(default_factory=list)
    hooks_present: bool = False


@dataclass(frozen=True)
class DiscoveryRecord:
    package_id: str
    source: str
    detected_local: bool = False
    detected_repo: bool = False
    hash_value: str = ""
    artifact_summary: ArtifactSummary = field(default_factory=ArtifactSummary)


@dataclass(frozen=True)
class PackageRow:
    package_id: str
    display_name: str
    managed: bool
    detected_local: bool
    detected_repo: bool
    enabled: bool
    applied: bool
    source: str
    artifacts: ArtifactSummary
    mcp_keys: List[str]


@dataclass(frozen=True)
class Overview:
    package_rows: List[PackageRow]


@dataclass
class StateSnapshot:
    enabled_packages: Dict[str, bool] = field(default_factory=dict)
    tracked_workspaces: List[str] = field(default_factory=list)
    instruction_hashes: Dict[str, str] = field(default_factory=dict)
