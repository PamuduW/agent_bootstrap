from __future__ import annotations

import json
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from src.paths import AgentbotPaths


def agentbot_paths(root: Path) -> AgentbotPaths:
    home = root / "home"
    return AgentbotPaths(
        root=root,
        codex_home=home / ".codex",
        claude_home=home / ".claude",
        cursor_home=home / ".cursor",
        config_home=home / ".config" / "agentbot",
        # Explicit, so isolation never depends on when HOME was patched.
        agents_home=home / ".agents",
    )


@contextmanager
def isolated_agentbot_paths() -> Iterator[tuple[Path, AgentbotPaths]]:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary) / "agent_bootstrap"
        root.mkdir()
        yield root, agentbot_paths(root)


@contextmanager
def temporary_git_workspace() -> Iterator[Path]:
    with tempfile.TemporaryDirectory() as temporary:
        workspace = Path(temporary) / "workspace"
        workspace.mkdir()
        subprocess.run(
            ["git", "init", "--quiet", "--initial-branch=main", str(workspace)],
            check=True,
            capture_output=True,
            text=True,
        )
        yield workspace


def write_skills_manifest(root: Path, *, sources: str = "sources: []\n") -> Path:
    manifest = root / "skills.sources.yaml"
    manifest.write_text(
        f"version: 1\nagents: [cursor, codex, claude-code]\nscope: global\n{sources}",
        encoding="utf-8",
    )
    return manifest


def write_global_lock(paths: AgentbotPaths, skills: dict[str, object]) -> Path:
    paths.global_skill_lock.parent.mkdir(parents=True, exist_ok=True)
    paths.global_skill_lock.write_text(json.dumps({"skills": skills}, indent=2), encoding="utf-8")
    return paths.global_skill_lock


def create_skill(paths: AgentbotPaths, name: str, *, body: str | None = None) -> Path:
    skill = paths.agents_skills_home / name
    skill.mkdir(parents=True, exist_ok=True)
    (skill / "SKILL.md").write_text(body or f"# {name}\n", encoding="utf-8")
    return skill
