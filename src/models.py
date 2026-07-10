from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DoctorIssue:
    level: str
    scope: str
    message: str
