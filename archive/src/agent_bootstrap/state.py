from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .models import StateSnapshot


def load_state(state_file: Path) -> StateSnapshot:
    if not state_file.exists():
        return StateSnapshot()

    data = json.loads(state_file.read_text(encoding="utf-8"))
    return StateSnapshot(
        enabled_packages=data.get("enabled_packages", {}),
        tracked_workspaces=data.get("tracked_workspaces", []),
        instruction_hashes=data.get("instruction_hashes", {}),
    )


def save_state(state_file: Path, state: StateSnapshot) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "enabled_packages": state.enabled_packages,
        "tracked_workspaces": state.tracked_workspaces,
        "instruction_hashes": state.instruction_hashes,
    }
    state_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def append_audit(audit_log: Path, event: str, details: str) -> None:
    audit_log.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()
    with audit_log.open("a", encoding="utf-8") as handle:
        handle.write(f"{timestamp}\t{event}\t{details}\n")
