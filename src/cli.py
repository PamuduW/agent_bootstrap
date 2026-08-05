from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .paths import AgentbotPaths, default_paths
from .service import AgentbotService
from .skills_installer import SkillsInstallError, parse_update_output
from .ui import (
    print_doctor_summary,
    print_graphify_status,
    print_header,
    print_reconciliation_report,
    print_skills_report,
    print_skills_update_report,
    print_status_summary,
    print_workspace_list,
    print_workspace_removed,
    print_workspace_report,
    print_workspace_resync_report,
)
from .workspace_render import WORKSPACE_TARGETS

ARCHIVED_COMMANDS = frozenset(
    {
        "all",
        "interactive",
        "import-local",
        "remove-managed",
        "delete-local",
    }
)


def _workspace_report_has_failures(report) -> bool:
    if report is None:
        return False
    if any(item.status in {"conflict", "failed"} for item in report.results):
        return True
    return any(action.kind == "conflict" for action in report.global_actions)


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
        if command == "graphify":
            graphify_command = getattr(args, "graphify_command", None) or "status"
            status = (
                service.setup_graphify()
                if graphify_command == "setup"
                else service.graphify_status()
            )
            print_graphify_status(status)
            if graphify_command == "status":
                return 1 if status.state == "broken" else 0
            return 0 if status.state in {"ready", "conflict", "stale"} else 1
        if command in {"update", "upgrade"}:
            result = service.run_reconciliation_update(
                dry_run=bool(getattr(args, "dry_run", False)),
                confirm=bool(getattr(args, "confirm", False)),
            )
            title = command.capitalize()
            print_header(f"Agentbot {command}", f"Agentbot › {title}")
            print(f"  {result.status}: {result.message or 'source-owned skills reconciled'}")
            for path in result.changed_paths:
                print(f"  changed: {path}")
            print_reconciliation_report(result)
            if result.workspace_report is not None:
                print_workspace_resync_report(result.workspace_report)
            failed_surfaces = _workspace_report_has_failures(result.workspace_report)
            if result.status not in {
                "applied",
                "applied-with-local-changes",
                "preview",
                "confirmation_required",
            }:
                return 1
            return 1 if failed_surfaces else 0
        if command == "workspace":
            targets = parse_workspace_targets(args.targets)
            if args.yes:
                result = service.apply_workspace(
                    Path(args.path),
                    profile=args.profile,
                    targets=targets,
                    register=True,
                )
            else:
                result = service.preview_workspace(
                    Path(args.path),
                    profile=args.profile,
                    targets=targets,
                )
            print_workspace_report(result)
            return 1 if result.status in {"conflict", "failed"} else 0
        if command == "workspaces":
            if args.remove:
                removed = service.remove_workspace(Path(args.remove))
                print_workspace_removed(removed)
            elif args.paths0:
                for record in service.list_workspaces():
                    sys.stdout.write(f"{record.path}\0")
            else:
                print_workspace_list(service.list_workspaces())
            return 0
        if command == "resync":
            if args.yes and args.dry_run:
                raise ValueError("resync cannot use --yes and --dry-run together")
            if args.all and args.paths:
                raise ValueError("resync cannot combine --all with explicit PATH values")
            if not args.all and not args.paths:
                raise ValueError("resync requires --all or at least one PATH")
            report = service.resync_workspaces(
                apply=bool(args.yes),
                paths=() if args.all else tuple(Path(path) for path in args.paths),
            )
            print_workspace_resync_report(report)
            return 1 if any(item.status in {"conflict", "failed"} for item in report.results) else 0
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
    graphify = subparsers.add_parser("graphify", help="Inspect or set up Graphify integration")
    graphify_sub = graphify.add_subparsers(dest="graphify_command")
    graphify_sub.add_parser("status", help="Show Graphify CLI and skill state")
    graphify_sub.add_parser("setup", help="Install or refresh the generic Agent Skills copy")
    for command in ("update", "upgrade"):
        update = subparsers.add_parser(
            command,
            help="Refresh upstream skills and managed workspace/global outputs",
        )
        update.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview reconciliation and managed-surface changes without writing",
        )
        update.add_argument(
            "--yes",
            dest="confirm",
            action="store_true",
            help="Pre-approve source-owned skill and manifest changes",
        )

    workspace = subparsers.add_parser("workspace", help="Preview or render one workspace")
    workspace.add_argument("--profile", help="Workspace profile name")
    workspace.add_argument(
        "--targets",
        help="Comma-separated outputs: agents,claude,copilot,cursor (codex aliases agents)",
    )
    workspace.add_argument("--yes", action="store_true", help="Apply and register the render")
    workspace.add_argument("path", help="Workspace directory")

    workspaces = subparsers.add_parser(
        "workspaces", help="List or forget locally registered workspaces"
    )
    workspaces_action = workspaces.add_mutually_exclusive_group()
    workspaces_action.add_argument(
        "--paths0",
        action="store_true",
        help="Print canonical recorded paths separated by NUL bytes",
    )
    workspaces_action.add_argument(
        "--remove",
        metavar="PATH",
        help="Stop managing one recorded workspace without changing its files",
    )

    resync = subparsers.add_parser("resync", help="Preview or refresh registered workspaces")
    resync_group = resync.add_mutually_exclusive_group()
    resync_group.add_argument("--yes", action="store_true", help="Apply Agentbot-managed changes")
    resync_group.add_argument("--dry-run", action="store_true", help="Preview without writing")
    resync.add_argument("--all", action="store_true", help="Include all enabled registered workspaces")
    resync.add_argument("paths", nargs="*", help="Explicit registered workspace paths")

    skills = subparsers.add_parser("skills", help="Install and manage curated skills")
    skills_sub = skills.add_subparsers(dest="skills_command", required=True)
    skills_sub.add_parser("install", help="Install skills from skills.sources.yaml")
    skills_sub.add_parser(
        "update",
        help="Refresh globally installed skills from ~/.agents/.skill-lock.json",
    )
    skills_sub.add_parser(
        "upgrade",
        help="Alias for updating globally installed skills",
    )
    skills_sub.add_parser("list", help="List installed skills under ~/.agents/skills")
    skills_sub.add_parser("doctor", help="Validate skills sources and tooling")

    return parser


