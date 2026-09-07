"""VS Code host detection, extension reconciliation, and settings merging.

Remote-WSL splits one editor across two hosts, and they are not
interchangeable: extensions are installed per host, the Windows profile holds
the user-scope settings both hosts read, and the WSL server holds machine-scope
settings only the remote reads. Each host also has its own CLI, and picking the
wrong one silently mutates the other host -- `code` on ``PATH`` inside WSL is
the Windows executable reached through interop, so it is right for the Windows
host and wrong for the WSL one.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .atomic_io import write_text_atomic

WINDOWS_MOUNT_ROOT = Path("/mnt/c")

# "publisher.name-1.2.3" and "publisher.name-1.2.3-linux-x64" both identify
# "publisher.name". The version is the first hyphen-separated field that starts
# with a digit, which is what separates an id from a build suffix.
_EXTENSION_DIRECTORY = re.compile(r"^(?P<identifier>.+?)-\d+\.\d+\.\d+.*$")


@dataclass(frozen=True)
class VSCodeHost:
    """One extension host: where its settings live and how to drive its CLI."""

    name: str
    settings_path: Path
    extensions_dir: Path
    cli: Path | None
    detail: str

    @property
    def available(self) -> bool:
        return self.extensions_dir.is_dir()

    @property
    def can_install(self) -> bool:
        return self.available and self.cli is not None


@dataclass
class SettingsPlan:
    """What a settings merge would change, before anything is written."""

    path: Path
    additions: dict[str, object] = field(default_factory=dict)
    changes: dict[str, tuple[object, object]] = field(default_factory=dict)
    unreadable: str | None = None

    @property
    def is_noop(self) -> bool:
        return not self.additions and not self.changes


@dataclass
class ExtensionPlan:
    """Which extensions a host is missing. Never which ones to remove."""

    host: str
    missing: tuple[str, ...] = ()
    unmanaged: tuple[str, ...] = ()
    skipped: str | None = None

    @property
    def is_noop(self) -> bool:
        return not self.missing


def wsl_host(home: Path) -> VSCodeHost:
    """The WSL extension host, served from ~/.vscode-server."""
    server = home / ".vscode-server"
    return VSCodeHost(
        name="wsl",
        settings_path=server / "data" / "Machine" / "settings.json",
        extensions_dir=server / "extensions",
        cli=_newest_remote_cli(server),
        detail=str(server),
    )


def windows_host(mount_root: Path = WINDOWS_MOUNT_ROOT) -> VSCodeHost:
    """The Windows host, reached over the WSL mount.

    The profile is resolved by looking for exactly one VS Code user directory.
    Zero means VS Code is not installed on the Windows side; more than one means
    several Windows accounts, and guessing which one the operator meant would be
    a write into somebody's profile on a coin flip.
    """
    candidates = sorted((mount_root / "Users").glob("*/AppData/Roaming/Code/User"))
    if len(candidates) != 1:
        detail = (
            "no Windows VS Code profile found"
            if not candidates
            else f"{len(candidates)} Windows profiles found; cannot choose one"
        )
        return VSCodeHost(
            name="windows",
            settings_path=mount_root / "Users",
            extensions_dir=mount_root / "Users",
            cli=None,
            detail=detail,
        )
    user_dir = candidates[0]
    profile = user_dir.parents[3]
    return VSCodeHost(
        name="windows",
        settings_path=user_dir / "settings.json",
        extensions_dir=profile / ".vscode" / "extensions",
        cli=_windows_cli(mount_root),
        detail=str(profile),
    )


def _newest_remote_cli(server: Path) -> Path | None:
    """The remote CLI belonging to the most recently used server build.

    Never `code` from PATH: inside WSL that is the Windows executable, and
    using it here would install into the other host.
    """
    candidates = [
        candidate
        for candidate in server.glob("bin/*/bin/remote-cli/code")
        if candidate.is_file()
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _windows_cli(mount_root: Path) -> Path | None:
    for relative in (
        "Program Files/Microsoft VS Code/bin/code",
        "Program Files (x86)/Microsoft VS Code/bin/code",
    ):
        candidate = mount_root / relative
        if candidate.is_file():
            return candidate
    return None


def installed_extensions(host: VSCodeHost) -> tuple[str, ...]:
    """Extension ids present in a host's extensions directory.

    Read from disk rather than from `code --list-extensions`: the CLI is slow,
    needs the host to be runnable, and on the Windows side runs through interop.
    """
    if not host.available:
        return ()
    identifiers = set()
    for entry in host.extensions_dir.iterdir():
        if not entry.is_dir():
            continue
        matched = _EXTENSION_DIRECTORY.match(entry.name)
        if matched:
            identifiers.add(matched.group("identifier"))
    return tuple(sorted(identifiers))


def plan_extensions(host: VSCodeHost, desired: list[str]) -> ExtensionPlan:
    """Which desired extensions are absent from this host.

    Extensions present but unmanaged are reported, never removed: absence from
    the manifest is not a request to uninstall.
    """
    if not host.available:
        return ExtensionPlan(host=host.name, skipped=f"host unavailable ({host.detail})")
    present = set(installed_extensions(host))
    wanted = {identifier.strip() for identifier in desired if identifier.strip()}
    return ExtensionPlan(
        host=host.name,
        missing=tuple(sorted(wanted - present)),
        unmanaged=tuple(sorted(present - wanted)),
    )


def strip_jsonc(text: str) -> str:
    """JSONC with comments and trailing commas removed, for parsing only.

    The result is never written back; writes edit the original text in place so
    comments and formatting survive.
    """
    out: list[str] = []
    index = 0
    length = len(text)
    while index < length:
        character = text[index]
        if character == '"':
            end = _end_of_string(text, index)
            out.append(text[index:end])
            index = end
            continue
        if text.startswith("//", index):
            newline = text.find("\n", index)
            index = length if newline == -1 else newline
            continue
        if text.startswith("/*", index):
            close = text.find("*/", index + 2)
            index = length if close == -1 else close + 2
            continue
        out.append(character)
        index += 1
    without_comments = "".join(out)
    return re.sub(r",(\s*[}\]])", r"\1", without_comments)


def _end_of_string(text: str, start: int) -> int:
    index = start + 1
    while index < len(text):
        if text[index] == "\\":
            index += 2
            continue
        if text[index] == '"':
            return index + 1
        index += 1
    return len(text)


def read_settings(path: Path) -> tuple[dict, str | None]:
    """Parse a JSONC settings file. Returns (settings, error)."""
    if not path.is_file():
        return {}, None
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as error:
        return {}, f"cannot read {path}: {error}"
    stripped = strip_jsonc(raw).strip()
    if not stripped:
        return {}, None
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as error:
        return {}, f"cannot parse {path}: {error}"
    if not isinstance(parsed, dict):
        return {}, f"{path} is not a JSON object"
    return parsed, None


def plan_settings(path: Path, desired: dict[str, object]) -> SettingsPlan:
    existing, error = read_settings(path)
    if error:
        return SettingsPlan(path=path, unreadable=error)
    plan = SettingsPlan(path=path)
    for key, value in desired.items():
        if key not in existing:
            plan.additions[key] = value
        elif existing[key] != value:
            plan.changes[key] = (existing[key], value)
    return plan


def merge_settings_text(text: str, desired: dict[str, object]) -> str:
    """Apply owned keys to JSONC text, leaving everything else byte-identical.

    Values are replaced in place and new keys appended, rather than the file
    being re-serialised from a parsed object: re-serialising would silently
    delete every comment and reformat settings the operator wrote by hand.
    """
    if not desired:
        return text
    working = text if text.strip() else "{}"
    for key, value in desired.items():
        span = _top_level_value_span(working, key)
        rendered = json.dumps(value, indent=2)
        if span is None:
            working = _append_key(working, key, rendered)
        else:
            start, end = span
            working = working[:start] + rendered + working[end:]
    return working


def _top_level_value_span(text: str, key: str) -> tuple[int, int] | None:
    """Byte span of a top-level key's value, or None when the key is absent."""
    depth = 0
    index = 0
    length = len(text)
    while index < length:
        character = text[index]
        if character == '"':
            end = _end_of_string(text, index)
            if depth == 1:
                name = json.loads(strip_jsonc(text[index:end]))
                colon = _skip_to_colon(text, end)
                if colon is not None and name == key:
                    value_start = _skip_whitespace_and_comments(text, colon + 1)
                    return value_start, _end_of_value(text, value_start)
            index = end
            continue
        if text.startswith("//", index):
            newline = text.find("\n", index)
            index = length if newline == -1 else newline
            continue
        if text.startswith("/*", index):
            close = text.find("*/", index + 2)
            index = length if close == -1 else close + 2
            continue
        if character in "{[":
            depth += 1
        elif character in "}]":
            depth -= 1
        index += 1
    return None


