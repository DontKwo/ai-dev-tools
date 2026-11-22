"""Unit tests verifying filesystem safety, backup integrity, uninstall, and detection."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from apply_config import (
    STATE_MANIFEST_FILE,
    atomic_write_text,
    build_plan_from_config,
    create_safe_backup,
    detect_workspace_integrations,
    execute_plan,
    format_plan_preview,
    uninstall_configuration,
    validate_workspace_path,
)
from lint_fixer import fix_file, rollback_backups
from smart_test_runner import find_matching_tests, get_all_tests
from yaml_utils import validate_config_schema


class TestSafetyAndUninstall(unittest.TestCase):
    """Tests path validation, atomic writing, uninstall, and auto-detection."""

    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        self.workspace_directory = Path(self.temp_directory.name)
        self.home_directory = self.workspace_directory / "home"
        self.home_directory.mkdir()

    def tearDown(self) -> None:
        self.temp_directory.cleanup()

    def test_validate_workspace_path_blocks_escape(self) -> None:
        valid_path = self.workspace_directory / "CLAUDE.md"
        resolved = validate_workspace_path(valid_path, self.workspace_directory)
        self.assertEqual(resolved, valid_path.resolve())

        escaped_path = self.workspace_directory / ".." / "outside.txt"
        with self.assertRaises(ValueError):
            validate_workspace_path(escaped_path, self.workspace_directory)

    def test_atomic_write_text(self) -> None:
        target_file = self.workspace_directory / "test_file.txt"
        content = "Important test content\n"
        atomic_write_text(target_file, content)
        self.assertTrue(target_file.is_file())
        self.assertEqual(target_file.read_text(encoding="utf-8"), content)

    def test_collision_safe_backup_naming_and_integrity(self) -> None:
        target_file = self.workspace_directory / "config.txt"
        target_file.write_text("Version 1 content", encoding="utf-8")

        first_backup = create_safe_backup(target_file)
        self.assertEqual(first_backup.name, "config.txt.bak")
        self.assertEqual(first_backup.read_text(encoding="utf-8"), "Version 1 content")

        target_file.write_text("Version 2 content", encoding="utf-8")
        second_backup = create_safe_backup(target_file)
        self.assertEqual(second_backup.name, "config.txt.bak.1")
        self.assertEqual(second_backup.read_text(encoding="utf-8"), "Version 2 content")

        target_file.write_text("Version 3 content", encoding="utf-8")
        third_backup = create_safe_backup(target_file)
        self.assertEqual(third_backup.name, "config.txt.bak.2")
        self.assertEqual(third_backup.read_text(encoding="utf-8"), "Version 3 content")

    def test_manifest_state_and_clean_uninstall_created_file(self) -> None:
        config_data = {
            "scope": "workspace",
            "write_mode": "append",
            "tools": {"claude": True},
            "mcp": {"enabled": False},
            "skills": {"enabled": False},
            "hooks": {"git_pre_commit": False},
        }
        plan = build_plan_from_config(config_data, self.workspace_directory, home_dir=self.home_directory)
        success_count, error_count = execute_plan(plan, dry_run=False)
        self.assertEqual(error_count, 0)
        self.assertGreater(success_count, 0)

        manifest_file = self.workspace_directory / STATE_MANIFEST_FILE
        self.assertTrue(manifest_file.is_file())
        manifest_dict = json.loads(manifest_file.read_text(encoding="utf-8"))
        self.assertEqual(manifest_dict["schema_version"], 1)

        claude_file = self.workspace_directory / "CLAUDE.md"
        self.assertTrue(claude_file.is_file())

        uninstall_success, uninstall_error = uninstall_configuration(
            self.workspace_directory, restore_backups=True, dry_run=False
        )
        self.assertEqual(uninstall_error, 0)
        self.assertFalse(claude_file.exists())
        self.assertFalse(manifest_file.exists())

    def test_clean_uninstall_preserves_user_rules(self) -> None:
        claude_file = self.workspace_directory / "CLAUDE.md"
        user_instructions = "# My Custom Instructions\nNever remove this custom line."
        claude_file.write_text(user_instructions, encoding="utf-8")

        config_data = {
            "scope": "workspace",
            "write_mode": "append",
            "tools": {"claude": True},
            "mcp": {"enabled": False},
            "skills": {"enabled": False},
            "hooks": {"git_pre_commit": False},
        }
        plan = build_plan_from_config(config_data, self.workspace_directory, home_dir=self.home_directory)
        execute_plan(plan, dry_run=False)

        combined_text = claude_file.read_text(encoding="utf-8")
        self.assertIn("Never remove this custom line.", combined_text)
        self.assertIn("<!-- BEGIN AI-DEV-TOOLS -->", combined_text)

        uninstall_configuration(self.workspace_directory, restore_backups=False, dry_run=False)

        self.assertTrue(claude_file.is_file())
        cleaned_text = claude_file.read_text(encoding="utf-8")
        self.assertIn("Never remove this custom line.", cleaned_text)
        self.assertNotIn("<!-- BEGIN AI-DEV-TOOLS -->", cleaned_text)
        self.assertNotIn("<!-- END AI-DEV-TOOLS -->", cleaned_text)

    def test_detect_workspace_integrations(self) -> None:
        (self.workspace_directory / ".cursor").mkdir()
        (self.workspace_directory / "CLAUDE.md").write_text("# Claude", encoding="utf-8")

        detection_results = detect_workspace_integrations(self.workspace_directory)
        detected_names = set(detection_results["detected_tools"])
        self.assertIn("cursor", detected_names)
        self.assertIn("claude", detected_names)
        self.assertNotIn("windsurf", detected_names)

    def test_validate_config_schema(self) -> None:
        valid_config = {
            "version": 1,
            "scope": "workspace",
            "write_mode": "append",
            "tools": {"claude": True},
        }
        self.assertEqual(validate_config_schema(valid_config), [])

        invalid_config = {
            "version": 1,
            "unknown_attribute": "bad",
            "write_mode": "invalid_mode",
            "scope": "invalid_scope",
        }
        schema_warnings = validate_config_schema(invalid_config)
        self.assertTrue(any("unknown_attribute" in warning for warning in schema_warnings))
        self.assertTrue(any("write_mode" in warning for warning in schema_warnings))
        self.assertTrue(any("scope" in warning for warning in schema_warnings))

    def test_plan_preview_with_diff(self) -> None:
        config_data = {
            "scope": "workspace",
            "write_mode": "append",
            "tools": {"claude": True},
        }
        plan = build_plan_from_config(config_data, self.workspace_directory, home_dir=self.home_directory)
        preview_text = format_plan_preview(plan, show_diff=True)
        self.assertIn("DETAILED FILE DIFFS", preview_text)
        self.assertIn("--- a/CLAUDE.md", preview_text)
        self.assertIn("+++ b/CLAUDE.md", preview_text)

    def test_lint_fixer_diff_backup_and_idempotence(self) -> None:
        sample_code = "def check_item(target_val):\n    if target_val == None:\n        return True\n"
        sample_path = self.workspace_directory / "sample.py"
        sample_path.write_text(sample_code, encoding="utf-8")

        fixes_applied = fix_file(
            sample_path,
            dry_run=False,
            fix_emojis=False,
            show_diff=True,
            create_backup=True,
        )
        self.assertEqual(fixes_applied, 1)

        fixed_content = sample_path.read_text(encoding="utf-8")
        self.assertIn("is None", fixed_content)
        self.assertNotIn("== None", fixed_content)

        backup_file = self.workspace_directory / "sample.py.bak"
        self.assertTrue(backup_file.is_file())
        self.assertIn("== None", backup_file.read_text(encoding="utf-8"))

        second_pass_fixes = fix_file(
            sample_path,
            dry_run=False,
            fix_emojis=False,
            show_diff=False,
            create_backup=False,
        )
        self.assertEqual(second_pass_fixes, 0)

        restored_count = rollback_backups(self.workspace_directory)
        self.assertEqual(restored_count, 1)
        self.assertIn("== None", sample_path.read_text(encoding="utf-8"))
        self.assertFalse(backup_file.exists())


if __name__ == "__main__":
    unittest.main()
