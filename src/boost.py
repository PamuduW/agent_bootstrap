from __future__ import annotations

import fcntl
import json
import os
import re
import shutil
import stat
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, replace
from pathlib import Path

try:
    import tomllib  # type: ignore[import-not-found]
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 compatibility
    import tomli as tomllib  # type: ignore[import-not-found]

from .command_runner import CommandRunner
from .paths import AgentbotPaths


@dataclass(frozen=True)
class BoostStatus:
    state: str
    cli_path: Path | None
    cli_version: str | None
    config_path: Path
    upload_disabled: bool
    auto_update_disabled: bool
    claude_state: str
    codex_state: str
    graph_state: str
    message: str


DEFAULT_BOOST_TIMEOUT_SECONDS = 300
BOOST_TIMEOUT_ENV = "AGENTBOT_BOOST_TIMEOUT_SECONDS"
CONFIG_LOCK_TIMEOUT_SECONDS = 5.0
_CONFIG_LOCK_POLL_SECONDS = 0.05
_FORBIDDEN_PLAN_RE = re.compile(
    r"boost[ -]?graph|\bmcp\b|background (?:index|watch)|(?:^|[\s/])\.boost(?:/|$)",
    re.IGNORECASE | re.MULTILINE,
)


class BoostIntegration:
    """Configure and inspect Boost's Claude/Codex shell-output integration."""

    def __init__(self, paths: AgentbotPaths, *, runner: CommandRunner | None = None) -> None:
        self.paths = paths
        self._runner = runner or CommandRunner()

    @property
    def config_path(self) -> Path:
        return self.paths.codex_home.parent / ".boost" / "config.toml"

    @staticmethod
    def _timeout_seconds() -> int:
        raw = os.environ.get(BOOST_TIMEOUT_ENV, str(DEFAULT_BOOST_TIMEOUT_SECONDS))
        try:
            timeout = int(raw)
        except ValueError as error:
            raise ValueError(f"{BOOST_TIMEOUT_ENV} must be a positive integer") from error
        if timeout <= 0:
            raise ValueError(f"{BOOST_TIMEOUT_ENV} must be a positive integer")
        return timeout

    def status(self) -> BoostStatus:
        cli_path = self._find_cli()
        cli_version = self._cli_version(cli_path)
        upload_disabled, auto_update_disabled = self._config_flags()
        claude_state = self._claude_state()
        codex_state = self._codex_state()
        graph_state = "forbidden" if self._forbidden_graph_evidence() else "absent"

        if cli_path is None:
            state = "not-installed"
            message = "Boost CLI is not installed."
        elif graph_state == "forbidden":
            state = "forbidden"
            message = "Forbidden BoostGraph or MCP configuration is present."
        elif not upload_disabled or not auto_update_disabled:
            state = "unsafe-config"
            message = "Boost privacy or update pinning is not safely configured."
        elif claude_state == "missing" and codex_state == "missing":
            state = "cli-only"
            message = "Boost CLI is installed; Claude and Codex are not integrated."
        elif claude_state == "unregistered":
            state = "partial"
            message = (
                "Boost hook files are installed for Claude but not registered in "
                "settings.json, so nothing is filtered. Rerun 'agentbot boost setup'."
            )
        elif claude_state != "ready" or codex_state != "ready":
            state = "partial"
            message = "Boost integration is incomplete for Claude or Codex."
        else:
            state = "ready"
            message = "Boost shell-output integration is ready for Claude and Codex."

        return BoostStatus(
            state,
            cli_path,
            cli_version,
            self.config_path,
            upload_disabled,
            auto_update_disabled,
            claude_state,
            codex_state,
            graph_state,
            message,
        )

    @contextmanager
    def _config_lock(self) -> Iterator[None]:
        """Hold Boost's own config lock across the read-modify-write.

        Boost rewrites config.toml on its own schedule to refresh remote feature
        flags, and guards it with this zero-byte lock file. Writing without the
        lock means whichever process calls os.replace last wins, silently
        dropping either our safety keys or Boost's flags.
        """
        lock_path = self.config_path.with_name(f"{self.config_path.name}.lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + CONFIG_LOCK_TIMEOUT_SECONDS
        with open(lock_path, "a+", encoding="utf-8") as handle:
            while True:
                try:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise ValueError(
                            f"Could not acquire the Boost config lock at {lock_path}; "
                            "another Boost process is holding it. Retry once it exits."
                        ) from None
                    time.sleep(_CONFIG_LOCK_POLL_SECONDS)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def ensure_safe_config(self) -> None:
        with self._config_lock():
            self._ensure_safe_config_locked()

    def _ensure_safe_config_locked(self) -> None:
        path = self.config_path
        existing = path.read_text(encoding="utf-8") if path.is_file() else ""
        if path.exists() and (path.is_symlink() or not path.is_file()):
            raise ValueError(f"Boost config is not a regular file: {path}")
        if existing:
            try:
                tomllib.loads(existing)
            except tomllib.TOMLDecodeError as error:
                raise ValueError(f"Boost config is invalid TOML: {error}") from error

        updated = self._set_section_bool(existing, "tracing", "upload", False)
        updated = self._set_section_bool(updated, "update", "auto_update", False)
        parsed = tomllib.loads(updated)
        if parsed.get("tracing", {}).get("upload") is not False:
            raise ValueError("Boost tracing.upload could not be disabled")
        if parsed.get("update", {}).get("auto_update") is not False:
            raise ValueError("Boost update.auto_update could not be disabled")
        if updated == existing:
            return

        path.parent.mkdir(parents=True, exist_ok=True)
        original_mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o600
        temporary_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", dir=path.parent, prefix=".config.toml.", delete=False
            ) as handle:
                temporary_name = handle.name
                handle.write(updated)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary_name, original_mode)
            os.replace(temporary_name, path)
        finally:
            if temporary_name is not None:
                Path(temporary_name).unlink(missing_ok=True)

    def setup(self) -> BoostStatus:
        current = self.status()
        if current.cli_path is None:
            return replace(
                current,
                message=(
                    "Boost CLI is not installed. Select Boost CLI in Dotfiles setup, "
                    "then rerun agentbot install."
                ),
            )
        if current.state == "forbidden":
            return current
        self.ensure_safe_config()
        base = [
            str(current.cli_path),
            "init",
            "--no-boostgraph",
            "--claude",
            "--codex",
        ]
        dry_run = self._runner.run(
            [*base[:2], "--dry-run", *base[2:]],
            timeout_seconds=self._timeout_seconds(),
        )
        if dry_run.returncode != 0:
            return replace(
                self.status(),
                state="broken",
                message=f"Boost dry run failed: {dry_run.detail()}",
            )
        plan = f"{dry_run.stdout}\n{dry_run.stderr}"
        if _FORBIDDEN_PLAN_RE.search(plan):
            return replace(
                self.status(),
                state="broken",
                message="Boost dry run contains forbidden BoostGraph, MCP, or indexing behavior.",
            )
        if "Claude" not in plan or "Codex" not in plan:
            return replace(
                self.status(),
                state="broken",
                message="Boost dry run did not include both requested Claude and Codex targets.",
            )
        result = self._runner.run_interactive(
            base,
            timeout_seconds=self._timeout_seconds(),
        )
        if result.returncode != 0:
            return replace(
                self.status(),
                state="broken",
                message=f"Boost setup failed: {result.detail()}",
            )
        return self.status()

    def setup_if_cli_available(self) -> BoostStatus:
        current = self.status()
        return current if current.cli_path is None else self.setup()

    def off(self) -> BoostStatus:
        current = self.status()
        if current.cli_path is None:
            return current
        # Asymmetric with setup: `init` accepts several targets at once, but
        # `init --uninstall` rejects more than one ("specify only one target to
        # uninstall"). Remove them one at a time, each behind its own dry run.
        #
        # Boost v0.12.6 resolves `--uninstall --claude` paths relative to the
        # working directory even though install is always global, so running it
        # from a repository deletes `<repo>/.claude/...` and leaves the real
        # `~/.claude` integration in place. `--codex` is unaffected. Pin cwd to
        # the home directory so the rollback hits what setup actually wrote.
        home = self.paths.codex_home.parent
        for target in ("--claude", "--codex"):
            base = [
                str(current.cli_path),
                "init",
                "--uninstall",
                "--no-boostgraph",
                target,
            ]
            dry_run = self._runner.run(
                [*base[:2], "--dry-run", *base[2:]],
                timeout_seconds=self._timeout_seconds(),
                cwd=home,
            )
            if dry_run.returncode != 0:
                return replace(
                    self.status(),
                    state="broken",
                    message=(
                        f"Boost integration removal dry run failed for {target}: "
                        f"{dry_run.detail()}"
                    ),
                )
            result = self._runner.run_interactive(
                base,
                timeout_seconds=self._timeout_seconds(),
                cwd=home,
            )
            if result.returncode != 0:
                return replace(
                    self.status(),
                    state="broken",
                    message=(
                        f"Boost integration removal failed for {target}: {result.detail()}"
                    ),
                )
        return self.status()

    def _find_cli(self) -> Path | None:
        command = shutil.which("boost")
        if command:
            return Path(command)
        fallback = self.paths.codex_home.parent / ".local" / "bin" / "boost"
        return fallback if fallback.is_file() and os.access(fallback, os.X_OK) else None

    def _cli_version(self, cli_path: Path | None) -> str | None:
        if cli_path is None:
            return None
        result = self._runner.run(
            [str(cli_path), "version"],
            timeout_seconds=self._timeout_seconds(),
        )
        if result.returncode != 0:
            return None
        output = (result.stdout or result.stderr).strip()
        return output.splitlines()[0] if output else None

    def _config_flags(self) -> tuple[bool, bool]:
        try:
            parsed = tomllib.loads(self.config_path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            return False, False
        return (
            parsed.get("tracing", {}).get("upload") is False,
            parsed.get("update", {}).get("auto_update") is False,
        )

    def _claude_state(self) -> str:
        required = (
            self.paths.claude_home / "hooks" / "boost-hook-claude.sh",
            self.paths.claude_home / "rules" / "boost-awareness.md",
        )
        if not all(path.is_file() for path in required):
            return "missing"
        # The hook scripts existing is not the same as Claude running them.
        # Boost's rewrite filter only takes effect once the hook is registered
        # under `hooks` in settings.json, so check the registration too --
        # otherwise an inert install reports "ready". This mirrors the
        # hooks.json check `_codex_state` already does.
        return "ready" if self._claude_hook_registered() else "unregistered"

    def _claude_hook_registered(self) -> bool:
        try:
            raw = (self.paths.claude_home / "settings.json").read_text(encoding="utf-8")
            hooks = json.loads(raw).get("hooks")
        except (OSError, json.JSONDecodeError, AttributeError):
            return False
        if not isinstance(hooks, dict) or not hooks:
            return False
        # Claude nests hooks as event -> matchers -> hooks -> command, and the
        # shape has changed before. Scan the serialized subtree for the hook
        # name rather than hard-coding a traversal that a schema change breaks.
        return "boost-hook-claude" in json.dumps(hooks)

    def _codex_state(self) -> str:
        required = (
            self.paths.codex_home / "hooks" / "boost-hook-codex.sh",
            self.paths.codex_home / "hooks" / "boost-sync.sh",
            self.paths.codex_home / "hooks.json",
            self.paths.codex_home / "BOOST.md",
        )
        return "ready" if all(path.is_file() for path in required) else "missing"

    def _forbidden_graph_evidence(self) -> bool:
        candidates = (
            self.paths.claude_home / "settings.json",
            self.paths.claude_home.parent / ".claude.json",
            self.paths.codex_home / "config.toml",
            self.paths.codex_home / "hooks.json",
        )
        for path in candidates:
            try:
                content = path.read_text(encoding="utf-8")
            except OSError:
                continue
            if re.search(r"boost[ -]?graph|boostgraph_explore", content, re.IGNORECASE):
                return True
        return False

    @staticmethod
    def _set_section_bool(content: str, section: str, key: str, value: bool) -> str:
        rendered = "true" if value else "false"
        lines = content.splitlines(keepends=True)
        section_start: int | None = None
        section_end = len(lines)
        header_re = re.compile(r"^\s*\[([^]]+)]\s*(?:#.*)?(?:\r?\n)?$")
        key_re = re.compile(rf"^(\s*){re.escape(key)}\s*=.*?(\r?\n)?$")
        for index, line in enumerate(lines):
            match = header_re.match(line)
            if not match:
                continue
            if section_start is not None:
                section_end = index
                break
            if match.group(1).strip() == section:
                section_start = index
        if section_start is None:
            prefix = content
            if prefix and not prefix.endswith("\n"):
                prefix += "\n"
            if prefix and not prefix.endswith("\n\n"):
                prefix += "\n"
            return f"{prefix}[{section}]\n{key} = {rendered}\n"
        for index in range(section_start + 1, section_end):
            match = key_re.match(lines[index])
            if match:
                newline = match.group(2) or ""
                lines[index] = f"{match.group(1)}{key} = {rendered}{newline}"
                return "".join(lines)
        lines.insert(section_end, f"{key} = {rendered}\n")
        return "".join(lines)
