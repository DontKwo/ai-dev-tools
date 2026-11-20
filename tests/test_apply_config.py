"""Unit tests for apply_config runner script."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from apply_config import (
    build_plan_from_config,
    execute_plan,
    format_plan_preview,
)
from yaml_utils import load_yaml_file


class TestApplyConfig(unittest.TestCase):
    """Validates configuration planning, previewing, and execution."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.ws_dir = Path(self.temp_dir.name)
        self.home_dir = self.ws_dir / "home"
        self.home_dir.mkdir()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_build_plan_new_files(self) -> None:
        config = {
            "scope": "workspace",
            "write_mode": "append",
            "tools": {"claude": True, "cursor": False},
            "profile": {"level": "strict"},
            "mcp": {"enabled": True},
            "skills": {"enabled": True, "bundle": "core"},
            "hooks": {"git_pre_commit": False},
        }
        plan = build_plan_from_config(config, self.ws_dir, home_dir=self.home_dir)
        self.assertEqual(plan.profile_name, "strict")
        self.assertEqual(plan.write_mode, "append")
        self.assertFalse(plan.git_hook_enabled)
        self.assertTrue(plan.mcp_enabled)
        self.assertEqual(len(plan.rule_actions), 1)

        rule_action = plan.rule_actions[0]
        self.assertEqual(rule_action.tool_key, "claude")
        self.assertFalse(rule_action.file_exists)
        self.assertFalse(rule_action.data_loss_risk)

    def test_build_plan_overwrite_data_loss_warning(self) -> None:
        existing_file = self.ws_dir / "CLAUDE.md"
        existing_file.write_text("# Existing Custom Instructions\nCustom rule line.", encoding="utf-8")

        config = {
            "scope": "workspace",
            "write_mode": "overwrite",
            "tools": {"claude": True},
            "profile": {"level": "strict"},
        }
        plan = build_plan_from_config(config, self.ws_dir, home_dir=self.home_dir)
        rule_action = plan.rule_actions[0]
        self.assertTrue(rule_action.file_exists)
        self.assertTrue(rule_action.data_loss_risk)
        self.assertIn("DATA LOSS RISK", rule_action.risk_description)
        self.assertIn("CLAUDE.md.bak", rule_action.risk_description)

    def test_execute_plan_creates_backup_on_overwrite(self) -> None:
        existing_file = self.ws_dir / "CLAUDE.md"
        original_content = "# Previous Custom Rules"
        existing_file.write_text(original_content, encoding="utf-8")

        config = {
            "scope": "workspace",
            "write_mode": "overwrite",
            "tools": {"claude": True},
            "mcp": {"enabled": False},
            "skills": {"enabled": False},
            "hooks": {"git_pre_commit": False},
        }
        plan = build_plan_from_config(config, self.ws_dir, home_dir=self.home_dir)
        successes, errors = execute_plan(plan, dry_run=False)

        self.assertEqual(errors, 0)
        self.assertGreater(successes, 0)
        backup_file = self.ws_dir / "CLAUDE.md.bak"
        self.assertTrue(backup_file.is_file())
        self.assertEqual(backup_file.read_text(encoding="utf-8"), original_content)

    def test_execute_plan_safe_append_preserves_content(self) -> None:
        existing_file = self.ws_dir / "CLAUDE.md"
        user_header = "# Custom User Section\nDo not delete me."
        existing_file.write_text(user_header, encoding="utf-8")

        config = {
            "scope": "workspace",
            "write_mode": "append",
            "tools": {"claude": True},
            "mcp": {"enabled": False},
            "skills": {"enabled": False},
            "hooks": {"git_pre_commit": False},
        }
        plan = build_plan_from_config(config, self.ws_dir, home_dir=self.home_dir)
        execute_plan(plan, dry_run=False)

        updated_text = existing_file.read_text(encoding="utf-8")
        self.assertIn("# Custom User Section", updated_text)
        self.assertIn("Do not delete me.", updated_text)
        self.assertIn("BEGIN AI-DEV-TOOLS", updated_text)

    def test_format_plan_preview(self) -> None:
        config = {
            "scope": "workspace",
            "write_mode": "append",
            "tools": {"claude": True},
            "profile": {"level": "standard"},
            "mcp": {"enabled": True},
            "skills": {"enabled": True, "bundle": "core"},
            "hooks": {"git_pre_commit": True},
        }
        plan = build_plan_from_config(config, self.ws_dir, home_dir=self.home_dir)
        preview_text = format_plan_preview(plan)

        self.assertIn("AI-DEV-TOOLS CONFIGURATION PLAN", preview_text)
        self.assertIn("Workspace", preview_text)
        self.assertIn("Profile    : standard", preview_text)
        self.assertIn("CLAUDE.md", preview_text)

    def test_default_config_yaml_loads_and_builds_plan(self) -> None:
        cfg_path = REPO_ROOT / "config.yaml"
        self.assertTrue(cfg_path.is_file())
        loaded = load_yaml_file(cfg_path)
        self.assertEqual(loaded.get("version"), 1)
        plan = build_plan_from_config(loaded, self.ws_dir, home_dir=self.home_dir)
        self.assertEqual(plan.profile_name, "strict")
        self.assertTrue(plan.mcp_enabled)
        self.assertTrue(plan.skills_enabled)
        self.assertTrue(plan.git_hook_enabled)


if __name__ == "__main__":
    unittest.main()
