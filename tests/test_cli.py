import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from scripts.cli import COMMAND_MAP, print_usage, run_target_script


class TestCLI(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_command_map_integrity(self) -> None:
        self.assertIn("lint", COMMAND_MAP)
        self.assertIn("fix", COMMAND_MAP)
        self.assertIn("ui", COMMAND_MAP)
        self.assertIn("skills", COMMAND_MAP)
        self.assertIn("doctor", COMMAND_MAP)
        self.assertIn("config", COMMAND_MAP)
        self.assertIn("repo-map", COMMAND_MAP)
        self.assertIn("tree", COMMAND_MAP)
        self.assertIn("slice", COMMAND_MAP)
        self.assertIn("tokens", COMMAND_MAP)
        self.assertIn("search", COMMAND_MAP)

    @patch("scripts.cli.subprocess.run")
    def test_run_target_script_invocation(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0)
        code = run_target_script("claudemd_linter.py", ["--level", "strict"])
        self.assertEqual(code, 0)
        self.assertTrue(mock_run.called)

    def test_run_target_script_missing(self) -> None:
        code = run_target_script("non_existent_script.py", [])
        self.assertEqual(code, 1)

    @patch("builtins.print")
    def test_print_usage(self, mock_print: MagicMock) -> None:
        print_usage()
        self.assertTrue(mock_print.called)


if __name__ == "__main__":
    unittest.main()
