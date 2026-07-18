from __future__ import annotations

import os
import re
import sys
import textwrap
from pathlib import Path

BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"
ORANGE = "\033[38;5;208m"

LABEL_W = 22
DETAIL_W = 40
RESULT_W = 10

ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def use_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR") or os.environ.get("AGENTBOT_TUI"):
        return True
    # Match dotfiles report_table: stdin may still be a TTY when stdout is piped (e.g. tee).
    return sys.stdout.isatty() or sys.stdin.isatty()


def _c(text: str, code: str) -> str:
    if not use_color():
        return text
    return f"{code}{text}{RESET}"


def strip_ansi(text: str) -> str:
    return ANSI_ESCAPE.sub("", text)


def shorten_detail(text: str, *, max_len: int = DETAIL_W) -> str:
    cleaned = strip_ansi(text).replace("\r", "")
    for line in cleaned.splitlines():
        line = line.strip()
        if not line or line == "skills" or "████" in line:
            continue
        if len(line) > max_len:
            return f"{line[: max_len - 3]}..."
        return line
    compact = " ".join(part for part in cleaned.split() if part)
    if len(compact) > max_len:
        return f"{compact[: max_len - 3]}..."
    return compact


def print_header(title: str, breadcrumb: str = "") -> None:
    print()
    print(f"  {_c(f'=== {title} ===', BOLD + ORANGE)}")
    if breadcrumb:
        print(f"  {_c(breadcrumb, DIM)}")
    print()


def print_section(label: str) -> None:
    print(f"  {_c(label, BOLD + YELLOW)}")


def color_result(result: str) -> str:
    key = result.strip().lower()
    if key in {"ok", "installed", "configured", "linked", "up to date", "current", "applied"}:
        return _c(result, GREEN)
    if key in {"missing", "failed", "error", "conflict"}:
        return _c(result, RED)
    if key.startswith("skipped") or key in {
        "check",
        "warn",
        "warning",
        "partial",
        "drift",
        "extra",
        "applied-with-local-changes",
    }:
        return _c(result, YELLOW)
    if key in {"info", "dry-run", "preview"}:
        return _c(result, CYAN)
    return result


def print_table_columns(*, headers: tuple[str, str, str] = ("component", "detail", "result")) -> None:
    h0, h1, h2 = headers
    print(f"  {_c(f'{h0:<{LABEL_W}} | {h1:<{DETAIL_W}} | {h2}', BOLD)}")
    print(
        f"  {'-' * LABEL_W}-+-{'-' * DETAIL_W}-+-{'-' * RESULT_W}"
    )


def print_table(
    rows: list[tuple[str, str, str]],
    *,
    headers: tuple[str, str, str] = ("component", "detail", "result"),
    show_header: bool = True,
    wrap_details: bool = False,
) -> tuple[int, int, int]:
    ok_count = check_count = miss_count = 0
    if show_header:
        print_table_columns(headers=headers)
    for label, detail, result in rows:
        if wrap_details:
            detail_lines: list[str] = []
            for paragraph in strip_ansi(detail).replace("\r", "").splitlines() or [""]:
                detail_lines.extend(
                    textwrap.wrap(
                        paragraph,
                        width=DETAIL_W,
                        break_long_words=False,
                        break_on_hyphens=False,
                    )
                    or [""]
                )
        else:
            detail_lines = [detail if len(detail) <= DETAIL_W else f"{detail[: DETAIL_W - 3]}..."]

        for line_number, detail_fit in enumerate(detail_lines):
            if line_number == 0:
                print(f"  {label:<{LABEL_W}} | {detail_fit:<{DETAIL_W}} | ", end="")
                print(color_result(result))
            else:
                print(f"  {'':<{LABEL_W}} | {detail_fit:<{DETAIL_W}} |")
        key = result.strip().lower()
        if key in {"ok", "installed", "configured", "linked", "up to date", "current"}:
            ok_count += 1
        elif key in {"missing", "failed", "error"}:
            miss_count += 1
        elif key.startswith("skipped"):
            continue
        else:
            check_count += 1
    return ok_count, check_count, miss_count


