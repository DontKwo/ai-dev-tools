"""Unit tests for unified WebView setup_gui model, HTTP server, and self-test."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from setup_gui import SetupGuiModel, SetupGuiServer, run_self_test


class TestSetupGui(unittest.TestCase):
    """Validates SetupGuiModel state transitions, WebView API server, and self-test."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.ws_dir = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_default_model_state(self) -> None:
        model = SetupGuiModel(workspace=str(self.ws_dir))
        self.assertEqual(model.write_mode, "append")
        self.assertEqual(model.profile_level, "strict")
        self.assertEqual(model.scope, "workspace")
        self.assertEqual(model.skip_rules, "")
        self.assertEqual(model.mcp_server_name, "ai-dev-tools")
        self.assertTrue(model.mcp_enabled)
        self.assertTrue(model.skills_enabled)
        self.assertTrue(model.git_hook_enabled)
        self.assertTrue(model.git_pre_push_enabled)
        self.assertTrue(model.tools["claude"])
        self.assertTrue(model.tools["cursor"])
        self.assertTrue(model.targets["claude_md"])

    def test_model_to_config_dict(self) -> None:
        model = SetupGuiModel(
            workspace=str(self.ws_dir),
            scope="global",
            profile_level="standard",
            write_mode="overwrite",
            skip_rules="10, 38",
            mcp_server_name="custom-mcp",
            git_hook_command="custom hook cmd",
        )
        model.targets["claude_md"] = False
        cfg = model.to_config_dict()
        self.assertEqual(cfg["version"], 1)
        self.assertEqual(cfg["scope"], "global")
        self.assertEqual(cfg["write_mode"], "overwrite")
        self.assertEqual(cfg["profile"]["level"], "standard")
        self.assertEqual(cfg["profile"]["skip_rules"], [10, 38])
        self.assertEqual(cfg["mcp"]["server_name"], "custom-mcp")
        self.assertEqual(cfg["hooks"]["command"], "custom hook cmd")
        self.assertFalse(cfg["targets"]["claude_md"])
        self.assertTrue(cfg["tools"]["claude"])

    def test_load_from_config_dict(self) -> None:
        model = SetupGuiModel(workspace=str(self.ws_dir))
        custom_cfg = {
            "scope": "global",
            "write_mode": "skip",
            "profile": {"level": "safe", "skip_rules": [12, 44]},
            "tools": {"claude": True, "cursor": False},
            "targets": {"claude_md": True, "cursorrules": False},
            "mcp": {"enabled": False, "server_name": "corp-mcp"},
            "skills": {"enabled": False, "bundle": "core"},
            "hooks": {"git_pre_commit": False, "command": "python test.py"},
        }
        model.load_from_config_dict(custom_cfg)
        self.assertEqual(model.scope, "global")
        self.assertEqual(model.write_mode, "skip")
        self.assertEqual(model.profile_level, "safe")
        self.assertEqual(model.skip_rules, "12, 44")
        self.assertFalse(model.tools["cursor"])
        self.assertFalse(model.targets["cursorrules"])
        self.assertFalse(model.mcp_enabled)
        self.assertEqual(model.mcp_server_name, "corp-mcp")
        self.assertFalse(model.skills_enabled)
        self.assertFalse(model.git_hook_enabled)
        self.assertEqual(model.git_hook_command, "python test.py")

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

    def test_auto_detect_model(self) -> None:
        (self.ws_dir / ".cursor").mkdir()
        model = SetupGuiModel(workspace=str(self.ws_dir))
        reasons = model.auto_detect()
        self.assertTrue(model.tools["cursor"])
        self.assertFalse(model.tools["windsurf"])
        self.assertIn("cursor", reasons)

    def test_webview_self_test_and_endpoints(self) -> None:
        self.assertEqual(run_self_test(), 0)
        srv = SetupGuiServer(SetupGuiModel(workspace=str(self.ws_dir)))
        srv.start()
        try:
            with urllib.request.urlopen(f"{srv.url}setup_gui_theme.css", timeout=5.0) as css_resp:
                css_txt = css_resp.read().decode("utf-8")
                self.assertIn("--astryx-primary", css_txt)
            req = urllib.request.Request(
                f"{srv.url}api/preset",
                data=json.dumps({"name": "safe", "state": srv.model.to_state_dict()}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5.0) as res:
                payload = json.loads(res.read().decode("utf-8"))
                self.assertEqual(payload["state"]["profile_level"], "safe")
        finally:
            srv.stop()


if __name__ == "__main__":
    unittest.main()
