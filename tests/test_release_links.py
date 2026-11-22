"""Tests verifying release download links and CI/CD artifact parity."""
from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestReleaseLinks(unittest.TestCase):
    """Ensures README and unified CI workflow contain matching release artifacts."""

    def test_readme_contains_all_platform_downloads(self) -> None:
        readme_path = REPO_ROOT / "README.md"
        self.assertTrue(readme_path.is_file(), "README.md must exist")
        content = readme_path.read_text(encoding="utf-8")

        expected_artifacts = [
            "adt-setup-Windows.exe",
            "adt-setup-macOS.zip",
            "adt-setup-Linux.tar.gz",
        ]
        for artifact in expected_artifacts:
            expected_url = f"https://github.com/DontKwo/ai-dev-tools/releases/latest/download/{artifact}"
            self.assertIn(
                expected_url,
                content,
                f"README.md is missing expected release download URL: {expected_url}",
            )

    def test_workflow_defines_all_release_artifacts(self) -> None:
        workflow_path = REPO_ROOT / ".github" / "workflows" / "ci.yml"
        self.assertTrue(workflow_path.is_file(), "ci.yml must exist")
        wf_content = workflow_path.read_text(encoding="utf-8")

        self.assertIn("adt-setup-Windows.exe", wf_content)
        self.assertIn("adt-setup-macOS.zip", wf_content)
        self.assertIn("adt-setup-Linux.tar.gz", wf_content)
        self.assertIn("--self-test", wf_content)
        self.assertIn("prerelease: false", wf_content)
        self.assertIn("make_latest: true", wf_content)


if __name__ == "__main__":
    unittest.main()
