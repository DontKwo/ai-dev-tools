import json
import subprocess
import tempfile
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from scripts.doctor import (
    check_ci_workflows,
    check_git_tracking,
    check_installed_skills,
    check_python_version,
    check_ui_helpers,
    inspect_mcp_config,
)


class TestDoctor(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_check_installed_skills(self) -> None:
        # A better approach for pathlib testing is to actually create temp files
        repo = self.root / "repo"
        skills = repo / "skills"
        skills.mkdir(parents=True)

        (skills / "skill1").mkdir()
        (skills / "skill2").mkdir()
        (skills / "not_a_dir").touch()

        home_dir = self.root / "home"
        dest_skills = home_dir / ".gemini" / "antigravity" / "skills"
        dest_skills.mkdir(parents=True)

        # Install skill 1 correctly
        skill1_dest = dest_skills / "skill1"
        skill1_dest.mkdir()
        (skill1_dest / "SKILL.md").touch()

        # Skill 2 missing

        status = check_installed_skills(repo, home_dir)
        self.assertIn("skill1", status)
        self.assertIn("skill2", status)
        self.assertNotIn("not_a_dir", status)
        self.assertTrue(status["skill1"])
        self.assertFalse(status["skill2"])

    def test_inspect_mcp_config_missing(self) -> None:
        mcp_path = self.root / "missing.json"
        info = inspect_mcp_config(mcp_path)
        self.assertFalse(info["exists"])

    def test_inspect_mcp_config_corrupted(self) -> None:
        mcp_path = self.root / "corrupted.json"
        mcp_path.write_text("{ invalid json", encoding="utf-8")
        info = inspect_mcp_config(mcp_path)
        self.assertTrue(info["exists"])
        self.assertTrue(info["corrupted"])

    def test_inspect_mcp_config_not_registered(self) -> None:
        mcp_path = self.root / "not_registered.json"
        mcp_path.write_text(json.dumps({"mcpServers": {"other-tool": {}}}), encoding="utf-8")
        info = inspect_mcp_config(mcp_path)
        self.assertTrue(info["exists"])
        self.assertFalse(info["is_registered"])

    def test_inspect_mcp_config_valid(self) -> None:
        mcp_path = self.root / "valid.json"

        cmd_path = self.root / "python"
        cmd_path.touch()

        script_path = self.root / "server.py"
        script_path.touch()

        config = {
            "mcpServers": {
                "ai-dev-tools": {
                    "command": str(cmd_path),
                    "args": ["run", str(script_path)]
                }
            }
        }
        mcp_path.write_text(json.dumps(config), encoding="utf-8")

        info = inspect_mcp_config(mcp_path)
        self.assertTrue(info["exists"])
        self.assertTrue(info["is_registered"])
        self.assertFalse(info["corrupted"])
        self.assertTrue(info["command_valid"])
        self.assertTrue(info["script_valid"])

    def test_inspect_mcp_config_invalid_paths(self) -> None:
        mcp_path = self.root / "invalid.json"

        config = {
            "mcpServers": {
                "ai-dev-tools": {
                    "command": "/does/not/exist",
                    "args": ["run", "/also/missing/server.py"]
                }
            }
        }
        mcp_path.write_text(json.dumps(config), encoding="utf-8")

        info = inspect_mcp_config(mcp_path)
        self.assertTrue(info["exists"])
        self.assertTrue(info["is_registered"])
        self.assertFalse(info["command_valid"])
        self.assertFalse(info["script_valid"])

    @patch("scripts.doctor.shutil.which")
    def test_check_git_tracking_no_git(self, mock_which: MagicMock) -> None:
        mock_which.return_value = None
        info = check_git_tracking(self.root)
        self.assertFalse(info["has_git"])

    @patch("scripts.doctor.shutil.which")
    @patch("scripts.doctor.subprocess.run")
    def test_check_git_tracking_not_repo(self, mock_run: MagicMock, mock_which: MagicMock) -> None:
        mock_which.return_value = "/usr/bin/git"
        mock_run.side_effect = subprocess.CalledProcessError(128, "git")
        info = check_git_tracking(self.root)
        self.assertTrue(info["has_git"])
        self.assertFalse(info["is_repo"])

    @patch("scripts.doctor.shutil.which")
    @patch("scripts.doctor.subprocess.run")
    def test_check_git_tracking_no_remote(self, mock_run: MagicMock, mock_which: MagicMock) -> None:
        mock_which.return_value = "/usr/bin/git"

        # First call works (is repo), second call fails (no remote)
        mock_is_inside = MagicMock()
        mock_is_inside.returncode = 0

        mock_remote = MagicMock()
        mock_remote.returncode = 128

        mock_run.side_effect = [mock_is_inside, mock_remote]

        info = check_git_tracking(self.root)
        self.assertTrue(info["is_repo"])
        self.assertFalse(info["has_tracking"])
        self.assertEqual(info["branch"], "")

    @patch("scripts.doctor.shutil.which")
    @patch("scripts.doctor.subprocess.run")
    def test_check_git_tracking_success(self, mock_run: MagicMock, mock_which: MagicMock) -> None:
        mock_which.return_value = "/usr/bin/git"

        mock_is_inside = MagicMock()
        mock_is_inside.returncode = 0

        mock_remote = MagicMock()
        mock_remote.returncode = 0
        mock_remote.stdout = "origin/main\n"

        mock_run.side_effect = [mock_is_inside, mock_remote]

        info = check_git_tracking(self.root)
        self.assertTrue(info["is_repo"])
        self.assertTrue(info["has_tracking"])
        self.assertEqual(info["branch"], "origin/main")

    def test_check_python_version_no_toml(self) -> None:
        info = check_python_version(self.root)
        self.assertFalse(info["has_toml"])

    def test_check_python_version_no_requires(self) -> None:
        toml = self.root / "pyproject.toml"
        toml.write_text("[tool.something]\nkey = 'value'", encoding="utf-8")
        info = check_python_version(self.root)
        self.assertTrue(info["has_toml"])
        self.assertEqual(info["requires_python"], "")
        self.assertTrue(info["meets_req"])

    @patch("scripts.doctor.sys.version_info")
    def test_check_python_version_meets_req(self, mock_version: MagicMock) -> None:
        mock_version.major = 3
        mock_version.minor = 10

        toml = self.root / "pyproject.toml"
        toml.write_text("requires-python = '>=3.9'", encoding="utf-8")

        info = check_python_version(self.root)
        self.assertTrue(info["has_toml"])
        self.assertEqual(info["requires_python"], ">=3.9")
        self.assertTrue(info["meets_req"])

    @patch("scripts.doctor.sys.version_info")
    def test_check_python_version_fails_req(self, mock_version: MagicMock) -> None:
        mock_version.major = 3
        mock_version.minor = 8

        toml = self.root / "pyproject.toml"
        toml.write_text("requires-python = '>=3.10'", encoding="utf-8")

        info = check_python_version(self.root)
        self.assertTrue(info["has_toml"])
        self.assertEqual(info["requires_python"], ">=3.10")
        self.assertFalse(info["meets_req"])

    def test_check_ui_helpers(self) -> None:
        helpers = check_ui_helpers(Path(__file__).resolve().parent.parent)
        self.assertIn("pyqt", helpers)
        self.assertIn("web", helpers)
        self.assertTrue(all(helpers.values()))

    def test_check_ci_workflows_valid_release(self) -> None:
        wf_dir = self.root / ".github" / "workflows"
        wf_dir.mkdir(parents=True)
        (self.root / "package.json").write_text('{"name":"app","version":"1.2.3"}', encoding="utf-8")
        (self.root / "src-tauri").mkdir()
        (wf_dir / "release.yml").write_text(
            "on:\n  push:\n    branches: [main]\n  pull_request:\n    branches: [main]\n"
            "files: App_1.2.3_x64-setup.exe App_1.2.3_x64_en-US.msi\n",
            encoding="utf-8",
        )
        info = check_ci_workflows(self.root)
        self.assertTrue(info["has_workflows"])
        self.assertEqual(info["warnings"], [])
        self.assertGreaterEqual(len(info["ok"]), 3)  # type: ignore[arg-type]

    def test_check_ci_workflows_detects_mismatches_and_missing_triggers(self) -> None:
        wf_dir = self.root / ".github" / "workflows"
        wf_dir.mkdir(parents=True)
        (self.root / "package.json").write_text('{"name":"app","version":"2.0.0"}', encoding="utf-8")
        (wf_dir / "release.yml").write_text(
            "on:\n  push:\n    tags: ['v*']\n"
            "files: App_1.0.0_x64-setup.exe\n",
            encoding="utf-8",
        )
        info = check_ci_workflows(self.root)
        warnings_joined = "\n".join(info["warnings"])  # type: ignore[arg-type]
        self.assertIn("pull_request:", warnings_joined)
        self.assertIn(".msi", warnings_joined)
        self.assertIn("1.0.0", warnings_joined)

    def test_check_ci_workflows_warns_on_static_latest_tag(self) -> None:
        wf_dir = self.root / ".github" / "workflows"
        wf_dir.mkdir(parents=True)
        (wf_dir / "release.yml").write_text(
            "on:\n  push:\n    branches: [main]\n  pull_request:\n    branches: [main]\n"
            "with:\n  tag_name: ${{ startsWith(github.ref, 'refs/tags/v') && github.ref_name || 'latest' }}\n",
            encoding="utf-8",
        )
        info = check_ci_workflows(self.root)
        warnings_joined = "\n".join(info["warnings"])  # type: ignore[arg-type]
        self.assertIn("static 'latest' tag_name", warnings_joined)

    def test_check_ci_workflows_warns_on_android_debug_signing_and_cleartext(self) -> None:
        wf_dir = self.root / ".github" / "workflows"
        wf_dir.mkdir(parents=True)
        (wf_dir / "release.yml").write_text(
            "on:\n  push:\n    branches: [main]\n  pull_request:\n    branches: [main]\n"
            "steps:\n  - run: gradle assembleRelease\n",
            encoding="utf-8",
        )
        android_app = self.root / "android" / "app"
        manifest_dir = android_app / "src" / "main"
        manifest_dir.mkdir(parents=True)
        (android_app / "build.gradle").write_text(
            "android {\n  buildTypes {\n    release {\n      signingConfig signingConfigs.debug\n    }\n  }\n}\n",
            encoding="utf-8",
        )
        (manifest_dir / "AndroidManifest.xml").write_text(
            '<manifest><application android:usesCleartextTraffic="true" /></manifest>\n',
            encoding="utf-8",
        )
        info = check_ci_workflows(self.root)
        warnings_joined = "\n".join(info["warnings"])  # type: ignore[arg-type]
        self.assertIn("signingConfigs.debug", warnings_joined)
        self.assertIn("usesCleartextTraffic", warnings_joined)

if __name__ == "__main__":
    unittest.main()
