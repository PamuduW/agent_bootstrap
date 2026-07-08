from __future__ import annotations

import argparse
import os
import sys
import termios
import tty
from contextlib import contextmanager
from pathlib import Path

from .paths import BootstrapPaths, default_paths
from .models import PackageRow
from .service import BootstrapService

BOLD = "\033[1m"
DIM = "\033[2m"
REVERSE = "\033[7m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
NC = "\033[0m"


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    paths = default_paths(Path(args.root))
    service = BootstrapService(paths)

    try:
        command = args.command or "interactive"
        if command == "interactive":
            return run_interactive(service)
        if command == "status":
            print_status(service)
            return 0
        if command == "global":
            service.render_global()
            return 0
        if command == "workspace":
            workspace = Path(args.path).resolve()
            service.track_and_render_workspace(workspace)
            return 0
        if command == "all":
            apply_all_under(service, Path(args.path).resolve())
            return 0
        if command == "import-local":
            service.import_from_local(args.path)
            return 0
        if command == "remove-managed":
            service.remove_managed_package(args.path)
            return 0
        if command == "delete-local":
            service.delete_local_package(args.path)
            return 0
        if command == "doctor":
            return print_doctor(service)
        if command == "bootstrap":
            return run_bootstrap_command(service, paths)
        if command == "skills":
            return handle_skills_command(service, args.skills_command)
        raise SystemExit(f"unknown command: {command}")
    except (ValueError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent_bootstrap")
    parser.add_argument("--root", dest="root", default=str(Path(__file__).resolve().parents[2]))
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("interactive", help="Interactive TUI (default when no command is given)")
    subparsers.add_parser("status", help="Show current control-plane state")
    subparsers.add_parser("global", help="Render global outputs")
    subparsers.add_parser("bootstrap", help="Run full fresh-machine bootstrap flow")

    workspace = subparsers.add_parser("workspace", help="Track and render a workspace")
    workspace.add_argument("path")

    all_cmd = subparsers.add_parser("all", help="Render all git repos under a parent directory")
    all_cmd.add_argument("path")

    import_local = subparsers.add_parser("import-local", help="Import a package from local cache")
    import_local.add_argument("path", help="Package id")

    remove_managed = subparsers.add_parser("remove-managed", help="Remove a managed package from this repo")
    remove_managed.add_argument("path", help="Package id")

    delete_local = subparsers.add_parser("delete-local", help="Delete a package from local cache")
    delete_local.add_argument("path", help="Package id")

    subparsers.add_parser("doctor", help="Validate tracked workspaces and catalog state")

    skills = subparsers.add_parser("skills", help="Install and manage curated skills")
    skills_sub = skills.add_subparsers(dest="skills_command", required=True)
    skills_sub.add_parser("install", help="Install skills from skills.sources.yaml")
    skills_sub.add_parser("update", help="Update skills from skills.sources.yaml")
    skills_sub.add_parser("list", help="List installed skills under ~/.agents/skills")
    skills_sub.add_parser("doctor", help="Validate skills sources and tooling")

    return parser


def handle_skills_command(service: BootstrapService, skills_command: str) -> int:
    if skills_command == "install":
        service.install_skills()
        return 0
    if skills_command == "update":
        service.update_skills()
        return 0
    if skills_command == "list":
        skills = service.list_skills()
        if not skills:
            print("No installed skills found.")
            return 0
        print("\n=== Installed Skills ===")
        for skill in skills:
            print(skill)
        return 0
    if skills_command == "doctor":
        return print_skills_doctor(service)
    raise SystemExit(f"unknown skills command: {skills_command}")


def run_bootstrap_command(service: BootstrapService, paths: BootstrapPaths) -> int:
    exit_code = service.run_bootstrap()
    print(f"AGENT_BOOTSTRAP_HOME={paths.root.resolve()}")
    return exit_code


def print_skills_doctor(service: BootstrapService) -> int:
    issues = service.skills_doctor_issues()
    print("\n=== Skills Doctor ===")
    if not issues:
        print("No issues found.")
        return 0
    print(f"Found {len(issues)} issue(s):")
    for issue in issues:
        print(f"- [{issue.level.upper()}] {issue.scope}: {issue.message}")
    return 1


def move_cursor(index: int, direction: str, count: int) -> int:
    if count <= 0:
        return 0
    if direction == "up":
        return max(0, index - 1)
    if direction == "down":
        return min(count - 1, index + 1)
    return index


def workspace_menu_rows(tracked_workspaces: list[str]) -> list[dict[str, str]]:
    rows = [{"id": f"workspace:{workspace}", "label": workspace} for workspace in tracked_workspaces]
    rows.extend(
        [
            {"id": "action:add", "label": "Add workspace"},
            {"id": "action:remove", "label": "Remove selected workspace"},
            {"id": "action:back", "label": "Back"},
        ]
    )
    return rows


def resolve_workspace_target(rows: list[dict[str, str]], cursor: int, last_workspace_index: int) -> str | None:
    if not rows:
        return None
    selected = rows[cursor]
    if selected["id"].startswith("workspace:"):
        return selected["label"]
    workspace_rows = [row for row in rows if row["id"].startswith("workspace:")]
    if not workspace_rows:
        return None
    index = max(0, min(last_workspace_index, len(workspace_rows) - 1))
    return workspace_rows[index]["label"]


def package_menu_rows(service: BootstrapService) -> list[dict[str, str]]:
    overview = service.build_overview()
    rows = []
    for row in overview.package_rows:
        managed = "M" if row.managed else " "
        detected_local = "L" if row.detected_local else " "
        detected_repo = "R" if row.detected_repo else " "
        enabled = "x" if row.enabled else " "
        label = f"[{managed}] [{detected_local}] [{detected_repo}] [{enabled}] {row.package_id}"
        rows.append({"id": f"package:{row.package_id}", "label": label})
    return rows


def package_action_rows(row: PackageRow) -> list[dict[str, str]]:
    actions = [
        {"id": "action:toggle", "label": "Toggle enabled"},
    ]
    if row.detected_local:
        label = "Import or refresh from local cache"
        if row.managed:
            label = "Refresh managed copy from local cache"
        actions.append({"id": "action:import-local", "label": label})
        if not row.managed:
            actions.append({"id": "action:delete-local", "label": "Delete local cache copy"})
    if row.managed:
        actions.append({"id": "action:remove-managed", "label": "Remove managed package from this repo"})
    actions.append({"id": "action:back", "label": "Back"})
    return actions


def run_interactive(service: BootstrapService) -> int:
    if not sys.stdin.isatty():
        print_status(service)
        return 0

    menu_items = [
        ("Packages", "Manage curated package enablement"),
        ("Workspaces", "Track repo overlays and outputs"),
        ("Apply", "Render global and tracked workspace outputs"),
        ("Status", "Show current control-plane state"),
        ("Doctor", "Validate tracked workspaces and catalog state"),
        ("Quit", "Exit"),
    ]
    cursor = 0

    with terminal_ui():
        while True:
            lines = ["", f"  {BOLD}=== Agent Bootstrap v2 ==={NC}", "  ↑/↓ navigate   Enter select   q quit", ""]
            for index, (label, desc) in enumerate(menu_items):
                prefix = ">" if index == cursor else " "
                if index == cursor:
                    lines.append(
                        f"  {BOLD}{prefix} {index + 1}) {REVERSE}{label:<12}{NC}{BOLD}  {DIM}{desc}{NC}"
                    )
                else:
                    lines.append(f"    {index + 1}) {label:<12}  {DIM}{desc}{NC}")
            draw_screen(lines)

            key = read_key()
            if key == "up":
                cursor = move_cursor(cursor, "up", len(menu_items))
            elif key == "down":
                cursor = move_cursor(cursor, "down", len(menu_items))
            elif key in {"q", "escape"}:
                return 0
            elif key == "enter":
                label = menu_items[cursor][0]
                if label == "Packages":
                    run_package_menu(service)
                elif label == "Workspaces":
                    run_workspace_menu(service)
                elif label == "Apply":
                    try:
                        service.apply_all()
                    except (ValueError, OSError) as error:
                        flash_message(f"Error: {error}")
                    else:
                        flash_message("Applied global and tracked workspace outputs.")
                elif label == "Status":
                    run_status_screen(service)
                elif label == "Doctor":
                    run_doctor_screen(service)
                elif label == "Quit":
                    return 0


def run_package_menu(service: BootstrapService) -> None:
    cursor = 0
    while True:
        rows = package_menu_rows(service)
        lines = [
            "",
            f"  {BOLD}=== Packages ==={NC}",
            "  ↑/↓ navigate   Enter actions   q back",
            "",
        ]
        for index, row in enumerate(rows):
            prefix = ">" if index == cursor else " "
            if index == cursor:
                lines.append(f"  {BOLD}{prefix} {index + 1:2d}. {REVERSE}{row['label']}{NC}")
            else:
                lines.append(f"    {index + 1:2d}. {row['label']}")
        lines.extend(
            [
                "",
                f"  {CYAN}Legend: M=managed, L=detected local, R=detected repo, x=enabled{NC}",
            ]
        )
        draw_screen(lines)

        key = read_key()
        if key == "up":
            cursor = move_cursor(cursor, "up", len(rows))
        elif key == "down":
            cursor = move_cursor(cursor, "down", len(rows))
        elif key in {"q", "escape"}:
            return
        elif key == "enter" and rows:
            package_id = rows[cursor]["id"].split(":", 1)[1]
            current_rows = {row.package_id: row for row in service.build_overview().package_rows}
            row = current_rows[package_id]
            run_package_actions(service, row)


def run_workspace_menu(service: BootstrapService) -> None:
    cursor = 0
    last_workspace_index = 0
    while True:
        rows = workspace_menu_rows(service.state.tracked_workspaces)
        cursor = min(cursor, len(rows) - 1) if rows else 0
        if rows and rows[cursor]["id"].startswith("workspace:"):
            last_workspace_index = cursor
        lines = [
            "",
            f"  {BOLD}=== Workspaces ==={NC}",
            "  ↑/↓ navigate   Enter select   q back",
            "",
        ]

        for index, row in enumerate(rows):
            prefix = ">" if index == cursor else " "
            label = row["label"]
            if index == cursor:
                lines.append(f"  {BOLD}{prefix} {index + 1:2d}. {REVERSE}{label}{NC}")
            else:
                lines.append(f"    {index + 1:2d}. {label}")

        if not service.state.tracked_workspaces:
            lines.append("")
            lines.append(f"  {DIM}No tracked workspaces yet.{NC}")
        elif rows:
            selected_workspace = resolve_workspace_target(rows, cursor, last_workspace_index)
            if selected_workspace:
                lines.append("")
                lines.append(f"  {CYAN}Selected workspace: {selected_workspace}{NC}")
        draw_screen(lines)

        key = read_key()
        if key == "up":
            cursor = move_cursor(cursor, "up", len(rows))
        elif key == "down":
            cursor = move_cursor(cursor, "down", len(rows))
        elif key in {"q", "escape"}:
            return
        elif key == "enter" and rows:
            selected = rows[cursor]["id"]
            if selected == "action:add":
                path = prompt_line("Workspace path: ")
                if path:
                    try:
                        workspace = Path(path).expanduser().resolve()
                        service.track_and_render_workspace(workspace)
                    except (ValueError, OSError) as error:
                        flash_message(f"Error: {error}")
            elif selected == "action:remove":
                workspace = resolve_workspace_target(rows, cursor, last_workspace_index)
                if workspace:
                    service.untrack_workspace(Path(workspace))
                    last_workspace_index = max(0, min(last_workspace_index, len(service.state.tracked_workspaces) - 1))
                    cursor = min(cursor, len(workspace_menu_rows(service.state.tracked_workspaces)) - 1)
            elif selected == "action:back":
                return


def run_package_actions(service: BootstrapService, package_row: PackageRow) -> None:
    cursor = 0
    while True:
        current_rows = {row.package_id: row for row in service.build_overview().package_rows}
        package_row = current_rows[package_row.package_id]
        actions = package_action_rows(package_row)
        lines = [
            "",
            f"  {BOLD}=== Package Actions ==={NC}",
            f"  {CYAN}Package: {package_row.package_id}{NC}",
            "  ↑/↓ navigate   Enter select   q back",
            "",
        ]
        for index, action in enumerate(actions):
            prefix = ">" if index == cursor else " "
            label = action["label"]
            if index == cursor:
                lines.append(f"  {BOLD}{prefix} {index + 1:2d}. {REVERSE}{label}{NC}")
            else:
                lines.append(f"    {index + 1:2d}. {label}")
        draw_screen(lines)

        key = read_key()
        if key == "up":
            cursor = move_cursor(cursor, "up", len(actions))
        elif key == "down":
            cursor = move_cursor(cursor, "down", len(actions))
        elif key in {"q", "escape"}:
            return
        elif key == "enter":
            selected = actions[cursor]["id"]
            if selected == "action:toggle":
                service.set_package_enabled(package_row.package_id, not package_row.enabled)
                flash_message(f"Toggled {package_row.package_id}.")
            elif selected == "action:import-local":
                try:
                    service.import_from_local(package_row.package_id)
                except (ValueError, OSError) as error:
                    flash_message(f"Error: {error}")
                else:
                    flash_message(f"Imported {package_row.package_id} from local cache.")
            elif selected == "action:remove-managed":
                service.remove_managed_package(package_row.package_id)
                flash_message(f"Removed managed package {package_row.package_id}.")
                return
            elif selected == "action:delete-local":
                service.delete_local_package(package_row.package_id)
                flash_message(f"Deleted local cache copy of {package_row.package_id}.")
                return
            elif selected == "action:back":
                return


def run_status_screen(service: BootstrapService) -> None:
    overview = service.build_overview()
    managed = sum(1 for row in overview.package_rows if row.managed)
    detected = sum(1 for row in overview.package_rows if row.detected_local or row.detected_repo)
    enabled = sum(1 for row in overview.package_rows if row.enabled)
    lines = [
        "",
        f"  {BOLD}=== Status ==={NC}",
        "",
        f"  Managed packages: {managed}",
        f"  Detected packages: {detected}",
        f"  Enabled packages: {enabled}",
        f"  Tracked workspaces: {len(service.state.tracked_workspaces)}",
        "",
        f"  {DIM}Press any key to return.{NC}",
    ]
    draw_screen(lines)
    read_key()


def print_status(service: BootstrapService) -> None:
    overview = service.build_overview()
    managed = sum(1 for row in overview.package_rows if row.managed)
    detected = sum(1 for row in overview.package_rows if row.detected_local or row.detected_repo)
    enabled = sum(1 for row in overview.package_rows if row.enabled)
    print("\n=== Status ===")
    print(f"Managed packages: {managed}")
    print(f"Detected packages: {detected}")
    print(f"Enabled packages: {enabled}")
    print(f"Tracked workspaces: {len(service.state.tracked_workspaces)}")


def run_doctor_screen(service: BootstrapService) -> None:
    issues = service.doctor_issues()
    lines = [
        "",
        f"  {BOLD}=== Doctor ==={NC}",
        "",
    ]
    if not issues:
        lines.extend(
            [
                f"  {CYAN}No issues found.{NC}",
                "",
                f"  {DIM}Press any key to return.{NC}",
            ]
        )
        draw_screen(lines)
        read_key()
        return

    lines.append(f"  Found {len(issues)} issue(s):")
    lines.append("")
    for issue in issues:
        level = issue.level.upper()
        lines.append(f"  [{level}] {issue.scope}")
        lines.append(f"  {issue.message}")
        lines.append("")
    lines.append(f"  {DIM}Press any key to return.{NC}")
    draw_screen(lines)
    read_key()


def print_doctor(service: BootstrapService) -> int:
    issues = service.doctor_issues()
    print("\n=== Doctor ===")
    if not issues:
        print("No issues found.")
        return 0
    print(f"Found {len(issues)} issue(s):")
    for issue in issues:
        print(f"- [{issue.level.upper()}] {issue.scope}: {issue.message}")
    return 1


def apply_all_under(service: BootstrapService, parent: Path) -> None:
    for child in sorted(parent.iterdir()):
        if (child / ".git").exists():
            service.track_and_render_workspace(child)
    service.render_global()


@contextmanager
def terminal_ui():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        hide_cursor()
        yield
    finally:
        show_cursor()
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        clear_screen()


def read_key() -> str:
    first = sys.stdin.read(1)
    if first in {"\r", "\n"}:
        return "enter"
    if first in {"q", "Q"}:
        return "q"
    if first == "\x1b":
        if not os.isatty(sys.stdin.fileno()):
            return "escape"
        second = sys.stdin.read(1)
        if second != "[":
            return "escape"
        third = sys.stdin.read(1)
        if third == "A":
            return "up"
        if third == "B":
            return "down"
        return "escape"
    return first


def prompt_line(prompt: str) -> str:
    show_cursor()
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.write(prompt)
    sys.stdout.flush()
    try:
        return input().strip()
    finally:
        hide_cursor()


def draw_screen(lines: list[str]) -> None:
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.write("\n".join(lines))
    sys.stdout.write("\n")
    sys.stdout.flush()


def clear_screen() -> None:
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def hide_cursor() -> None:
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()


def show_cursor() -> None:
    sys.stdout.write("\033[?25h")
    sys.stdout.flush()


def flash_message(message: str) -> None:
    lines = [
        "",
        f"  {YELLOW}{message}{NC}",
        "",
        f"  {DIM}Press any key to continue.{NC}",
    ]
    draw_screen(lines)
    read_key()


if __name__ == "__main__":
    raise SystemExit(main())
