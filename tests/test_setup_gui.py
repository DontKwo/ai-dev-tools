"""Unit tests for setup_gui model, configuration, and preset loading."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from setup_gui import SetupGuiModel, _import_tk_modules


class TestSetupGui(unittest.TestCase):
    """Validates SetupGuiModel state transitions, preset loading, and plan calculation."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.ws_dir = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_default_model_state(self) -> None:
        model = SetupGuiModel(workspace=str(self.ws_dir))
        self.assertEqual(model.write_mode, "append")
        self.assertEqual(model.profile_level, "strict")
        self.assertTrue(model.mcp_enabled)
        self.assertTrue(model.skills_enabled)
        self.assertTrue(model.git_hook_enabled)
        self.assertTrue(model.tools["claude"])
        self.assertTrue(model.tools["cursor"])

    def test_model_to_config_dict(self) -> None:
        model = SetupGuiModel(workspace=str(self.ws_dir), profile_level="standard", write_mode="overwrite")
        cfg = model.to_config_dict()
        self.assertEqual(cfg["version"], 1)
        self.assertEqual(cfg["scope"], "workspace")
        self.assertEqual(cfg["write_mode"], "overwrite")
        self.assertEqual(cfg["profile"]["level"], "standard")
        self.assertTrue(cfg["tools"]["claude"])

    def test_load_from_config_dict(self) -> None:
        model = SetupGuiModel(workspace=str(self.ws_dir))
        custom_cfg = {
            "scope": "global",
            "write_mode": "skip",
            "profile": {"level": "safe"},
            "tools": {"claude": True, "cursor": False},
            "mcp": {"enabled": False},
            "skills": {"enabled": False, "bundle": "core"},
            "hooks": {"git_pre_commit": False},
        }
        model.load_from_config_dict(custom_cfg)
        self.assertEqual(model.scope, "global")
        self.assertEqual(model.write_mode, "skip")
        self.assertEqual(model.profile_level, "safe")
        self.assertFalse(model.tools["cursor"])
        self.assertFalse(model.mcp_enabled)
        self.assertFalse(model.skills_enabled)
        self.assertFalse(model.git_hook_enabled)

    def test_load_presets(self) -> None:
        model = SetupGuiModel(workspace=str(self.ws_dir))
        model.load_preset("safe")
        self.assertEqual(model.profile_level, "safe")
        self.assertFalse(model.git_hook_enabled)

        model.load_preset("full")
        self.assertEqual(model.profile_level, "strict")
        self.assertTrue(model.git_hook_enabled)

    def test_calculate_plan_from_model(self) -> None:
        model = SetupGuiModel(workspace=str(self.ws_dir))
        plan = model.calculate_plan()
        self.assertEqual(plan.profile_name, "strict")
        self.assertEqual(plan.workspace_path, str(self.ws_dir.resolve()))
        self.assertGreater(len(plan.rule_actions), 0)

    def test_import_tk_modules(self) -> None:
        tk_mod, ttk_mod, fd_mod, mb_mod = _import_tk_modules()
        self.assertIsNotNone(tk_mod)
        self.assertIsNotNone(ttk_mod)
        self.assertIsNotNone(fd_mod)
        self.assertIsNotNone(mb_mod)


if __name__ == "__main__":
    unittest.main()
