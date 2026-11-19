import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from configure import (
    PlannedAction,
    ask_user_plan_confirmation,
    build_instructions,
    configure_mcp_servers,
    configure_skills,
    create_setup_plan,
    execute_setup_plan,
    get_tool_definitions,
    install_file,
    remove_tool_targets,
    render_plan_summary,
)


class TestConfigure(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp()).resolve()
        self.mock_home = self.temp_dir / "home"
        self.mock_ws = self.temp_dir / "workspace"
        self.mock_repo = self.temp_dir / "repo"
        self.mock_home.mkdir(parents=True)
        self.mock_ws.mkdir(parents=True)
        self.mock_repo.mkdir(parents=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_get_tool_definitions(self) -> None:
        # get_user_home is already patched in setUp, but need to patch it for the actual configure module scope
        with patch("configure.get_user_home", return_value=self.mock_home):
            defs = get_tool_definitions(self.mock_ws)
        expected_tools = ["claude", "cursor", "cline", "antigravity", "codex", "windsurf", "copilot", "aider"]
        for tool in expected_tools:
            self.assertIn(tool, defs)

        cursor_def = defs["cursor"]
        self.assertIn("alwaysApply: true", cursor_def["frontmatter"])
        self.assertIn("globs: *", cursor_def["frontmatter"])

        claude_def = defs["claude"]
        self.assertEqual(claude_def["frontmatter"], "")

        # Verify workspace paths use the provided workspace
        self.assertTrue(any(str(self.mock_ws) in str(p) for p in cursor_def["workspace_paths"]))
        # Verify global paths use the home dir
        self.assertTrue(any(str(self.mock_home) in str(p) for p in cursor_def["global_paths"]))

    @patch("configure.calc_linter_command", return_value="uv run python linter.py")
    def test_build_instructions(self, mock_calc: MagicMock) -> None:
        mock_template = MagicMock()
        mock_template.read_text.return_value = "Linter: {{LINTER_COMMAND}}\nEng Rules: {{ENGINEERING_RULES_PATH}}\nPy Rules: {{PYTHON_RULES_PATH}}\n"

        with patch("configure.TEMPLATE_PATH", mock_template):
            with patch("configure.format_command_path", side_effect=lambda x: str(x).replace("/workspace/", "rel/") if "workspace" in str(x) else str(x)):
                content = build_instructions()
        self.assertIn("Linter: uv run python linter.py", content)
        self.assertNotIn("{{LINTER_COMMAND}}", content)
        self.assertNotIn("{{ENGINEERING_RULES_PATH}}", content)
        self.assertNotIn("{{PYTHON_RULES_PATH}}", content)

        frontmatter = "---\nfrontmatter\n---\n"
        with patch("configure.TEMPLATE_PATH", mock_template):
            with patch("configure.format_command_path", side_effect=lambda x: str(x)):
                content_with_fm = build_instructions(frontmatter)
        self.assertTrue(content_with_fm.startswith(frontmatter))
        self.assertIn("Linter: uv run python linter.py", content_with_fm)

    def test_configure_mcp_servers(self) -> None:
        mcp_script = self.mock_repo / "mcp" / "server.py"
        mcp_script.parent.mkdir()
        mcp_script.touch()

        # Create existing MCP configs to ensure we don't clobber them
        cursor_mcp_path = self.mock_ws / ".cursor" / "mcp.json"
        cursor_mcp_path.parent.mkdir(parents=True)
        cursor_mcp_path.write_text(json.dumps({"mcpServers": {"other-server": {"command": "dummy"}}}), encoding="utf-8")

        windsurf_mcp_path = self.mock_home / ".codeium" / "windsurf" / "mcp_config.json"
        windsurf_mcp_path.parent.mkdir(parents=True)
        windsurf_mcp_path.write_text(json.dumps({"mcpServers": {"other": {"command": "dummy"}}}), encoding="utf-8")

        anti_mcp_path = self.mock_home / ".gemini" / "antigravity" / "mcp_config.json"
        anti_mcp_path.parent.mkdir(parents=True)
        anti_mcp_path.write_text(json.dumps({"mcpServers": {"other-gemini": {"command": "dummy"}}}), encoding="utf-8")

        import platform
        from scripts.utils import IS_WINDOWS
        if IS_WINDOWS:
            claude_mcp_path_desktop = self.mock_home / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"  # noqa: 91
        elif platform.system() == "Darwin":
            claude_mcp_path_desktop = self.mock_home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
        else:
            claude_mcp_path_desktop = self.mock_home / ".config" / "Claude" / "claude_desktop_config.json"

        claude_mcp_path_desktop.parent.mkdir(parents=True)
        claude_mcp_path_desktop.write_text(json.dumps({"mcpServers": {"other-claude": {"command": "dummy"}}}), encoding="utf-8")

        with patch("configure.get_user_home", return_value=self.mock_home):
            configure_mcp_servers(
                repo_root=self.mock_repo,
                scope="both",
                workspace=self.mock_ws,
                tools=["claude", "cursor", "windsurf", "antigravity"],
            )

        data = json.loads(cursor_mcp_path.read_text(encoding="utf-8"))
        self.assertIn("other-server", data["mcpServers"])
        self.assertIn("ai-dev-tools", data["mcpServers"])
        self.assertIn("command", data["mcpServers"]["ai-dev-tools"])
        self.assertIn("args", data["mcpServers"]["ai-dev-tools"])

        data_ws = json.loads(windsurf_mcp_path.read_text(encoding="utf-8"))
        self.assertIn("other", data_ws["mcpServers"])
        self.assertIn("ai-dev-tools", data_ws["mcpServers"])
        self.assertIn("command", data_ws["mcpServers"]["ai-dev-tools"])
        self.assertIn("args", data_ws["mcpServers"]["ai-dev-tools"])

        # Antigravity tests
        data_anti = json.loads(anti_mcp_path.read_text(encoding="utf-8"))
        self.assertIn("other-gemini", data_anti["mcpServers"])
        self.assertIn("ai-dev-tools", data_anti["mcpServers"])
        self.assertIn("command", data_anti["mcpServers"]["ai-dev-tools"])

        # Claude tests
        claude_mcp_path = self.mock_ws / ".claude.json"
        data_claude = json.loads(claude_mcp_path.read_text(encoding="utf-8"))
        self.assertIn("ai-dev-tools", data_claude["mcpServers"])
        self.assertIn("command", data_claude["mcpServers"]["ai-dev-tools"])

        data_claude_desktop = json.loads(claude_mcp_path_desktop.read_text(encoding="utf-8"))
        self.assertIn("other-claude", data_claude_desktop["mcpServers"])
        self.assertIn("ai-dev-tools", data_claude_desktop["mcpServers"])
        self.assertIn("command", data_claude_desktop["mcpServers"]["ai-dev-tools"])

        # Test remove functionality
        with patch("configure.get_user_home", return_value=self.mock_home):
            configure_mcp_servers(
                repo_root=self.mock_repo,
                scope="both",
                workspace=self.mock_ws,
                tools=["claude", "cursor", "windsurf", "antigravity"],
                remove=True,
            )

        data = json.loads(cursor_mcp_path.read_text(encoding="utf-8"))
        self.assertIn("other-server", data["mcpServers"])
        self.assertNotIn("ai-dev-tools", data["mcpServers"])

    def test_configure_skills(self) -> None:
        skills_dir = self.mock_repo / "skills"
        skills_dir.mkdir()
        skill_a = skills_dir / "skill_a"
        skill_a.mkdir()
        (skill_a / "SKILL.md").write_text("test")

        configure_skills(
            repo_root=self.mock_repo,
            scope="workspace",
            workspace=self.mock_ws,
        )

        target_dir = self.mock_ws / ".agent" / "skills" / "skill_a"
        self.assertTrue(target_dir.is_dir())
        self.assertTrue((target_dir / "SKILL.md").is_file())

        configure_skills(
            repo_root=self.mock_repo,
            scope="workspace",
            workspace=self.mock_ws,
            remove=True,
        )

        self.assertFalse(target_dir.exists())

    def test_install_file_appends_and_updates_idempotently(self) -> None:
        claude_md = self.mock_ws / "CLAUDE.md"
        claude_md.write_text("# User Project Rules\nKeep my rules.\n", encoding="utf-8")

        install_file(claude_md, "Rule v1\nPath scripts/script.py", default_action="append")
        first_text = claude_md.read_text(encoding="utf-8")
        self.assertIn("# User Project Rules\nKeep my rules.", first_text)
        self.assertIn("<!-- BEGIN AI-DEV-TOOLS -->", first_text)
        self.assertIn("Rule v1", first_text)

        install_file(claude_md, "Rule v2\nPath scripts/script.py", default_action="append")
        second_text = claude_md.read_text(encoding="utf-8")
        self.assertIn("# User Project Rules\nKeep my rules.", second_text)
        self.assertEqual(second_text.count("<!-- BEGIN AI-DEV-TOOLS -->"), 1)
        self.assertNotIn("Rule v1", second_text)
        self.assertIn("Rule v2", second_text)

    def test_install_file_preserves_mdc_frontmatter_and_remove_restores(self) -> None:
        mdc_file = self.mock_ws / ".cursor" / "rules" / "developer-rules.mdc"
        mdc_content = "---\ndescription: Rules\nglobs: *\nalwaysApply: true\n---\n\n# Body\nRule A"
        install_file(mdc_file, mdc_content, default_action="append")

        created = mdc_file.read_text(encoding="utf-8")
        self.assertTrue(created.startswith("---\ndescription: Rules\nglobs: *\nalwaysApply: true\n---\n\n<!-- BEGIN AI-DEV-TOOLS -->"))
        self.assertEqual(created.count("description: Rules"), 1)

        claude_md = self.mock_ws / "CLAUDE.md"
        claude_md.write_text("# Existing Header\n", encoding="utf-8")
        install_file(claude_md, "# Managed Body\n", default_action="append")

        with patch("configure.get_user_home", return_value=self.mock_home):
            remove_tool_targets(["claude", "cursor"], "workspace", self.mock_ws)

        self.assertFalse(mdc_file.exists())
        self.assertTrue(claude_md.exists())
        self.assertEqual(claude_md.read_text(encoding="utf-8"), "# Existing Header\n")

    def test_install_file_non_tty_ask_defaults_to_append(self) -> None:
        claude_md = self.mock_ws / "CLAUDE.md"
        claude_md.write_text("# Existing Custom Rules\n", encoding="utf-8")
        with patch("sys.stdin.isatty", return_value=False):
            install_file(claude_md, "# Managed", default_action="ask")
        text = claude_md.read_text(encoding="utf-8")
        self.assertIn("# Existing Custom Rules", text)
        self.assertIn("# Managed", text)

    def test_create_setup_plan(self) -> None:
        with patch("configure.get_user_home", return_value=self.mock_home):
            plan = create_setup_plan(
                repo_root=self.mock_repo,
                selected_tools=["claude"],
                scope="workspace",
                workspace=self.mock_ws,
                setup_rules=True,
                setup_mcp=True,
                setup_skills=False,
                init_custom_config=False,
            )
        self.assertTrue(len(plan) >= 2)
        rule_actions = [item for item in plan if item.category == "rule"]
        mcp_actions = [item for item in plan if item.category == "mcp"]
        self.assertEqual(len(rule_actions), 1)
        self.assertEqual(rule_actions[0].target_path, self.mock_ws / "CLAUDE.md")
        self.assertEqual(rule_actions[0].action_type, "create")
        self.assertEqual(len(mcp_actions), 1)
        self.assertEqual(mcp_actions[0].target_path, self.mock_ws / ".claude.json")

    def test_render_plan_summary(self) -> None:
        plan = [
            PlannedAction(
                category="rule",
                title="Claude Rules",
                description="Create rules at CLAUDE.md",
                target_path=self.mock_ws / "CLAUDE.md",
                action_type="create",
            ),
            PlannedAction(
                category="mcp",
                title="Claude Desktop MCP",
                description="Register MCP server in config",
                target_path=self.mock_home / "claude.json",
                action_type="register",
            ),
        ]
        summary = render_plan_summary(plan)
        self.assertIn("AI-DEV-TOOLS SETUP PLAN", summary)
        self.assertIn("Claude Rules", summary)
        self.assertIn("Claude Desktop MCP", summary)

    def test_ask_user_plan_confirmation_approve_all(self) -> None:
        plan = [
            PlannedAction(
                category="rule",
                title="Claude Rules",
                description="Create rules",
                target_path=self.mock_ws / "CLAUDE.md",
                action_type="create",
            ),
        ]
        with patch("builtins.input", return_value="A"):
            approved = ask_user_plan_confirmation(plan, self.mock_ws)
        self.assertEqual(len(approved), 1)
        self.assertEqual(approved[0].title, "Claude Rules")

    def test_ask_user_plan_confirmation_cancel(self) -> None:
        plan = [
            PlannedAction(
                category="rule",
                title="Claude Rules",
                description="Create rules",
                target_path=self.mock_ws / "CLAUDE.md",
                action_type="create",
            ),
        ]
        with patch("builtins.input", return_value="C"):
            approved = ask_user_plan_confirmation(plan, self.mock_ws)
        self.assertEqual(approved, [])

    def test_ask_user_plan_confirmation_individual_approval(self) -> None:
        item_one = PlannedAction(
            category="rule",
            title="Claude Rules",
            description="Create rules",
            target_path=self.mock_ws / "CLAUDE.md",
            action_type="create",
        )
        item_two = PlannedAction(
            category="mcp",
            title="MCP Config",
            description="Register MCP",
            target_path=self.mock_ws / ".claude.json",
            action_type="register",
        )
        inputs = ["i", "y", "n", "y"]
        with patch("builtins.input", side_effect=inputs):
            approved = ask_user_plan_confirmation([item_one, item_two], self.mock_ws)
        self.assertEqual(len(approved), 1)
        self.assertEqual(approved[0].title, "Claude Rules")

    def test_execute_setup_plan(self) -> None:
        target_rule = self.mock_ws / "CLAUDE.md"
        plan = [
            PlannedAction(
                category="rule",
                title="Claude Rules",
                description="Create rules",
                target_path=target_rule,
                action_type="create",
                metadata={"frontmatter": "", "default_action": "append"},
            ),
        ]
        with patch("configure.calc_linter_command", return_value="aitools lint"):
            execute_setup_plan(plan, self.mock_ws, action="append", dry_run=False)
        self.assertTrue(target_rule.exists())
        self.assertIn("<!-- BEGIN AI-DEV-TOOLS -->", target_rule.read_text(encoding="utf-8"))

    def test_create_setup_plan_with_linter_profile(self) -> None:
        plan = create_setup_plan(
            repo_root=self.mock_repo,
            selected_tools=["claude"],
            scope="workspace",
            workspace=self.mock_ws,
            setup_rules=False,
            setup_mcp=False,
            setup_skills=False,
            init_custom_config=False,
            linter_profile="safe",
            linter_disable=[1, 5],
        )
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0].category, "config")
        self.assertEqual(plan[0].metadata.get("profile"), "safe")
        self.assertEqual(plan[0].metadata.get("disable"), [1, 5])

    def test_execute_setup_plan_config_profile(self) -> None:
        target_cfg = self.mock_ws / ".aitools.toml"
        plan = [
            PlannedAction(
                category="config",
                title="Linter Profile (Safe)",
                description="Configure profile",
                target_path=target_cfg,
                action_type="create",
                metadata={"profile": "safe", "disable": [38]},
            )
        ]
        execute_setup_plan(plan, self.mock_ws, action="append", dry_run=False)
        self.assertTrue(target_cfg.is_file())
        content = target_cfg.read_text(encoding="utf-8")
        self.assertIn('profile = "safe"', content)


if __name__ == "__main__":
    unittest.main()
