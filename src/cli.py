from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

from .commands import COMMANDS, CommandSpec, command_by_name
from .diagnostics import Diagnostics
from .graphify import GraphifyIntegration
from .lifecycle import Lifecycle
from .paths import AgentbotPaths, default_paths
from .skills_installer import SkillsInstallError, parse_update_output
from .ui import (
    print_command_help,
    print_doctor_summary,
    print_graphify_status,
    print_header,
    print_reconciliation_report,
    print_skill_prune_report,
    print_skills_report,
    print_skills_update_report,
    print_status_summary,
    print_update_outcome,
    print_update_plan,
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

    command = args.command or "bootstrap"
    if command == "help":
        return print_help_command(
            getattr(args, "help_topic", None),
            output_format=getattr(args, "help_format", "plain"),
        )

    paths = default_paths(Path(args.root))
    diagnostics = Diagnostics(paths)
    lifecycle = Lifecycle(
        paths,
        diagnostics=diagnostics,
        graphify=GraphifyIntegration(paths),
    )
    context = CommandContext(args=args, paths=paths, diagnostics=diagnostics, lifecycle=lifecycle)

    if command in ARCHIVED_COMMANDS:
        return _archived_command_error(command)
    handler = COMMAND_HANDLERS.get(command)
    if handler is None:
        raise SystemExit(f"unknown command: {command}")

    try:
        return handler(context)
    except (SkillsInstallError, ValueError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


@dataclass(frozen=True)
class CommandContext:
    """Everything a command handler needs, assembled once by main()."""

    args: argparse.Namespace
    paths: AgentbotPaths
    diagnostics: Diagnostics
    lifecycle: Lifecycle


def _handle_status(context: CommandContext) -> int:
    if bool(getattr(context.args, "status_json", False)):
        print_status_json(context.diagnostics)
        return 0
    return print_status(
        context.diagnostics,
        include_issues=bool(getattr(context.args, "status_doctor", False)),
    )


def _handle_global(context: CommandContext) -> int:
    context.lifecycle.render_global()
    return 0


def _handle_doctor(context: CommandContext) -> int:
    return print_doctor(context.diagnostics)


def _handle_graphify(context: CommandContext) -> int:
    graphify_command = getattr(context.args, "graphify_command", None) or "status"
    status = (
        context.lifecycle.setup_graphify()
        if graphify_command == "setup"
        else context.lifecycle.graphify_status()
    )
    print_graphify_status(status)
    if graphify_command == "status":
        return 1 if status.state == "broken" else 0
    return 0 if status.state in {"ready", "conflict", "stale"} else 1


def _handle_update(context: CommandContext) -> int:
    args = context.args
    command = args.command
    plan = context.lifecycle.plan_update()
    print_update_plan(plan, command=command)
    if bool(getattr(args, "dry_run", False)):
        return 0
    if bool(getattr(args, "interactive", False)):
        if not confirm_update_plan():
            print("  Update cancelled.")
            return 0
    elif not bool(getattr(args, "confirm", False)) and (
        plan.reconcile.wildcard_additions
        or plan.reconcile.wildcard_removals
        or plan.reconcile.manifest_changes
    ):
        print("  confirmation_required: rerun with --yes to apply this plan")
        return 0

    outcome = context.lifecycle.apply_update(plan)
    print_update_outcome(outcome)
    if outcome.reconcile is not None:
        print_reconciliation_report(outcome.reconcile)
    workspace_report = outcome.workspace_report
    if workspace_report is not None:
        print_workspace_resync_report(workspace_report)
    if outcome.status not in {"applied", "applied-with-local-changes"}:
        return 1
    return 1 if _workspace_report_has_failures(workspace_report) else 0


def _handle_workspace(context: CommandContext) -> int:
    args = context.args
    targets = parse_workspace_targets(args.targets)
    if args.yes:
        result = context.lifecycle.apply_workspace(
            Path(args.path), profile=args.profile, targets=targets, register=True
        )
    else:
        result = context.lifecycle.preview_workspace(
            Path(args.path), profile=args.profile, targets=targets
        )
    print_workspace_report(result)
    return 1 if result.status in {"conflict", "failed"} else 0


def _handle_workspaces(context: CommandContext) -> int:
    args = context.args
    if args.remove:
        print_workspace_removed(context.lifecycle.remove_workspace(Path(args.remove)))
    elif args.paths0:
        for record in context.lifecycle.list_workspaces():
            sys.stdout.write(f"{record.path}\0")
    else:
        print_workspace_list(context.lifecycle.list_workspaces())
    return 0


def _handle_resync(context: CommandContext) -> int:
    args = context.args
    if args.yes and args.dry_run:
        raise ValueError("resync cannot use --yes and --dry-run together")
    if args.all and args.paths:
        raise ValueError("resync cannot combine --all with explicit PATH values")
    if not args.all and not args.paths:
        raise ValueError("resync requires --all or at least one PATH")
    report = context.lifecycle.resync_workspaces(
        apply=bool(args.yes),
        paths=() if args.all else tuple(Path(path) for path in args.paths),
    )
    print_workspace_resync_report(report)
    return 1 if any(item.status in {"conflict", "failed"} for item in report.results) else 0


def _handle_bootstrap(context: CommandContext) -> int:
    return run_bootstrap_command(context.lifecycle, context.paths)


def _handle_skills(context: CommandContext) -> int:
    if context.args.skills_command == "prune":
        return handle_skills_prune(
            context.lifecycle,
            apply=bool(getattr(context.args, "confirm", False)),
            include_manual=bool(getattr(context.args, "include_manual", False)),
        )
    return handle_skills_command(context.lifecycle, context.args.skills_command)


COMMAND_HANDLERS: dict[str, Callable[[CommandContext], int]] = {
    "status": _handle_status,
    "global": _handle_global,
    "doctor": _handle_doctor,
    "graphify": _handle_graphify,
    "update": _handle_update,
    "upgrade": _handle_update,
    "workspace": _handle_workspace,
    "workspaces": _handle_workspaces,
    "resync": _handle_resync,
    "bootstrap": _handle_bootstrap,
    "skills": _handle_skills,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agentbot")
    parser.add_argument(
        "--root",
        dest="root",
        default=os.environ.get("AGENTBOT_HOME", str(Path(__file__).resolve().parents[1])),
    )
    subparsers = parser.add_subparsers(dest="command")

    help_parser = subparsers.add_parser("help", help="Show the command reference")
    help_parser.add_argument("help_topic", nargs="?", metavar="COMMAND")
    help_parser.add_argument(
        "--format",
        choices=("plain", "menu", "tui"),
        default="plain",
        dest="help_format",
        help=argparse.SUPPRESS,
    )

    subparsers.add_parser("bootstrap", help="Run fresh-machine bootstrap flow")
    status_parser = subparsers.add_parser("status", help="Show skills and global render status")
    status_output = status_parser.add_mutually_exclusive_group()
    status_output.add_argument("--json", action="store_true", dest="status_json")
    status_output.add_argument(
        "--doctor",
        action="store_true",
        dest="status_doctor",
        help="Show status and Doctor issues from one diagnostics snapshot",
    )
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
        update.add_argument(
            "--interactive",
            action="store_true",
            help="Preview, confirm, and apply one update plan in this process",
        )

    workspace = subparsers.add_parser("workspace", help="Preview or render one workspace")
    workspace.add_argument("--profile", help="Workspace profile name")
    workspace.add_argument(
        "--targets",
        help="Comma-separated outputs: agents,claude,cursor (codex aliases agents)",
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
    prune = skills_sub.add_parser(
        "prune",
        help="Remove installed skills that no active manifest source wants",
    )
    prune.add_argument(
        "--yes",
        dest="confirm",
        action="store_true",
        help="Apply the removals; without it this only reports",
    )
    prune.add_argument(
        "--include-manual",
        action="store_true",
        help="Also remove user-placed skills that have no lock entry",
    )

    return parser


def _archived_command_error(command: str) -> int:
    print(
        f"Error: '{command}' is archived. See archive/docs/README.md for catalog, "
        "MCP, and interactive control-plane features.",
        file=sys.stderr,
    )
    return 1


def confirm_update_plan() -> bool:
    input_path = os.environ.get("AGENTBOT_UPDATE_TTY_INPUT", "/dev/tty")
    output_path = os.environ.get("AGENTBOT_UPDATE_TTY_OUTPUT", "/dev/tty")
    with open(output_path, "a", encoding="utf-8") as output_stream:
        output_stream.write("\nApply this Agentbot update plan? [y/N] ")
        output_stream.flush()
    with open(input_path, encoding="utf-8") as input_stream:
        answer = input_stream.readline().strip()
    return answer.lower() in {"y", "yes"}


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
    return ("agents", *(target for target in targets if target != "agents"))


def handle_skills_prune(
    lifecycle: Lifecycle, *, apply: bool, include_manual: bool
) -> int:
    from .skill_prune import apply_prune, plan_prune
    from .skills_sources import load_skills_sources

    paths = lifecycle.paths
    config = load_skills_sources(paths.skills_sources_file)
    report = plan_prune(paths, config)
    if apply:
        report = apply_prune(paths, report, include_manual=include_manual)
    return print_skill_prune_report(report, include_manual=include_manual)


def handle_skills_command(lifecycle: Lifecycle, skills_command: str) -> int:
    if skills_command == "install":
        try:
            results = lifecycle.install_skills()
            skills_rc = print_skills_report(results, title="Skills install")
            lifecycle.refresh_outputs()
        except Exception as error:
            print_header("Skills install", "Agentbot › Skills install")
            print(f"  Error: {error}")
            return 1
        return skills_rc
    if skills_command in {"update", "upgrade"}:
        title = skills_command.capitalize()
        print_header(f"Skills {skills_command}", f"Agentbot › Skills {title}")
        try:
            result = lifecycle.update_skills()
            update_report = parse_update_output(result.stdout, result.stderr)
            outputs = lifecycle.refresh_outputs()
        except Exception as error:
            print(f"  Error: {error}")
            return 1
        return print_skills_update_report(
            linked=outputs.claude_linked,
            skipped=outputs.claude_skipped,
            updated=outputs.claude_updated,
            updated_skills=update_report.updated_skills,
            upstream_deleted_skills=update_report.deleted_skills,
        )
    if skills_command == "list":
        skills = lifecycle.list_skills()
        if not skills:
            print_header("Installed Skills", "Agentbot › Installed Skills")
            print("  No installed skills found.")
            return 0
        print_header("Installed Skills", "Agentbot › Installed Skills")
        for skill in skills:
            print(f"  {skill}")
        return 0
    if skills_command == "doctor":
        return print_skills_doctor(lifecycle.diagnostics)
    raise SystemExit(f"unknown skills command: {skills_command}")


def run_bootstrap_command(lifecycle: Lifecycle, paths: AgentbotPaths) -> int:
    print_header("Install Agentbot", "Agentbot › Install Agentbot")
    outcome = lifecycle.install()
    skills_rc = print_skills_report(list(outcome.skills), title="Skills install")
    if outcome.graphify.cli_path is not None or outcome.graphify.state == "broken":
        print_graphify_status(outcome.graphify)
    doctor_rc = print_doctor_summary(list(outcome.diagnostics.issues))
    print(f"AGENTBOT_HOME={paths.root.resolve()}")
    if skills_rc != 0:
        return skills_rc
    if outcome.graphify.state == "broken":
        return 1
    return doctor_rc


def print_skills_doctor(diagnostics: Diagnostics) -> int:
    issues = diagnostics.skills_doctor_issues()
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


def print_status(diagnostics: Diagnostics, *, include_issues: bool = False) -> int:
    snapshot = diagnostics.collect()
    print_status_summary(
        installed_skills=len(snapshot.installed_skills),
        global_agents_exists=snapshot.global_agents_exists,
        skills_sources_exists=snapshot.skills_sources_exists,
        enabled_sources=snapshot.enabled_sources,
        global_lock_exists=snapshot.global_lock_exists,
        global_lock_skills=snapshot.global_lock_skills,
        claude_bridge_links=snapshot.claude_bridge_links,
        claude_statusline_state=snapshot.claude_statusline_state,
        manual_skill_count=snapshot.manual_skill_count,
        doctor_issue_count=len(snapshot.issues),
    )
    if include_issues:
        return print_doctor_summary(list(snapshot.issues), include_header=False)
    return 0


def print_status_json(diagnostics: Diagnostics) -> None:
    snapshot = diagnostics.collect()
    payload = asdict(snapshot)
    payload["installed_skills"] = len(snapshot.installed_skills)
    payload["doctor_issue_count"] = len(snapshot.issues)
    payload.pop("issues")
    print(json.dumps(payload, indent=2, sort_keys=True))


def print_doctor(diagnostics: Diagnostics) -> int:
    return print_doctor_summary(list(diagnostics.collect().issues))


def print_help_command(topic: str | None, *, output_format: str = "plain") -> int:
    if output_format == "menu":
        for command_spec in COMMANDS:
            print(
                f"{command_spec.name}\t{command_spec.behavior}"
                f"\t{command_spec.surface}\t{command_spec.summary}"
            )
        return 0
    spec: CommandSpec | None
    try:
        spec = command_by_name(topic) if topic else None
    except KeyError:
        print(f"Error: unknown help topic: {topic}", file=sys.stderr)
        return 2
    print_command_help(spec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
