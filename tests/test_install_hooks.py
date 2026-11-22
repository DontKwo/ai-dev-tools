import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import StringIO
import sys

# Append scripts dir so we can import modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import install_hooks
import install_antigravity_hooks

class TestInstallHooks(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name).resolve()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_create_hook_content(self) -> None:
        content = install_hooks.create_hook_content()
        self.assertTrue(content.startswith("#!/usr/bin/env sh"))
        self.assertIn("claudemd_linter.py", content)
        self.assertIn("--staged", content)

    @patch("sys.stdout", new_callable=StringIO)
    def test_install_hook_no_git(self, mock_stdout: StringIO) -> None:
        install_hooks.install_hook(self.temp_path, action="overwrite")
        self.assertIn("not a git repository", mock_stdout.getvalue())

    def test_install_hook_success(self) -> None:
        git_dir = self.temp_path / ".git"
        git_dir.mkdir()
        install_hooks.install_hook(self.temp_path, action="overwrite")

        hook_file = git_dir / "hooks" / "pre-commit"
        self.assertTrue(hook_file.exists())
        content = hook_file.read_text(encoding="utf-8")
        self.assertTrue(content.startswith("#!/usr/bin/env sh"))

        # Check permissions on POSIX
        if os.name != "nt":
            mode = hook_file.stat().st_mode
            self.assertTrue(mode & stat.S_IXUSR)

    @patch("sys.stdout", new_callable=StringIO)
    def test_uninstall_hook(self, mock_stdout: StringIO) -> None:
        git_dir = self.temp_path / ".git"
        git_dir.mkdir()
        install_hooks.install_hook(self.temp_path, action="append")
        hook_file = git_dir / "hooks" / "pre-commit"
        self.assertTrue(hook_file.exists())

        install_hooks.uninstall_hook(self.temp_path)
        self.assertFalse(hook_file.exists())
        self.assertIn("Removed pre-commit hook block", mock_stdout.getvalue())

    def test_append_preserves_existing_hook_and_is_idempotent(self) -> None:
        hooks_dir = self.temp_path / ".git" / "hooks"
        hooks_dir.mkdir(parents=True)
        hook_file = hooks_dir / "pre-commit"
        hook_file.write_text("#!/bin/sh\necho user-hook\nexit 0\n", encoding="utf-8")

        install_hooks.install_hook(self.temp_path, action="append")
        install_hooks.install_hook(self.temp_path, action="append")
        content = hook_file.read_text(encoding="utf-8")
        self.assertIn("echo user-hook", content)
        self.assertEqual(content.count(install_hooks.BEGIN_MARKER), 1)
        self.assertTrue(content.startswith("#!/bin/sh"))
        self.assertLess(content.index(install_hooks.BEGIN_MARKER), content.index("exit 0"))

    def test_uninstall_keeps_foreign_hook_content(self) -> None:
        hooks_dir = self.temp_path / ".git" / "hooks"
        hooks_dir.mkdir(parents=True)
        hook_file = hooks_dir / "pre-commit"
        hook_file.write_text("#!/bin/sh\necho user-hook\n", encoding="utf-8")
        install_hooks.install_hook(self.temp_path, action="append")

        install_hooks.uninstall_hook(self.temp_path)
        content = hook_file.read_text(encoding="utf-8")
        self.assertIn("echo user-hook", content)
        self.assertNotIn(install_hooks.BEGIN_MARKER, content)

    def test_uninstall_leaves_unmarked_hook_untouched(self) -> None:
        hooks_dir = self.temp_path / ".git" / "hooks"
        hooks_dir.mkdir(parents=True)
        hook_file = hooks_dir / "pre-commit"
        hook_file.write_text("fake hook", encoding="utf-8")
        install_hooks.uninstall_hook(self.temp_path)
        self.assertEqual(hook_file.read_text(encoding="utf-8"), "fake hook")

class TestInstallAntigravityHooks(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name).resolve()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    @patch("install_antigravity_hooks.get_user_home")
    def test_get_hook_paths(self, mock_home: MagicMock) -> None:
        mock_home.return_value = self.temp_path / "home"
        paths = install_antigravity_hooks.get_hook_paths(self.temp_path)

        self.assertIn("workspace", paths)
        self.assertIn("global", paths)
        self.assertEqual(paths["workspace"][0], self.temp_path / ".agent" / "hooks.json")
        self.assertEqual(paths["global"][0], self.temp_path / "home" / ".gemini" / "config" / "hooks.json")

    def test_build_hook_config(self) -> None:
        config = install_antigravity_hooks.build_hook_config("fake cmd", "Stop")
        self.assertIn("developer-linter-completion-guard", config)
        guard = config["developer-linter-completion-guard"]
        self.assertIn("Stop", guard)
        self.assertEqual(guard["Stop"][0]["command"], "fake cmd")

    def test_install_hook(self) -> None:
        dest = self.temp_path / "hooks.json"
        install_antigravity_hooks.install_hook(dest, "fake cmd")

        self.assertTrue(dest.exists())
        data = json.loads(dest.read_text(encoding="utf-8"))
        self.assertIn("developer-linter-completion-guard", data)

    def test_remove_hook(self) -> None:
        dest = self.temp_path / "hooks.json"
        install_antigravity_hooks.install_hook(dest, "fake cmd")

        res = install_antigravity_hooks.remove_hook(dest)
        self.assertTrue(res)
        data = json.loads(dest.read_text(encoding="utf-8"))
        self.assertNotIn("developer-linter-completion-guard", data)

    def test_main_installs_and_removes_git_hook(self) -> None:
        (self.temp_path / ".git").mkdir()
        with patch.object(sys, "argv", ["install_antigravity_hooks.py", "--scope", "workspace", "--workspace", str(self.temp_path), "--git"]):
            install_antigravity_hooks.main()
        self.assertTrue((self.temp_path / ".agent" / "hooks.json").is_file())
        self.assertTrue((self.temp_path / ".git" / "hooks" / "pre-commit").is_file())

        with patch.object(sys, "argv", ["install_antigravity_hooks.py", "--scope", "workspace", "--workspace", str(self.temp_path), "--git", "--remove"]):
            install_antigravity_hooks.main()
        self.assertFalse((self.temp_path / ".git" / "hooks" / "pre-commit").exists())

    def test_pre_push_hook_install_and_uninstall(self) -> None:
        (self.temp_path / ".git").mkdir()
        install_hooks.install_hook(self.temp_path, action="overwrite", hook_type="pre-push")
        pre_push = self.temp_path / ".git" / "hooks" / "pre-push"
        self.assertTrue(pre_push.is_file())
        text = pre_push.read_text(encoding="utf-8")
        self.assertIn("claudemd_linter.py", text)
        self.assertIn("link_checker.py", text)
        install_hooks.uninstall_hook(self.temp_path, hook_type="pre-push")
        self.assertFalse(pre_push.exists())

if __name__ == "__main__":
    unittest.main()
