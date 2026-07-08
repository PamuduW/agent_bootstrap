from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BootstrapPaths:
    root: Path
    cursor_plugin_cache: Path
    codex_home: Path
    claude_home: Path
    cursor_home: Path

    @property
    def catalog_file(self) -> Path:
        return self.root / "catalog" / "packages.json"

    @property
    def global_agents(self) -> Path:
        return self.root / "global" / "AGENTS.md"

    @property
    def state_dir(self) -> Path:
        return self.root / "state"

    @property
    def state_file(self) -> Path:
        return self.state_dir / "operator_state.json"

    @property
    def audit_log(self) -> Path:
        return self.state_dir / "audit.log"

    @property
    def mcp_catalog(self) -> Path:
        return self.root / "mcp" / "mcp.json"

    @property
    def skills_dir(self) -> Path:
        return self.root / "skills"

    @property
    def rules_dir(self) -> Path:
        return self.root / "rules"

    @property
    def commands_dir(self) -> Path:
        return self.root / "commands"

    @property
    def agents_dir(self) -> Path:
        return self.root / "agents"

    @property
    def hooks_dir(self) -> Path:
        return self.root / "hooks"

    @property
    def skills_sources_file(self) -> Path:
        return self.root / "skills.sources.yaml"

    @property
    def skills_lock_file(self) -> Path:
        return self.root / "skills-lock.json"

    @property
    def exports_dir(self) -> Path:
        return self.root / "exports"

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
        cursor_plugin_cache=home / ".cursor" / "plugins" / "cache" / "cursor-public",
        codex_home=home / ".codex",
        claude_home=home / ".claude",
        cursor_home=home / ".cursor",
    )
