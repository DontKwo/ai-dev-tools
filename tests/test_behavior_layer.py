"""Unit tests for the behavior layer, skills, memory protocol, and sync."""
from __future__ import annotations

import io
import json
import re
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent

# Append scripts directory for module imports
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import grill_user
from secret_sanitizer import scan_file


class TestBehaviorLayer(unittest.TestCase):
    """Validates behavior layer sections, root instruction sync, skills, and memory."""

    def test_six_root_rule_files_exist_and_match(self) -> None:
        """Ensure canonical instruction template exists and contains all behavior sections."""
        template_target = REPO_ROOT / "templates" / "INSTRUCTIONS_TEMPLATE.md"
        self.assertTrue(template_target.is_file(), f"Missing canonical rule template: {template_target}")
        template_content = template_target.read_text(encoding="utf-8")

        required_headers = [
            "# Proactive Quality",
            "# Testing Standard",
            "# UI/UX Standard",
            "# Interaction",
            "# Memory",
            "# Cloud Agents",
        ]

        for header in required_headers:
            self.assertIn(header, template_content, f"Missing section '{header}' in template")

        from configure import build_instructions, get_tool_definitions
        tool_defs = get_tool_definitions(REPO_ROOT)
        for tool_key in ["claude", "cursor", "cline", "antigravity", "windsurf", "aider"]:
            definition = tool_defs[tool_key]
            generated = build_instructions(frontmatter=definition.get("frontmatter", ""), workspace=REPO_ROOT)
            for header in required_headers:
                self.assertIn(header, generated, f"Generated rules for '{tool_key}' missing section '{header}'")

    def test_agents_md_line_limit(self) -> None:
        """Verify canonical instructions template remains at about 120 lines or fewer."""
        template_path = REPO_ROOT / "templates" / "INSTRUCTIONS_TEMPLATE.md"
        lines = template_path.read_text(encoding="utf-8").splitlines()
        self.assertLessEqual(len(lines), 120, f"Template has {len(lines)} lines; exceeds 120 line limit")

    def test_skills_frontmatter_and_naming(self) -> None:
        """Verify every skill has valid YAML frontmatter and its name matches its directory."""
        skills_dir = REPO_ROOT / "skills"
        skill_subdirs = [p for p in skills_dir.iterdir() if p.is_dir()]
        self.assertGreaterEqual(len(skill_subdirs), 16)

        for sdir in skill_subdirs:
            skill_md = sdir / "SKILL.md"
            self.assertTrue(skill_md.is_file(), f"Missing SKILL.md in {sdir.name}")
            content = skill_md.read_text(encoding="utf-8")
            self.assertTrue(content.startswith("---\n"), f"{sdir.name}/SKILL.md missing frontmatter start")

            match = re.search(r"^name:\s*([a-zA-Z0-9_-]+)", content, re.MULTILINE)
            self.assertIsNotNone(match, f"{sdir.name}/SKILL.md missing 'name' in frontmatter")
            declared_name = match.group(1).strip() if match else ""
            self.assertEqual(declared_name, sdir.name, f"Skill directory {sdir.name} != declared {declared_name}")

    def test_memory_format_and_security(self) -> None:
        """Verify memory files adhere to schema, have no secrets, and include seeded dates."""
        memory_dir = REPO_ROOT / "memory"
        self.assertTrue((memory_dir / "README.md").is_file())

        seeded_files = [
            memory_dir / "preferences.md",
            memory_dir / "user-profile.md",
            memory_dir / "projects" / "ai-dev-tools.md",
            memory_dir / "projects" / "math-flashcards.md",
        ]

        all_memory_files = [
            memory_dir / "preferences.md",
            memory_dir / "user-profile.md",
            memory_dir / "lessons-learned.md",
            memory_dir / "decisions.md",
            memory_dir / "projects" / "ai-dev-tools.md",
            memory_dir / "projects" / "math-flashcards.md",
        ]

        entry_pattern = re.compile(r"^- \d{4}-\d{2}-\d{2}: .+$")

        for target in all_memory_files:
            self.assertTrue(target.is_file(), f"Missing expected memory file: {target}")
            lines = target.read_text(encoding="utf-8").splitlines()
            entries = [ln.strip() for ln in lines if ln.strip().startswith("- ")]
            if target in seeded_files:
                self.assertGreater(len(entries), 0, f"No entries found in {target.name}")

            for entry in entries:
                self.assertIsNotNone(
                    entry_pattern.match(entry),
                    f"Entry '{entry}' in {target.name} does not match required format '- YYYY-MM-DD: text'",
                )

            findings = scan_file(target)
            self.assertEqual(len(findings), 0, f"Found secrets in {target.name}: {findings}")

    def test_skills_registration(self) -> None:
        """Verify that every skill in skills/ is discovered and listed by doctor."""
        from doctor import check_installed_skills
        skills_status = check_installed_skills(REPO_ROOT, Path("/nonexistent/home"))
        skills_dir = REPO_ROOT / "skills"
        expected_skills = {p.name for p in skills_dir.iterdir() if p.is_dir()}
        self.assertEqual(set(skills_status.keys()), expected_skills)

    @patch("sys.argv", ["grill_user.py", "--async", "Redesign Architecture"])
    @patch("sys.stdout", new_callable=io.StringIO)
    def test_grill_user_async_output(self, mock_stdout: io.StringIO) -> None:
        """Verify grill_user --async outputs questions, options, and recommended defaults."""
        exit_code = grill_user.main()
        output = mock_stdout.getvalue()

        self.assertEqual(exit_code, 0)
        self.assertIn("### Grilling Questions & Defaults: Redesign Architecture", output)
        self.assertIn("Recommended Default:", output)
        self.assertIn("Recorded Assumptions", output)

    def test_plugin_manifest_matches_skills(self) -> None:
        """Verify .claude-plugin manifests match every skill directory cleanly."""
        plugin_path = REPO_ROOT / ".claude-plugin" / "plugin.json"
        marketplace_path = REPO_ROOT / ".claude-plugin" / "marketplace.json"
        self.assertTrue(plugin_path.is_file(), "Missing .claude-plugin/plugin.json")
        self.assertTrue(marketplace_path.is_file(), "Missing .claude-plugin/marketplace.json")

        plugin_data = json.loads(plugin_path.read_text(encoding="utf-8"))
        marketplace_data = json.loads(marketplace_path.read_text(encoding="utf-8"))
        self.assertEqual(plugin_data.get("name"), "ai-dev-tools")
        self.assertGreaterEqual(len(marketplace_data.get("plugins", [])), 1)

        skills_dir = REPO_ROOT / "skills"
        self.assertFalse((skills_dir / "jules-orchestrator").exists())  # noqa: 91
        expected = sorted(f"./skills/{p.name}" for p in skills_dir.iterdir() if p.is_dir())
        self.assertEqual(sorted(plugin_data.get("skills", [])), expected)

    def test_skills_openai_yaml_and_invocation_parity(self) -> None:
        """Verify every skill defines agents/openai.yaml matching its invocation mode."""
        skills_dir = REPO_ROOT / "skills"
        for sdir in skills_dir.iterdir():
            if not sdir.is_dir():
                continue
            skill_md = sdir / "SKILL.md"
            openai_yaml = sdir / "agents" / "openai.yaml"
            self.assertTrue(openai_yaml.is_file(), f"Missing agents/openai.yaml in {sdir.name}")

            skill_text = skill_md.read_text(encoding="utf-8")
            yaml_text = openai_yaml.read_text(encoding="utf-8")
            self.assertIn("display_name:", yaml_text)
            self.assertIn("short_description:", yaml_text)

            is_user_only = "disable-model-invocation: true" in skill_text
            if is_user_only:
                self.assertIn("allow_implicit_invocation: false", yaml_text, f"{sdir.name} openai.yaml out of sync")
            else:
                self.assertNotIn("allow_implicit_invocation: false", yaml_text, f"{sdir.name} openai.yaml out of sync")


if __name__ == "__main__":
    unittest.main()