def print_rollup(*, ok: int, check: int, miss: int) -> None:
    print()
    if miss == 0 and check == 0:
        print(f"  {_c(f'All {ok} component(s) look good.', GREEN)}")
    elif miss == 0:
        print(
            f"  {_c(f'{ok} ok', GREEN)}, "
            f"{_c(f'{check} need attention', YELLOW)}."
        )
    else:
        print(
            f"  {_c(f'{ok} ok', GREEN)}, "
            f"{_c(f'{miss} missing', RED)}, "
            f"{_c(f'{check} need attention', YELLOW)}."
        )
    print()


def print_section_block(label: str) -> None:
    print()
    print_section(label)
    print()
    print_table_columns()


def print_status_summary(
    *,
    installed_skills: int,
    global_agents_exists: bool,
    skills_sources_exists: bool,
    enabled_sources: int = 0,
    global_lock_exists: bool = False,
    global_lock_skills: int = 0,
    claude_bridge_links: int = 0,
    manual_skill_count: int = 0,
    doctor_issue_count: int = 0,
) -> None:
    manifest_detail = "skills.sources.yaml"
    if enabled_sources >= 0 and skills_sources_exists:
        manifest_detail = f"{enabled_sources} enabled source(s)"
    elif enabled_sources < 0:
        manifest_detail = "skills.sources.yaml (parse error)"

    lock_detail = "~/.agents/.skill-lock.json"
    if global_lock_exists and global_lock_skills >= 0:
        lock_detail = f"~/.agents/.skill-lock.json ({global_lock_skills} pinned)"
    elif global_lock_exists:
        lock_detail = "~/.agents/.skill-lock.json (unreadable)"

    print_header("Status", "Agentbot › Status")
    print_section_block("── Skills & baseline ──")
    ok, check, miss = print_table(
        [
            ("Installed skills", str(installed_skills), "ok" if installed_skills else "check"),
            ("Global AGENTS.md", "global/AGENTS.md", "ok" if global_agents_exists else "missing"),
            ("Skills manifest", manifest_detail, "ok" if skills_sources_exists else "missing"),
            (
                "Global skill lock",
                lock_detail,
                "ok" if global_lock_exists and global_lock_skills != 0 else "check",
            ),
            (
                "Claude bridge",
                f"{claude_bridge_links} symlink(s)" if claude_bridge_links else "none",
                "ok" if claude_bridge_links else "check",
            ),
            (
                "Manual skills",
                f"{manual_skill_count} outside global lock" if manual_skill_count else "none",
                "info" if manual_skill_count else "ok",
            ),
            (
                "Doctor",
                "no issues" if doctor_issue_count == 0 else f"{doctor_issue_count} issue(s)",
                "ok" if doctor_issue_count == 0 else "check",
            ),
        ],
        show_header=False,
    )
    print_rollup(ok=ok, check=check, miss=miss)


def print_doctor_summary(issues: list) -> int:
    print_header("Doctor", "Agentbot › Doctor")
    if not issues:
        print_table(
            [("Health check", "skills + global baseline", "ok")],
            show_header=True,
        )
        print_rollup(ok=1, check=0, miss=0)
        return 0

    rows: list[tuple[str, str, str]] = []
    errors = 0
    warnings = 0
    for issue in issues:
        level = issue.level.lower()
        if level == "error":
            errors += 1
        else:
            warnings += 1
        result = "error" if level == "error" else "check"
        rows.append((issue.scope, issue.message, result))
    _ok, check, miss = print_table(rows, wrap_details=True)
    print()
    print(f"  {errors} error(s), {warnings} warning(s).")
    print_rollup(ok=0, check=check, miss=miss)
    return 1 if errors else 0


