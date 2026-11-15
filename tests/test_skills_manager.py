import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.skills_manager import (
    get_skill_status,
    get_tool_skill_dirs,
    install_single_skill,
    list_available_skills,
    parse_skill_metadata,
    remove_single_skill,
    sync_skills,
    toggle_skill_in_config,
)
from scripts.tools_config import AiToolsConfig


class TestSkillsManager(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.repo = self.root / "repo"
        self.skills_dir = self.repo / "skills"
        self.home = self.root / "home"
        self.ws = self.root / "ws"

        self.skills_dir.mkdir(parents=True)
        self.home.mkdir(parents=True)
        self.ws.mkdir(parents=True)

        # Create two sample skills
        skill1 = self.skills_dir / "test-skill-1"
        skill1.mkdir()
        (skill1 / "SKILL.md").write_text("---\nname: test-skill-1\ndescription: First sample skill.\n---\nBody", encoding="utf-8")

        skill2 = self.skills_dir / "test-skill-2"
        skill2.mkdir()
        (skill2 / "SKILL.md").write_text("---\nname: test-skill-2\ndescription: Second sample skill.\n---\nBody", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_list_available_skills(self) -> None:
        skills = list_available_skills(self.repo)
        self.assertEqual(len(skills), 2)
        names = {s.name for s in skills}
        self.assertIn("test-skill-1", names)
        self.assertIn("test-skill-2", names)

    def test_parse_skill_metadata(self) -> None:
        md_path = self.skills_dir / "test-skill-1" / "SKILL.md"
        desc = parse_skill_metadata(md_path)
        self.assertEqual(desc, "First sample skill.")

    def test_get_tool_skill_dirs(self) -> None:
        dirs = get_tool_skill_dirs(self.home, self.ws, scope="both")
        self.assertIn("agents", dirs)
        self.assertIn("claude", dirs)
        self.assertIn("cursor", dirs)
        self.assertIn("antigravity", dirs)
        self.assertTrue(any(str(self.home) in str(p) for p in dirs["claude"]))
        self.assertTrue(any(str(self.ws) in str(p) for p in dirs["claude"]))

    def test_install_and_remove_single_skill(self) -> None:
        target_dir = self.ws / ".claude" / "skills"
        skill1 = self.skills_dir / "test-skill-1"
        (skill1 / "agents").mkdir()
        (skill1 / "agents" / "openai.yaml").write_text('interface:\n  display_name: "Test Skill 1"\n', encoding="utf-8")
        (skill1 / "EXTRA.md").write_text("# Extra\n", encoding="utf-8")

        install_single_skill(skill1, target_dir)
        installed_md = target_dir / "test-skill-1" / "SKILL.md"
        installed_yaml = target_dir / "test-skill-1" / "agents" / "openai.yaml"
        installed_extra = target_dir / "test-skill-1" / "EXTRA.md"
        self.assertTrue(installed_md.is_file())
        self.assertTrue(installed_yaml.is_file())
        self.assertTrue(installed_extra.is_file())

        removed = remove_single_skill("test-skill-1", target_dir)
        self.assertTrue(removed)
        self.assertFalse(installed_md.exists())

    def test_list_available_skills_invocation_mode(self) -> None:
        user_skill = self.skills_dir / "user-only-skill"
        user_skill.mkdir()
        (user_skill / "SKILL.md").write_text(
            "---\nname: user-only-skill\ndisable-model-invocation: true\ndescription: User workflow.\n---\nBody",
            encoding="utf-8",
        )
        skills = {s.name: s for s in list_available_skills(self.repo)}
        self.assertTrue(skills["user-only-skill"].user_invoked)
        self.assertFalse(skills["test-skill-1"].user_invoked)

    def test_install_single_skill_link_mode(self) -> None:
        target_dir = self.ws / ".agents" / "skills"
        install_single_skill(self.skills_dir / "test-skill-1", target_dir, link=True)
        installed_md = target_dir / "test-skill-1" / "SKILL.md"
        self.assertTrue(installed_md.is_file())
        removed = remove_single_skill("test-skill-1", target_dir)
        self.assertTrue(removed)
        self.assertFalse(installed_md.exists())

    def test_sync_skills_with_config(self) -> None:
        cfg = AiToolsConfig(
            skill_targets=["claude", "cursor"],
            enabled_skills=["test-skill-1"],
            disabled_skills=["test-skill-2"],
        )
        res = sync_skills(self.repo, self.home, self.ws, cfg, scope="workspace")
        self.assertGreater(res["installed"], 0)

        claude_skill1 = self.ws / ".claude" / "skills" / "test-skill-1" / "SKILL.md"
        claude_skill2 = self.ws / ".claude" / "skills" / "test-skill-2" / "SKILL.md"
        self.assertTrue(claude_skill1.is_file())
        self.assertFalse(claude_skill2.exists())

    def test_get_skill_status(self) -> None:
        target_dir = self.home / ".claude" / "skills"
        install_single_skill(self.skills_dir / "test-skill-1", target_dir)
        status = get_skill_status(self.repo, self.home, ws=self.ws, tools=["claude"], scope="global")
        self.assertTrue(status["test-skill-1"]["claude"])
        self.assertFalse(status["test-skill-2"]["claude"])

    def test_toggle_skill_in_config(self) -> None:
        cfg_path = self.ws / ".aitools.toml"
        toggle_skill_in_config("test-skill-1", enable=False, config_path=cfg_path)
        self.assertTrue(cfg_path.is_file())
        content = cfg_path.read_text(encoding="utf-8")
        self.assertIn("test-skill-1", content)


if __name__ == "__main__":
    unittest.main()