def _skip_to_colon(text: str, index: int) -> int | None:
    position = _skip_whitespace_and_comments(text, index)
    if position < len(text) and text[position] == ":":
        return position
    return None


def _skip_whitespace_and_comments(text: str, index: int) -> int:
    length = len(text)
    while index < length:
        if text[index].isspace():
            index += 1
            continue
        if text.startswith("//", index):
            newline = text.find("\n", index)
            index = length if newline == -1 else newline
            continue
        if text.startswith("/*", index):
            close = text.find("*/", index + 2)
            index = length if close == -1 else close + 2
            continue
        break
    return index


def _end_of_value(text: str, start: int) -> int:
    if start >= len(text):
        return start
    if text[start] == '"':
        return _end_of_string(text, start)
    depth = 0
    index = start
    length = len(text)
    while index < length:
        character = text[index]
        if character == '"':
            index = _end_of_string(text, index)
            continue
        if character in "{[":
            depth += 1
        elif character in "}]":
            if depth == 0:
                return index
            depth -= 1
            if depth == 0:
                return index + 1
        elif character == "," and depth == 0:
            return index
        index += 1
    return length


def _append_key(text: str, key: str, rendered: str) -> str:
    close = text.rfind("}")
    if close == -1:
        return json.dumps({key: json.loads(rendered)}, indent=2) + "\n"
    # Match the file's own line ending. Settings written on the Windows side
    # are CRLF, and appending LF would leave one mixed line in an otherwise
    # consistent file the operator maintains by hand.
    newline = "\r\n" if "\r\n" in text else "\n"
    head = text[:close].rstrip()
    # A trailing comma before the closing brace is legal JSONC and common in
    # hand-written settings. A second one is legal nowhere, and appending it
    # broke every real file that had one.
    separator = "" if head.endswith(("{", ",")) else ","
    body = rendered.replace("\n", newline)
    entry = f"{separator}{newline}  {json.dumps(key)}: {body}{newline}"
    return head + entry + text[close:]


def apply_settings(path: Path, desired: dict[str, object]) -> SettingsPlan:
    """Merge owned keys into a settings file, backing the original up first."""
    plan = plan_settings(path, desired)
    if plan.unreadable or plan.is_noop:
        return plan
    original = path.read_text(encoding="utf-8") if path.is_file() else "{}\n"
    merged = merge_settings_text(original, desired)
    write_text_atomic(path, merged, backup=True)
    return plan
