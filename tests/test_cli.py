import io
import sys
import unittest
from unittest.mock import MagicMock, patch


class CliTests(unittest.TestCase):
    def _run_main(self, argv: list[str]) -> tuple[int, str, str]:
        from src.cli import main

        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch.object(sys, "argv", argv), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
            return main(), stdout.getvalue(), stderr.getvalue()

    @patch("src.cli.default_paths")
    @patch("src.cli.AgentbotService")
    def test_skills_install_refreshes_agent_outputs(self, service_type, _default_paths) -> None:
        service = MagicMock()
        service.install_skills.return_value = []
        service.refresh_agent_outputs.return_value = (0, 0, 0)
        service_type.return_value = service

        rc, _stdout, _stderr = self._run_main(["agentbot", "skills", "install"])

        self.assertEqual(0, rc)
        service.refresh_agent_outputs.assert_called_once_with()

    @patch("src.cli.default_paths")
    @patch("src.cli.AgentbotService")
    def test_bootstrap_skill_failure_is_a_clean_cli_error(self, service_type, _default_paths) -> None:
        from src.skills_installer import SkillsInstallError

        service = MagicMock()
        service.run_bootstrap.side_effect = SkillsInstallError("failed to install source 'test': offline")
        service_type.return_value = service

        rc, _stdout, stderr = self._run_main(["agentbot", "bootstrap"])

        self.assertEqual(1, rc)
        self.assertIn("Error: failed to install source 'test': offline", stderr)

    def test_parser_and_paths_use_agentbot_product_contract(self) -> None:
        import os
        import tempfile
        from pathlib import Path

        from src.cli import build_parser
        from src.paths import AgentbotPaths, default_paths

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "agent_bootstrap"
            xdg = Path(temp_dir) / "config"
            with patch.dict(
                os.environ,
                {"AGENTBOT_HOME": str(root), "XDG_CONFIG_HOME": str(xdg)},
                clear=False,
            ):
                args = build_parser().parse_args(["status"])
                paths = default_paths()

        self.assertEqual("agentbot", build_parser().prog)
        self.assertEqual(root, Path(args.root))
        self.assertIsInstance(paths, AgentbotPaths)
        self.assertEqual(root, paths.root)
        self.assertEqual(xdg / "agentbot", paths.config_home)


if __name__ == "__main__":
    unittest.main()
