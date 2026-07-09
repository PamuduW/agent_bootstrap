from __future__ import annotations

import os
import re
import sys

BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"

ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def use_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty()


def _c(text: str, code: str) -> str:
    if not use_color():
        return text
    return f"{code}{text}{RESET}"


def strip_ansi(text: str) -> str:
    return ANSI_ESCAPE.sub("", text)


def shorten_detail(text: str, *, max_len: int = 72) -> str:
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
    print(f"  {_c(f'=== {title} ===', BOLD)}")
    if breadcrumb:
        print(f"  {_c(breadcrumb, DIM)}")
    print()


def color_result(result: str) -> str:
    key = result.strip().lower()
    if key in {"ok", "installed", "configured", "linked", "up to date"}:
        return _c(result, GREEN)
    if key in {"missing", "failed", "error"}:
        return _c(result, RED)
    if key.startswith("skipped") or key in {"check", "warn", "warning", "partial"}:
        return _c(result, YELLOW)
    if key in {"info", "dry-run"}:
        return _c(result, CYAN)
    return result


def print_table(
    rows: list[tuple[str, str, str]],
    *,
    headers: tuple[str, str, str],
) -> None:
    label_w, detail_w, result_w = 22, 28, 10
    h0, h1, h2 = headers
    print(f"{h0:<{label_w}} | {h1:<{detail_w}} | {h2}")
    print(f"{'-' * label_w}-+-{'-' * detail_w}-+-{'-' * result_w}")
    for label, detail, result in rows:
        detail_fit = detail if len(detail) <= detail_w else f"{detail[: detail_w - 3]}..."
        print(f"{label:<{label_w}} | {detail_fit:<{detail_w}} | ", end="")
        print(color_result(result))


def print_status_summary(
    *,
    managed: int,
    detected: int,
    enabled: int,
    tracked_workspaces: int,
) -> None:
    print_header("Status", "agent_bootstrap")
    print_table(
        [
            ("Managed packages", str(managed), "ok"),
            ("Detected packages", str(detected), "ok"),
            ("Enabled packages", str(enabled), "ok"),
            ("Tracked workspaces", str(tracked_workspaces), "ok"),
        ],
        headers=("check", "detail", "result"),
    )


def print_doctor_summary(issues: list) -> int:
    print_header("Doctor", "agent_bootstrap")
    if not issues:
        print(f"  {_c('No issues found.', GREEN)}")
        print()
        return 0
    print(f"  {_c(f'Found {len(issues)} issue(s):', YELLOW)}")
    print()
    for issue in issues:
        level = issue.level.upper()
        print(f"  [{level}] {issue.scope}: {issue.message}")
    print()
    return 1


def print_skills_report(results: list, *, title: str) -> int:
    from .skills_installer import InstallResult, summarize_install_results

    summary = summarize_install_results(results)
    print_header(title, "agent_bootstrap › skills")

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
        print_table(rows, headers=("source", "detail", "result"))
    else:
        print(f"  {_c('No active skill sources configured.', DIM)}")

    print()
    if summary.failed:
        print(
            f"  {_c(str(summary.ok), GREEN)} ok, "
            f"{_c(str(summary.failed), RED)} failed, "
            f"{_c(str(summary.skipped), YELLOW)} skipped"
        )
        return 1 if summary.ok == 0 else 0
    print(f"  {_c(f'{summary.ok} source(s) installed successfully.', GREEN)}")
    return 0


def print_bridge_summary(*, linked: int, skipped: int, updated: int = 0) -> None:
    parts = [f"{linked} linked"]
    if updated:
        parts.append(f"{updated} updated")
    if skipped:
        parts.append(f"{skipped} skipped")
    print(f"  {_c('Claude skills bridge: ' + ', '.join(parts) + '.', CYAN)}")
