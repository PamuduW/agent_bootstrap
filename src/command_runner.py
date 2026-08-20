from __future__ import annotations

import re
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

_ANSI_ESCAPE = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def _text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return value


def _redact(text: str, values: tuple[str, ...]) -> str:
    for value in values:
        text = text.replace(value, "[redacted]")
    return text


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False
    missing_executable: bool = False
    _redactions: tuple[str, ...] = field(default=(), repr=False, compare=False)

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    def detail(self, max_length: int = 240) -> str:
        if max_length <= 0:
            return ""
        lines: list[str] = []
        for output in (self.stdout, self.stderr):
            for raw_line in output.splitlines():
                line = _ANSI_ESCAPE.sub("", raw_line).strip()
                if line and not line.lower().startswith("npm notice"):
                    lines.append(line)
        if lines:
            detail = " | ".join(lines[-3:])
        elif self.timed_out:
            detail = "command timed out"
        elif self.missing_executable:
            detail = "executable not found"
        elif self.returncode:
            detail = f"exit code {self.returncode}"
        else:
            detail = "no diagnostic output"
        detail = _redact(detail, self._redactions)
        if len(detail) > max_length:
            if max_length <= 3:
                return detail[:max_length]
            return f"...{detail[-max_length + 3:]}"
        return detail


class CommandRunner:
    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path | str | None = None,
        timeout_seconds: float,
        env: Mapping[str, str] | None = None,
    ) -> CommandResult:
        if not argv or any(not isinstance(argument, str) for argument in argv):
            raise ValueError("argv must be a non-empty sequence of strings")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

        redactions = tuple(
            sorted(
                {value for value in (env or {}).values() if len(value) >= 4},
                key=len,
                reverse=True,
            )
        )
        try:
            completed = subprocess.run(
                list(argv),
                cwd=str(cwd) if cwd is not None else None,
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout_seconds,
                env=dict(env) if env is not None else None,
                shell=False,
            )
        except subprocess.TimeoutExpired as error:
            return CommandResult(
                124,
                _redact(_text(error.stdout), redactions),
                _redact(_text(error.stderr), redactions),
                timed_out=True,
                _redactions=redactions,
            )
        except FileNotFoundError:
            return CommandResult(
                127,
                stderr="executable not found",
                missing_executable=True,
                _redactions=redactions,
            )
        except OSError as error:
            message = error.strerror or error.__class__.__name__
            return CommandResult(
                126,
                stderr=f"unable to start process: {message}",
                _redactions=redactions,
            )
        return CommandResult(
            completed.returncode,
            _redact(completed.stdout, redactions),
            _redact(completed.stderr, redactions),
            _redactions=redactions,
        )