def print_skills_report(results: list, *, title: str) -> int:
    from .skills_installer import InstallResult, summarize_install_results

    summary = summarize_install_results(results)
    print_header(title, f"Agentbot › {title}")
    print_section_block("── Sources ──")
    rows: list[tuple[str, str, str]] = []
    for result in results:
        if not isinstance(result, InstallResult):
            continue
        if result.skipped:
            rows.append((result.source_id, "—", "skipped"))
            continue
        repo = result.command[3] if len(result.command) > 3 else ""
        if result.returncode == 0:
            rows.append((result.source_id, repo, "ok"))
            continue
        detail = shorten_detail(result.stderr or result.stdout or f"exit {result.returncode}")
        rows.append((result.source_id, detail, "failed"))

    if rows:
        ok, check, miss = print_table(rows, show_header=False)
    else:
        print(f"  {_c('No active skill sources configured.', DIM)}")
        ok = check = miss = 0

    print()
    if summary.failed:
        print(
            f"  {_c(str(summary.ok), GREEN)} ok, "
            f"{_c(str(summary.failed), RED)} failed, "
            f"{_c(str(summary.skipped), YELLOW)} skipped"
        )
        return 1 if summary.ok == 0 else 0
    print(f"  {_c(f'{summary.ok} source(s) installed successfully.', GREEN)}")
    if rows:
        print_rollup(ok=ok, check=check, miss=miss)
    return 0


def print_skills_update_report(*, linked: int, skipped: int = 0, updated: int = 0) -> int:
    print_section_block("── Refresh ──")
    bridge_detail = f"{linked} linked"
    if updated:
        bridge_detail += f", {updated} updated"
    if skipped:
        bridge_detail += f", {skipped} skipped"
    rows = [
        ("global lock", "~/.agents/.skill-lock.json", "ok"),
        ("claude bridge", bridge_detail, "ok"),
        ("codex sync", "~/.codex/AGENTS.md + skills", "ok"),
    ]
    ok, check, miss = print_table(rows)
    print()
    print_rollup(ok=ok, check=check, miss=miss)
    return 0


def print_reconciliation_report(result) -> None:
    """Render the final source-owned reconciliation outcome as a compact table."""
    changed = ", ".join(str(path) for path in result.changed_paths) or "none"
    added = ", ".join(result.added_skills) or "none"
    removed = ", ".join(result.removed_skills) or "none"
    print_section_block("── Reconciliation report ──")
    print_table(
        [
            ("status", "repository reconciliation", result.status),
            ("changed files", changed, str(len(result.changed_paths))),
            ("added skills", added, str(len(result.added_skills))),
            ("removed skills", removed, str(len(result.removed_skills))),
        ],
        show_header=False,
    )
    print()


def print_bridge_summary(*, linked: int, skipped: int, updated: int = 0) -> None:
    parts = [f"{linked} linked"]
    if updated:
        parts.append(f"{updated} updated")
    if skipped:
        parts.append(f"{skipped} skipped")
    print(f"  {_c('Claude skills bridge: ' + ', '.join(parts) + '.', CYAN)}")


def print_workspace_report(result) -> None:
    from .workspace_service import WorkspaceResult

    if not isinstance(result, WorkspaceResult):
        raise TypeError("expected WorkspaceResult")
    print_header("Workspace", "Agentbot › Workspace")
    print_section_block("── Render ──")
    rows: list[tuple[str, str, str]] = []
    for action in result.actions:
        rows.append((action.relative_path, action.detail, action.kind))
    if not rows:
        rows.append((str(result.path), result.message, result.status))
    print_table(rows, show_header=False, wrap_details=True)
    print()
    print(f"  {result.message}")


def print_workspace_resync_report(report) -> None:
    print_header("Workspace Resync", "Agentbot › Workspace Resync")
    print_section_block("── Workspaces ──")
    rows: list[tuple[str, str, str]] = []
    for result in report.results:
        if result.actions:
            for action in result.actions:
                rows.append(
                    (
                        f"{result.path}:{action.relative_path}",
                        action.detail,
                        action.kind,
                    )
                )
        else:
            rows.append((str(result.path), result.message, result.status))
    if rows:
        print_table(rows, show_header=False, wrap_details=True)
    else:
        print("  No registered workspaces.")
    print()


def print_workspace_list(records) -> None:
    print_header("Workspaces", "Agentbot › Workspaces")
    print_section_block("── Registered ──")
    if not records:
        print("  No registered workspaces.")
        print()
        return
    rows: list[tuple[str, str, str]] = []
    for record in records:
        exists = Path(record.path).is_dir()
        detail = (
            f"{record.kind}, {record.policy_mode}, profile={record.profile}, "
            f"targets={','.join(record.targets)}"
        )
        rows.append((record.path, detail, "ok" if exists and record.enabled else "missing"))
    print_table(rows, show_header=False, wrap_details=True)
    print()
