from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .paths import BootstrapPaths, default_paths
from .service import BootstrapService
from .ui import print_doctor_summary, print_header, print_skills_report, print_status_summary

ARCHIVED_COMMANDS = frozenset(
    {
        "workspace",
        "all",
        "interactive",
        "import-local",
        "remove-managed",
        "delete-local",
    }
)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    paths = default_paths(Path(args.root))
    service = BootstrapService(paths)

    try:
        command = args.command or "bootstrap"
        if command in ARCHIVED_COMMANDS:
            return _archived_command_error(command)
        if command == "status":
            print_status(service)
            return 0
        if command == "global":
            service.render_global()
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

    subparsers.add_parser("bootstrap", help="Run fresh-machine bootstrap flow")
    subparsers.add_parser("status", help="Show skills and global render status")
    subparsers.add_parser("global", help="Render global outputs")
    subparsers.add_parser("doctor", help="Validate skills and global baseline")

    skills = subparsers.add_parser("skills", help="Install and manage curated skills")
    skills_sub = skills.add_subparsers(dest="skills_command", required=True)
    skills_sub.add_parser("install", help="Install skills from skills.sources.yaml")
    skills_sub.add_parser("update", help="Update skills from skills.sources.yaml")
    skills_sub.add_parser("list", help="List installed skills under ~/.agents/skills")
    skills_sub.add_parser("doctor", help="Validate skills sources and tooling")

    return parser


def _archived_command_error(command: str) -> int:
    print(
        f"Error: '{command}' is archived. See archive/README.md for workspace render, "
        "catalog, MCP, and interactive control-plane features.",
        file=sys.stderr,
    )
    return 1


def handle_skills_command(service: BootstrapService, skills_command: str) -> int:
    if skills_command == "install":
        try:
            results = service.install_skills()
            skills_rc = print_skills_report(results, title="Skills install")
            service.apply_claude_bridge()
        except Exception as error:  # noqa: BLE001
            print_header("Skills install", "agent_bootstrap › skills")
            print(f"  Error: {error}")
            return 1
        return skills_rc
    if skills_command == "update":
        try:
            service.update_skills()
        except Exception as error:  # noqa: BLE001
            print_header("Skills update", "agent_bootstrap › skills")
            print(f"  Error: {error}")
            return 1
        print_header("Skills update", "agent_bootstrap › skills")
        print("  Skills refreshed from upstream lockfile.")
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
    rc = service.run_bootstrap()
    print(f"AGENT_BOOTSTRAP_HOME={paths.root.resolve()}")
    return rc


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


def print_status(service: BootstrapService) -> None:
    summary = service.status_summary()
    print_status_summary(
        installed_skills=int(summary["installed_skills"]),
        global_agents_exists=bool(summary["global_agents_exists"]),
        skills_sources_exists=bool(summary["skills_sources_exists"]),
    )


def print_doctor(service: BootstrapService) -> int:
    issues = service.doctor_issues() + service.skills_doctor_issues()
    return print_doctor_summary(issues)


if __name__ == "__main__":
    raise SystemExit(main())
