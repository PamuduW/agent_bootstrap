from __future__ import annotations

import os
import re
import shutil
import sys
import textwrap
from collections.abc import Callable
from pathlib import Path

from .commands import CommandSpec, commands_for_surface
from .models import Table, TableSection

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
MANUAL_SKILL_NAME = re.compile(r"(?<=Manual skill ')[^']+(?=')")


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


def terminal_columns() -> int:
    configured = os.environ.get("AGENTBOT_MENU_COLS", "")
    if configured.isdigit():
        return max(20, int(configured))
    if os.environ.get("AGENTBOT_TUI"):
        return max(20, shutil.get_terminal_size(fallback=(80, 24)).columns)
    return 80


def _fit_line(text: str, width: int) -> str:
    if len(text) <= width:
        return text
    if width <= 3:
        return text[:width]
    return f"{text[: width - 3]}..."


def _table_widths() -> tuple[int, int, int]:
    if not os.environ.get("AGENTBOT_TUI") and not os.environ.get("AGENTBOT_MENU_COLS"):
        return LABEL_W, DETAIL_W, RESULT_W
    available = max(12, min(terminal_columns(), 80) - 8)
    label_width = max(6, available * 29 // 100)
    result_width = max(5, available * 14 // 100)
    detail_width = max(1, available - label_width - result_width)
    return label_width, detail_width, result_width


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
    width = terminal_columns() - 2
    print()
    print(f"  {_c(_fit_line(f'=== {title} ===', width), BOLD + ORANGE)}")
    if breadcrumb:
        print(f"  {_c(_fit_line(breadcrumb, width), DIM)}")
    print()


def print_section(label: str) -> None:
    print(f"  {_c(_fit_line(label, terminal_columns() - 2), BOLD + YELLOW)}")


def color_result(result: str) -> str:
    key = result.strip().lower()
    if key in {"ok", "installed", "configured", "linked", "up to date", "current", "applied", "read-only"}:
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
        "mutating",
    }:
        return _c(result, YELLOW)
    if key in {"info", "dry-run", "preview"}:
        return _c(result, CYAN)
    return result


def highlight_manual_skill_name(detail: str, line: str) -> str:
    match = MANUAL_SKILL_NAME.search(strip_ansi(detail))
    if match is None:
        return line
    skill_name = match.group(0)
    return line.replace(skill_name, _c(skill_name, BOLD + CYAN))


def print_table_columns(*, headers: tuple[str, str, str] = ("component", "detail", "result")) -> None:
    h0, h1, h2 = headers
    label_width, detail_width, result_width = _table_widths()
    h0 = _fit_line(h0, label_width)
    h1 = _fit_line(h1, detail_width)
    h2 = _fit_line(h2, result_width)
    print(f"  {_c(f'{h0:<{label_width}} | {h1:<{detail_width}} | {h2}', BOLD)}")
    print(
        f"  {'-' * label_width}-+-{'-' * detail_width}-+-{'-' * result_width}"
    )


def print_table(
    rows: list[tuple[str, str, str]],
    *,
    headers: tuple[str, str, str] = ("component", "detail", "result"),
    show_header: bool = True,
    wrap_details: bool = False,
    detail_highlighter: Callable[[str, str], str] | None = None,
) -> tuple[int, int, int]:
    ok_count = check_count = miss_count = 0
    label_width, detail_width, _result_width = _table_widths()
    if show_header:
        print_table_columns(headers=headers)
    for label, detail, result in rows:
        if wrap_details:
            detail_lines: list[str] = []
            for paragraph in strip_ansi(detail).replace("\r", "").splitlines() or [""]:
                detail_lines.extend(
                    textwrap.wrap(
                        paragraph,
                        width=detail_width,
                        break_long_words=True,
                        break_on_hyphens=False,
                    )
                    or [""]
                )
        else:
            detail_lines = [_fit_line(detail, detail_width)]

        for line_number, detail_fit in enumerate(detail_lines):
            detail_padded = f"{detail_fit:<{detail_width}}"
            if detail_highlighter is not None:
                detail_padded = detail_highlighter(detail, detail_padded)
            if line_number == 0:
                label_fit = _fit_line(label, label_width)
                print(f"  {label_fit:<{label_width}} | {detail_padded} | ", end="")
                print(color_result(_fit_line(result, _result_width)))
            else:
                print(f"  {'':<{label_width}} | {detail_padded} |")
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


def table_rows(table: Table) -> list[dict[str, str]]:
    return [
        {"section": section.label, "component": component, "detail": detail, "result": result}
        for section in table.sections
        for component, detail, result in section.rows
    ]


def print_table_model(table: Table) -> tuple[int, int, int]:
    print_header(table.title, table.breadcrumb)
    total_ok = total_check = total_miss = 0
    for section in table.sections:
        print_section_block(section.label)
        ok, check, miss = print_table(list(section.rows), show_header=False)
        total_ok += ok
        total_check += check
        total_miss += miss
    print_rollup(ok=total_ok, check=total_check, miss=total_miss)
    return total_ok, total_check, total_miss


def print_command_help(spec: CommandSpec | None = None) -> None:
    if spec is None:
        print_header("Agentbot Help", "Agentbot › Help")
        print("  Usage: agentbot <command> [options]")
        for surface, label in (("public", "── Commands ──"), ("bootstrap", "── Bootstrap commands ──")):
            print()
            print_section(label)
            print()
            print_table(
                [(item.name, item.summary, item.behavior) for item in commands_for_surface(surface)],
                headers=("command", "description", "behavior"),
                wrap_details=True,
            )
        print()
        print_section("── Environment ──")
        print()
        print_table(
            [
                ("AGENTBOT_HOME", "Owning Agentbot repository root", "info"),
                ("XDG_CONFIG_HOME", "Base for private Agentbot state", "info"),
                ("GITHUB_TOKEN", "Optional GitHub API credential; never rendered", "info"),
                ("NO_COLOR", "Disable ANSI color output", "info"),
            ],
            headers=("variable", "purpose", "behavior"),
            wrap_details=True,
        )
        return

    print_header(spec.name, f"Agentbot › Help › {spec.name}")
    print_table(
        [
            ("Usage", spec.usage, spec.behavior),
            ("Purpose", spec.summary, "info"),
            ("Effects", spec.effects, spec.behavior),
        ],
        show_header=False,
        wrap_details=True,
    )
    if spec.options:
        print_section_block("── Options ──")
        print_table(
            [
                (item.usage, f"{item.description} Default: {item.default}.", "info")
                for item in spec.options
            ],
            show_header=False,
            wrap_details=True,
        )
    if spec.examples:
        print_section_block("── Examples ──")
        print_table(
            [("Example", example, "info") for example in spec.examples],
            show_header=False,
            wrap_details=True,
        )
    if spec.related:
        print()
        print(f"  Related: {', '.join(spec.related)}")


def print_status_summary(
    *,
    installed_skills: int,
    global_agents_exists: bool,
    skills_sources_exists: bool,
    enabled_sources: int = 0,
    global_lock_exists: bool = False,
    global_lock_skills: int = 0,
    claude_bridge_links: int = 0,
    claude_statusline_state: str = "unknown",
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

    table = Table(
        title="Check Status",
        breadcrumb="Agentbot › Check Status",
        sections=(
            TableSection(
                label="── Skills & baseline ──",
                rows=(
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
                "Claude statusline",
                claude_statusline_state,
                "ok" if claude_statusline_state == "ok" else "check",
            ),
            (
                "Manual skills",
                f"{manual_skill_count} outside managed sources" if manual_skill_count else "none",
                "info" if manual_skill_count else "ok",
            ),
            (
                "Doctor",
                "no issues" if doctor_issue_count == 0 else f"{doctor_issue_count} issue(s)",
                "ok" if doctor_issue_count == 0 else "check",
            ),
                ),
            ),
        ),
    )
    print_table_model(table)


def print_doctor_summary(issues: list, *, include_header: bool = True) -> int:
    if include_header:
        print_header("Doctor", "Agentbot › Doctor")
    else:
        print_section_block("── Doctor issues ──")
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
    _ok, check, miss = print_table(
        rows,
        wrap_details=True,
        detail_highlighter=highlight_manual_skill_name,
    )
    print()
    print(f"  {errors} error(s), {warnings} warning(s).")
    print_rollup(ok=0, check=check, miss=miss)
    return 1 if errors else 0


def print_graphify_status(status) -> None:
    """Render the Graphify integration state without performing repairs."""
    print_header("Graphify", "Agentbot › Graphify")
    cli_detail = str(status.cli_path) if status.cli_path else "not installed"
    skill_detail = str(status.skill_path)
    rows = [
        ("State", status.state, status.state),
        ("CLI", cli_detail, "ok" if status.cli_path else "missing"),
        ("CLI version", status.cli_version or "—", "ok" if status.cli_version else "check"),
        ("Agent Skills", skill_detail, "ok" if status.skill_path.is_file() else "missing"),
        ("Codex", status.codex_state, "ok" if status.codex_state == "linked" else "check"),
        ("Claude", status.claude_state, "ok" if status.claude_state == "linked" else "check"),
    ]
    print_table(rows)
    print()
    print(f"  {status.message}")


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
        repo = result.command[4] if len(result.command) > 4 else ""
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


def print_skills_update_report(
    *,
    linked: int,
    skipped: int = 0,
    updated: int = 0,
    updated_skills: tuple[str, ...] = (),
    upstream_deleted_skills: tuple[str, ...] = (),
) -> int:
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
    if updated_skills:
        rows.append(("updated skills", ", ".join(updated_skills), str(len(updated_skills))))
    if upstream_deleted_skills:
        rows.append(
            (
                "upstream deleted",
                ", ".join(upstream_deleted_skills),
                str(len(upstream_deleted_skills)),
            )
        )
    ok, check, miss = print_table(rows)
    print()
    print_rollup(ok=ok, check=check, miss=miss)
    return 0


def print_reconciliation_report(result) -> None:
    """Render the final source-owned reconciliation outcome as a compact table."""
    changed = ", ".join(str(path) for path in result.changed_paths) or "none"
    updated = ", ".join(result.updated_skills) or "none"
    added = ", ".join(result.added_skills) or "none"
    removed = ", ".join(result.removed_skills) or "none"
    print_section_block("── Reconciliation report ──")
    print_table(
        [
            ("status", "repository reconciliation", result.status),
            ("changed files", changed, str(len(result.changed_paths))),
            ("updated skills", updated, str(len(result.updated_skills))),
            ("added skills", added, str(len(result.added_skills))),
            ("removed skills", removed, str(len(result.removed_skills))),
        ],
        show_header=False,
        wrap_details=True,
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

    global_actions = getattr(report, "global_actions", ()) or ()
    print_section_block("── Global ──")
    if global_actions:
        global_rows = [
            (action.relative_path, action.detail, action.kind) for action in global_actions
        ]
        print_table(global_rows, show_header=False, wrap_details=True)
    else:
        print("  No global outputs planned.")
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


def print_workspace_removed(record) -> None:
    print_header("Workspace removed", "Agentbot › Workspaces › Remove")
    print(f"  Stopped managing: {record.path}")
    print("  No workspace files were changed.")


def print_update_plan(plan, *, command: str = "update") -> None:
    title = command.capitalize()
    print_header(f"Agentbot {command}", f"Agentbot › {title}")
    rows = [
        (
            "Skills",
            (
                f"{len(plan.reconcile.wildcard_additions)} add, "
                f"{len(plan.reconcile.wildcard_removals)} remove, "
                f"{len(plan.reconcile.explicit_missing)} missing"
            ),
            "preview",
        ),
        ("Graphify", plan.graphify_action, "preview"),
        (
            "Workspaces",
            f"{len(plan.workspace_report.results)} registered result(s)",
            "preview",
        ),
    ]
    print_table(rows)


def print_update_outcome(outcome) -> None:
    result = "ok" if outcome.status in {"applied", "applied-with-local-changes"} else outcome.status
    print_table([("Update", outcome.message or outcome.status, result)], wrap_details=True)
    print()
