import unittest
from pathlib import Path

from scripts.cli import handle_lint_args

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestAdtCli(unittest.TestCase):
    def test_adt_wrapper_binaries_exist(self) -> None:
        bin_dir = REPO_ROOT / "bin"
        self.assertTrue((bin_dir / "adt").is_file())
        self.assertTrue((bin_dir / "adt.cmd").is_file())
        self.assertIn("cli.py", (bin_dir / "adt").read_text(encoding="utf-8"))
        self.assertIn("cli.py", (bin_dir / "adt.cmd").read_text(encoding="utf-8"))

    def test_handle_lint_args_default(self) -> None:
        args = ["--diff", "src/"]
        res = handle_lint_args(args)
        self.assertEqual(res, ["--diff", "src/"])

    def test_handle_lint_args_safe_profile(self) -> None:
        args = ["--diff", "--profile", "safe"]
        res = handle_lint_args(args)
        self.assertIn("--diff", res)
        self.assertIn("--level", res)
        self.assertIn("standard", res)
        self.assertIn("--skip", res)
        skip_idx = res.index("--skip") + 1
        skip_codes = res[skip_idx].split(",")
        self.assertIn("1", skip_codes)
        self.assertIn("11", skip_codes)
        self.assertIn("38", skip_codes)

    def test_handle_lint_args_standard_profile(self) -> None:
        args = ["--profile=standard"]
        res = handle_lint_args(args)
        self.assertIn("--level", res)
        self.assertIn("standard", res)
        self.assertIn("--skip", res)
        skip_idx = res.index("--skip") + 1
        skip_codes = res[skip_idx].split(",")
        self.assertIn("1", skip_codes)
        self.assertIn("5", skip_codes)
        self.assertIn("17", skip_codes)
        self.assertIn("38", skip_codes)

    def test_handle_lint_args_strict_profile(self) -> None:
        args = ["--profile", "strict"]
        res = handle_lint_args(args)
        self.assertIn("--level", res)
        self.assertIn("strict", res)
        self.assertNotIn("--skip", res)

    def test_pre_commit_hooks_file_exists(self) -> None:
        hook_file = REPO_ROOT / ".pre-commit-hooks.yaml"
        self.assertTrue(hook_file.is_file())
        content = hook_file.read_text(encoding="utf-8")
        self.assertIn("id: adt-lint", content)
        self.assertIn("id: adt-secrets", content)

    def test_github_action_definition_exists(self) -> None:
        action_file = REPO_ROOT / "action.yml"
        self.assertTrue(action_file.is_file())
        content = action_file.read_text(encoding="utf-8")
        self.assertIn("name: 'ai-dev-tools Action'", content)
        self.assertIn("using: 'composite'", content)
        self.assertIn("inputs:", content)


if __name__ == "__main__":
    unittest.main()