def _archived_command_error(command: str) -> int:
    print(
        f"Error: '{command}' is archived. See archive/docs/README.md for catalog, "
        "MCP, and interactive control-plane features.",
        file=sys.stderr,
    )
    return 1


def parse_workspace_targets(value: str | None) -> tuple[str, ...] | None:
    if value is None:
        return None
    raw_targets = tuple(part.strip() for part in value.split(",") if part.strip())
    if not raw_targets:
        raise ValueError("--targets must name at least one target")
    targets: list[str] = []
    for raw_target in raw_targets:
        target = "agents" if raw_target == "codex" else raw_target
        if target not in WORKSPACE_TARGETS:
            raise ValueError(f"unsupported workspace target: {raw_target}")
        if target in targets:
            raise ValueError(f"--targets contains duplicates: {target}")
        targets.append(target)
    return ("agents",) + tuple(target for target in targets if target != "agents")


def handle_skills_command(service: AgentbotService, skills_command: str) -> int:
    if skills_command == "install":
        try:
            results = service.install_skills()
            skills_rc = print_skills_report(results, title="Skills install")
            service.refresh_agent_outputs()
        except Exception as error:  # noqa: BLE001
            print_header("Skills install", "Agentbot › Skills install")
            print(f"  Error: {error}")
            return 1
        return skills_rc
    if skills_command in {"update", "upgrade"}:
        title = skills_command.capitalize()
        print_header(f"Skills {skills_command}", f"Agentbot › Skills {title}")
        try:
            result = service.update_skills()
            update_report = parse_update_output(result.stdout, result.stderr)
            linked, skipped, updated = service.refresh_agent_outputs()
        except Exception as error:  # noqa: BLE001
            print(f"  Error: {error}")
            return 1
        return print_skills_update_report(
            linked=linked,
            skipped=skipped,
            updated=updated,
            updated_skills=update_report.updated_skills,
            upstream_deleted_skills=update_report.deleted_skills,
        )
    if skills_command == "list":
        skills = service.list_skills()
        if not skills:
            print_header("Installed Skills", "Agentbot › Installed Skills")
            print("  No installed skills found.")
            return 0
        print_header("Installed Skills", "Agentbot › Installed Skills")
        for skill in skills:
            print(f"  {skill}")
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
    print_header("Skills Doctor", "Agentbot › Skills Doctor")
    if not issues:
        print("  No issues found.")
        return 0
    print(f"  Found {len(issues)} issue(s):")
    errors = 0
    for issue in issues:
        if issue.level.lower() == "error":
            errors += 1
        print(f"  - [{issue.level.upper()}] {issue.scope}: {issue.message}")
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
        claude_statusline_state=str(summary.get("claude_statusline_state", "unknown")),
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
