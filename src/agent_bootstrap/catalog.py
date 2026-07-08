from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from .models import ArtifactSummary, PackageCatalogEntry


def load_catalog(catalog_file: Path) -> Dict[str, PackageCatalogEntry]:
    if not catalog_file.exists():
        return {}

    data = json.loads(catalog_file.read_text(encoding="utf-8"))
    packages = {}
    for item in data.get("packages", []):
        entry = PackageCatalogEntry(
            id=item["id"],
            display_name=item.get("display_name", item["id"]),
            origin=item.get("origin", "internal"),
            dedupe_group=item.get("dedupe_group", item["id"]),
            supported_surfaces=item.get("supported_surfaces", []),
            mcp_keys=item.get("mcp_keys", []),
        )
        packages[entry.id] = entry
    return packages


def save_catalog(catalog_file: Path, packages: Dict[str, PackageCatalogEntry]) -> None:
    catalog_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "packages": [
            {
                "id": entry.id,
                "display_name": entry.display_name,
                "origin": entry.origin,
                "dedupe_group": entry.dedupe_group,
                "supported_surfaces": entry.supported_surfaces,
                "mcp_keys": entry.mcp_keys,
            }
            for entry in sorted(packages.values(), key=lambda item: item.id)
        ]
    }
    catalog_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def collect_repo_artifacts(root: Path, package_id: str) -> ArtifactSummary:
    def matched_names(base: Path, pattern: str, suffix_to_strip: str = "") -> list[str]:
        names = []
        if not base.exists():
            return names
        for path in sorted(base.glob(pattern)):
            if suffix_to_strip:
                names.append(path.name.removesuffix(suffix_to_strip))
            else:
                names.append(path.name)
        return names

    hooks_present = (root / "hooks" / package_id).exists()

    return ArtifactSummary(
        skills=[],
        rules=matched_names(root / "rules", f"{package_id}-*.mdc", ".mdc"),
        commands=matched_names(root / "commands", f"{package_id}-*.md", ".md"),
        agents=matched_names(root / "agents", f"{package_id}-*.md", ".md"),
        hooks_present=hooks_present,
    )
