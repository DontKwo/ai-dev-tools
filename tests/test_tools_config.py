import tempfile
import unittest
from pathlib import Path

from scripts.tools_config import (
    AiToolsConfig,
    generate_default_config,
    load_tools_config,
    parse_toml_content,
    resolve_linter_profile,
    save_tools_config,
)


class TestToolsConfig(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_default_config_values(self) -> None:
        cfg = AiToolsConfig()
        self.assertIn("antigravity", cfg.tools)
        self.assertIn("claude", cfg.tools)
        self.assertIn("cursor", cfg.tools)
        self.assertEqual(cfg.linter_level, "strict")
        self.assertTrue(cfg.linter_diff_only)
        self.assertTrue(cfg.is_skill_enabled("any-skill"))

    def test_parse_toml_content(self) -> None:
        sample = """
        [tools]
        configured = ["claude", "cursor"]

        [skills]
        targets = ["claude", "antigravity"]
        enabled = ["lint-and-fix"]
        disabled = ["doc-to-markdown"]

        [linter]
        level = "full"
        diff_only = false
        skip = [38, 41]
        """
        data = parse_toml_content(sample)
        self.assertEqual(data["tools"]["configured"], ["claude", "cursor"])
        self.assertEqual(data["skills"]["enabled"], ["lint-and-fix"])
        self.assertEqual(data["skills"]["disabled"], ["doc-to-markdown"])
        self.assertEqual(data["linter"]["level"], "full")
        self.assertFalse(data["linter"]["diff_only"])
        self.assertEqual(data["linter"]["skip"], [38, 41])

    def test_load_and_save_roundtrip(self) -> None:
        cfg_file = self.root / ".aitools.toml"
        cfg = AiToolsConfig(
            tools=["cursor", "claude"],
            skill_targets=["claude"],
            enabled_skills=["ux-audit"],
            disabled_skills=["secret-sanitizer"],
            linter_level="standard",
            linter_diff_only=False,
            linter_skip=[1, 2],
        )
        save_tools_config(cfg_file, cfg)
        self.assertTrue(cfg_file.is_file())

        loaded = load_tools_config(self.root)
        self.assertEqual(loaded.tools, ["cursor", "claude"])
        self.assertEqual(loaded.skill_targets, ["claude"])
        self.assertEqual(loaded.enabled_skills, ["ux-audit"])
        self.assertEqual(loaded.disabled_skills, ["secret-sanitizer"])
        self.assertEqual(loaded.linter_level, "standard")
        self.assertFalse(loaded.linter_diff_only)
        self.assertEqual(loaded.linter_skip, [1, 2])

    def test_skill_enablement_logic(self) -> None:
        cfg = AiToolsConfig(
            enabled_skills=["skill1", "skill2"],
            disabled_skills=["skill2"],
        )
        self.assertTrue(cfg.is_skill_enabled("skill1"))
        self.assertFalse(cfg.is_skill_enabled("skill2"))
        self.assertFalse(cfg.is_skill_enabled("skill3"))

    def test_generate_default_config(self) -> None:
        content = generate_default_config()
        self.assertIn("[tools]", content)
        self.assertIn("[skills]", content)
        self.assertIn("[linter]", content)
        self.assertIn("targets = ", content)
        self.assertIn("profile = ", content)
        self.assertIn("disable = ", content)
        self.assertIn("enable = ", content)

    def test_default_profile_is_strict(self) -> None:
        cfg = AiToolsConfig()
        self.assertEqual(cfg.linter_profile, "strict")
        self.assertEqual(cfg.linter_level, "strict")
        self.assertEqual(cfg.linter_skip, [])

    def test_profile_standard_loading(self) -> None:
        sample = """
        [linter]
        profile = "standard"
        """
        cfg_file = self.root / ".aitools.toml"
        cfg_file.write_text(sample, encoding="utf-8")
        loaded = load_tools_config(self.root)
        self.assertEqual(loaded.linter_profile, "standard")
        self.assertEqual(loaded.linter_level, "standard")
        self.assertIn(1, loaded.linter_skip)
        self.assertIn(5, loaded.linter_skip)
        self.assertIn(17, loaded.linter_skip)
        self.assertIn(38, loaded.linter_skip)

    def test_profile_safe_loading(self) -> None:
        sample = """
        [linter]
        profile = "safe"
        """
        cfg_file = self.root / ".aitools.toml"
        cfg_file.write_text(sample, encoding="utf-8")
        loaded = load_tools_config(self.root)
        self.assertEqual(loaded.linter_profile, "safe")
        self.assertEqual(loaded.linter_level, "standard")
        self.assertIn(11, loaded.linter_skip)
        self.assertIn(24, loaded.linter_skip)
        self.assertIn(25, loaded.linter_skip)

    def test_rule_disable_and_enable_overrides(self) -> None:
        sample = """
        [linter]
        profile = "standard"
        disable = [30]
        enable = [1]
        """
        cfg_file = self.root / ".aitools.toml"
        cfg_file.write_text(sample, encoding="utf-8")
        loaded = load_tools_config(self.root)
        self.assertIn(30, loaded.linter_skip)
        self.assertNotIn(1, loaded.linter_skip)
        self.assertIn(5, loaded.linter_skip)

    def test_custom_profile_definition(self) -> None:
        sample = """
        [linter]
        profile = "team_profile"

        [linter.profiles.team_profile]
        level = "full"
        skip = [2, 3]
        """
        cfg_file = self.root / ".aitools.toml"
        cfg_file.write_text(sample, encoding="utf-8")
        loaded = load_tools_config(self.root)
        self.assertEqual(loaded.linter_profile, "team_profile")
        self.assertEqual(loaded.linter_level, "full")
        self.assertEqual(loaded.linter_skip, [2, 3])

    def test_resolve_linter_profile_function(self) -> None:
        strict_info = resolve_linter_profile("strict")
        self.assertEqual(strict_info["level"], "strict")
        self.assertEqual(strict_info["skip"], [])

        safe_info = resolve_linter_profile("safe")
        self.assertEqual(safe_info["level"], "standard")
        self.assertIn(11, safe_info["skip"])


if __name__ == "__main__":
    unittest.main()
