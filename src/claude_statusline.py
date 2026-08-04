"""Install Claude Code statusline script and settings during global render."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

from .paths import AgentbotPaths

MANAGED_MARKER = "# Managed by Agentbot."
STATUSLINE_SCRIPT_NAME = "statusline-command.sh"
STATUSLINE_SETTINGS_COMMAND = f"~/.claude/{STATUSLINE_SCRIPT_NAME}"


def statusline_source(paths: AgentbotPaths) -> Path:
    return paths.root / "global" / "claude" / STATUSLINE_SCRIPT_NAME


def install_claude_statusline(paths: AgentbotPaths) -> None:
    """Install managed ~/.claude/statusline-command.sh and wire settings.json."""
    source = statusline_source(paths)
    if not source.is_file():
        return

    desired = source.read_text(encoding="utf-8")
    if not desired.endswith("\n"):
        desired += "\n"

    paths.claude_home.mkdir(parents=True, exist_ok=True)
    destination = paths.claude_home / STATUSLINE_SCRIPT_NAME
    _sync_statusline_script(destination, desired)
    _ensure_statusline_settings(paths.claude_home / "settings.json")


def _sync_statusline_script(destination: Path, desired: str) -> None:
    if destination.is_symlink():
        raise ValueError(f"claude statusline script is a symlink: {destination}")
    if destination.exists() and not destination.is_file():
        raise ValueError(f"claude statusline script is not a regular file: {destination}")

    if destination.is_file():
        existing = destination.read_text(encoding="utf-8")
        if MANAGED_MARKER not in existing and existing != desired:
            # Preserve a user-authored script that Agentbot does not own.
            _ensure_executable(destination)
            return
        if existing != desired:
            destination.write_text(desired, encoding="utf-8")
    else:
        destination.write_text(desired, encoding="utf-8")

    _ensure_executable(destination)


def _ensure_executable(path: Path) -> None:
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _ensure_statusline_settings(settings_path: Path) -> None:
    """Merge statusLine into settings.json without clobbering unrelated keys."""
    if settings_path.is_symlink():
        raise ValueError(f"claude settings is a symlink: {settings_path}")
    if settings_path.exists() and not settings_path.is_file():
        raise ValueError(f"claude settings is not a regular file: {settings_path}")

    data: dict = {}
    if settings_path.is_file():
        try:
            loaded = json.loads(settings_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"claude settings is not valid JSON: {settings_path}") from exc
        if not isinstance(loaded, dict):
            raise ValueError(f"claude settings root must be an object: {settings_path}")
        data = loaded

    desired_block = {
        "type": "command",
        "command": STATUSLINE_SETTINGS_COMMAND,
    }
    existing = data.get("statusLine")
    if isinstance(existing, dict):
        command = str(existing.get("command") or "")
        if command and not _is_managed_statusline_command(command):
            # User already pointed statusLine elsewhere; leave it alone.
            return
        if existing.get("type") == desired_block["type"] and command in {
            STATUSLINE_SETTINGS_COMMAND,
            os.path.expanduser(STATUSLINE_SETTINGS_COMMAND),
        }:
            # Keep optional fields (padding, etc.) but ensure type/command.
            merged = dict(existing)
            merged.update(desired_block)
            if merged == existing:
                return
            data["statusLine"] = merged
        else:
            data["statusLine"] = {**existing, **desired_block}
    else:
        data["statusLine"] = desired_block

    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _is_managed_statusline_command(command: str) -> bool:
    expanded = os.path.expanduser(command.strip())
    managed = os.path.expanduser(STATUSLINE_SETTINGS_COMMAND)
    if expanded == managed:
        return True
    # Accept "bash ~/.claude/statusline-command.sh" style wrappers.
    return expanded.endswith(f"/{STATUSLINE_SCRIPT_NAME}") or expanded.endswith(
        STATUSLINE_SCRIPT_NAME
    )
