"""Unit tests for the behavior layer, skills, memory protocol, and sync."""
from __future__ import annotations

import io
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
        """Ensure the six canonical instruction files exist and contain behavior sections."""
        root_files = [
            REPO_ROOT / "AGENTS.md",
            REPO_ROOT / "CLAUDE.md",
            REPO_ROOT / ".cursorrules",
            REPO_ROOT / ".clinerules",
            REPO_ROOT / ".windsurfrules",
            REPO_ROOT / ".aider.conventions.md",
        ]
        required_headers = [
            "# Proactive Quality",
            "# Testing Standard",
            "# UI/UX Standard",
            "# Interaction",
            "# Memory",
            "# Cloud Agents",
        ]

        for target in root_files:
            self.assertTrue(target.is_file(), f"Missing rule file: {target}")
            content = target.read_text(encoding="utf-8")
            for header in required_headers:
                self.assertIn(header, content, f"Missing section '{header}' in {target.name}")

    def test_agents_md_line_limit(self) -> None:
        """Verify generated AGENTS.md remains at about 120 lines or fewer."""
        agents_path = REPO_ROOT / "AGENTS.md"
        lines = agents_path.read_text(encoding="utf-8").splitlines()
        self.assertLessEqual(len(lines), 120, f"AGENTS.md has {len(lines)} lines; exceeds 120 line limit")

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


if __name__ == "__main__":
    unittest.main()
