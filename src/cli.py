from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .paths import AgentbotPaths, default_paths
from .service import AgentbotService
from .skills_installer import SkillsInstallError
from .ui import (
    print_doctor_summary,
    print_header,
    print_reconciliation_report,
    print_skills_report,
    print_skills_update_report,
    print_status_summary,
)

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
    service = AgentbotService(paths)

    try:
        command = args.command or "bootstrap"
        if command in ARCHIVED_COMMANDS:
            return _archived_command_error(command)
        if command == "status":
            if getattr(args, "status_json", False):
                print_status_json(service)
            else:
                print_status(service)
            return 0
        if command == "global":
            service.render_global()
            return 0
        if command == "doctor":
            return print_doctor(service)
        if command == "update":
            result = service.run_reconciliation_update(
                dry_run=bool(getattr(args, "dry_run", False)),
                confirm=bool(getattr(args, "confirm", False)),
            )
            print_header("Agentbot update", "Agentbot")
            print(f"  {result.status}: {result.message or 'source-owned skills reconciled'}")
            for path in result.changed_paths:
                print(f"  changed: {path}")
            print_reconciliation_report(result)
            return 0 if result.status in {"applied", "applied-with-local-changes", "preview", "confirmation_required"} else 1
        if command == "bootstrap":
            return run_bootstrap_command(service, paths)
        if command == "skills":
            return handle_skills_command(service, args.skills_command)
        raise SystemExit(f"unknown command: {command}")
    except (SkillsInstallError, ValueError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agentbot")
    parser.add_argument(
        "--root",
        dest="root",
        default=os.environ.get("AGENTBOT_HOME", str(Path(__file__).resolve().parents[1])),
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("bootstrap", help="Run fresh-machine bootstrap flow")
    status_parser = subparsers.add_parser("status", help="Show skills and global render status")
    status_parser.add_argument("--json", action="store_true", dest="status_json")
    subparsers.add_parser("global", help="Render global outputs")
    subparsers.add_parser("doctor", help="Validate skills and global baseline")
    update = subparsers.add_parser("update", help="Reconcile source-owned skills after the repository gate")
    update.add_argument("--dry-run", action="store_true", help="Preview reconciliation without writing")
    update.add_argument("--yes", dest="confirm", action="store_true", help="Confirm source-owned changes")

    skills = subparsers.add_parser("skills", help="Install and manage curated skills")
    skills_sub = skills.add_subparsers(dest="skills_command", required=True)
    skills_sub.add_parser("install", help="Install skills from skills.sources.yaml")
    skills_sub.add_parser(
        "update",
        help="Refresh globally installed skills from ~/.agents/.skill-lock.json",
    )
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


def handle_skills_command(service: AgentbotService, skills_command: str) -> int:
    if skills_command == "install":
        try:
            results = service.install_skills()
            skills_rc = print_skills_report(results, title="Skills install")
            service.refresh_agent_outputs()
        except Exception as error:  # noqa: BLE001
            print_header("Skills install", "Agentbot › skills")
            print(f"  Error: {error}")
            return 1
        return skills_rc
    if skills_command == "update":
        print_header("Skills update", "Agentbot › skills")
        try:
            service.update_skills()
            linked, skipped, updated = service.refresh_agent_outputs()
        except Exception as error:  # noqa: BLE001
            print(f"  Error: {error}")
            return 1
        return print_skills_update_report(linked=linked, skipped=skipped, updated=updated)
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


def run_bootstrap_command(service: AgentbotService, paths: AgentbotPaths) -> int:
    rc = service.run_bootstrap()
    print(f"AGENTBOT_HOME={paths.root.resolve()}")
    return rc


def print_skills_doctor(service: AgentbotService) -> int:
    issues = service.skills_doctor_issues()
    print("\n=== Skills Doctor ===")
    if not issues:
        print("No issues found.")
        return 0
    print(f"Found {len(issues)} issue(s):")
    errors = 0
    for issue in issues:
        if issue.level.lower() == "error":
            errors += 1
        print(f"- [{issue.level.upper()}] {issue.scope}: {issue.message}")
    return 1 if errors else 0


def print_status(service: AgentbotService) -> None:
    summary = service.status_summary()
    print_status_summary(
        installed_skills=int(summary["installed_skills"]),
        global_agents_exists=bool(summary["global_agents_exists"]),
        skills_sources_exists=bool(summary["skills_sources_exists"]),
        enabled_sources=int(summary["enabled_sources"]),
        global_lock_exists=bool(summary["global_lock_exists"]),
        global_lock_skills=int(summary["global_lock_skills"]),
        claude_bridge_links=int(summary["claude_bridge_links"]),
        manual_skill_count=int(summary["manual_skill_count"]),
        doctor_issue_count=int(summary["doctor_issue_count"]),
    )


def print_status_json(service: AgentbotService) -> None:
    print(json.dumps(service.status_summary(), indent=2, sort_keys=True))


def print_doctor(service: AgentbotService) -> int:
    issues = service.doctor_issues() + service.skills_doctor_issues()
    return print_doctor_summary(issues)


if __name__ == "__main__":
    raise SystemExit(main())
