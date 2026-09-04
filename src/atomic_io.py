"""Same-directory atomic text writes with flush, fsync, and replace."""

from __future__ import annotations

import os
import shutil
import stat
import tempfile
from pathlib import Path

DEFAULT_FILE_MODE = 0o644
BACKUP_SUFFIX = ".agentbot-backup"


def write_text_atomic(
    path: Path,
    text: str,
    *,
    encoding: str = "utf-8",
    backup: bool = False,
) -> None:
    """Write ``text`` to ``path`` without leaving a truncated destination.

    The payload is completed in a same-directory temporary file, then moved
    onto ``path`` with ``os.replace``. A failure before replace leaves the
    original file untouched. ``backup=True`` copies an existing destination
    to ``{name}.agentbot-backup`` immediately before replace.
    """
    path = Path(path)
    if path.is_symlink():
        raise ValueError(f"refusing to write through a symlink: {path}")
    if path.exists() and not path.is_file():
        raise ValueError(f"destination is not a regular file: {path}")

    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.is_file()
    existing_mode = stat.S_IMODE(path.stat().st_mode) if existing else DEFAULT_FILE_MODE

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.agentbot-",
        dir=path.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding=encoding, newline="") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, existing_mode)
        if backup and existing:
            shutil.copy2(path, path.with_name(f"{path.name}{BACKUP_SUFFIX}"))
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    finally:
        if temporary.exists():
            temporary.unlink()
