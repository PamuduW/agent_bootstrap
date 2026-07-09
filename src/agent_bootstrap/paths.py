from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BootstrapPaths:
    root: Path
    codex_home: Path
    claude_home: Path
    cursor_home: Path

    @property
    def global_agents(self) -> Path:
        return self.root / "global" / "AGENTS.md"

    @property
    def skills_sources_file(self) -> Path:
        return self.root / "skills.sources.yaml"

    @property
    def skills_lock_file(self) -> Path:
        return self.root / "skills-lock.json"

    @property
    def agents_skills_home(self) -> Path:
        return Path.home() / ".agents" / "skills"

    @property
    def claude_skills_home(self) -> Path:
        return self.claude_home / "skills"


def default_paths(root: Path) -> BootstrapPaths:
    home = Path.home()
    return BootstrapPaths(
        root=root,
        codex_home=home / ".codex",
        claude_home=home / ".claude",
        cursor_home=home / ".cursor",
    )
