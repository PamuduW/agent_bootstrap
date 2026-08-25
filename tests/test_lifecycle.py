import tempfile
import unittest
from pathlib import Path


class LifecycleTests(unittest.TestCase):
    def test_install_orders_each_stage_once_and_returns_typed_outcome(self) -> None:
        from src.boost import BoostStatus
        from src.graphify import GraphifyStatus
        from src.lifecycle import Lifecycle
        from src.models import DiagnosticsSnapshot, OutputRefreshOutcome
        from src.paths import AgentbotPaths

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = AgentbotPaths(root, root / "codex", root / "claude", root / "cursor")
            events: list[str] = []
            graphify_status = GraphifyStatus(
                "not-installed",
                None,
                None,
                root / "agents/skills/graphify/SKILL.md",
                None,
                "missing",
                "missing",
                "Graphify CLI and Agent Skills integration are not installed.",
            )
            diagnostics_snapshot = DiagnosticsSnapshot(
                installed_skills=(),
                enabled_sources=0,
                global_agents_exists=False,
                skills_sources_exists=False,
                global_lock_exists=False,
                global_lock_skills=0,
                managed_skill_count=0,
                manual_skill_count=0,
                claude_bridge_links=0,
                claude_statusline_state="missing",
                issues=(),
            )
            boost_status = BoostStatus(
                "not-installed",
                None,
                None,
                root / ".boost/config.toml",
                False,
                False,
                "missing",
                "missing",
                "absent",
                "Boost CLI is not installed.",
            )

            class FakeGraphify:
                def refresh_if_enabled(self):
                    events.append("graphify")
                    return graphify_status

            class FakeDiagnostics:
                def collect(self):
                    events.append("diagnostics")
                    return diagnostics_snapshot

            class FakeBoost:
                def setup_if_cli_available(self):
                    events.append("boost")
                    return boost_status

            def install_skills(_paths):
                events.append("skills")
                return []

            def refresh_outputs():
                events.append("outputs")
                return OutputRefreshOutcome(0, 0, 0)

            lifecycle = Lifecycle(
                paths,
                diagnostics=FakeDiagnostics(),
                graphify=FakeGraphify(),
                boost=FakeBoost(),
                install_skills=install_skills,
                refresh_outputs=refresh_outputs,
            )
            outcome = lifecycle.install()

            self.assertEqual(["skills", "graphify", "boost", "outputs", "diagnostics"], events)
            self.assertEqual((), outcome.skills)
            self.assertIs(graphify_status, outcome.graphify)
            self.assertIs(boost_status, outcome.boost)
            self.assertIs(diagnostics_snapshot, outcome.diagnostics)


if __name__ == "__main__":
    unittest.main()
