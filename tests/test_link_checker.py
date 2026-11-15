import tempfile
import unittest
from pathlib import Path

from scripts.link_checker import (
    slugify_heading,
    extract_markdown_anchors,
    find_workflow_artifact_names,
    validate_markdown_file,
    run_link_check,
)


class TestLinkChecker(unittest.TestCase):
    def test_slugify_heading(self) -> None:
        self.assertEqual(slugify_heading("Quick Start Guide!"), "quick-start-guide")
        self.assertEqual(slugify_heading("Installation & Setup"), "installation-setup")

    def test_extract_anchors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            doc_file = Path(tmp_dir) / "doc.md"
            doc_file.write_text("# Overview\n\n## Getting Started\n", encoding="utf-8")
            anchors = extract_markdown_anchors(doc_file)
            self.assertIn("overview", anchors)
            self.assertIn("getting-started", anchors)

    def test_valid_and_broken_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_dir_path = Path(tmp_dir)
            target = temp_dir_path / "target.md"
            target.write_text("# Target Section\n", encoding="utf-8")

            source = temp_dir_path / "source.md"
            source.write_text("[Good](target.md#target-section)\n[Bad](nonexistent.md)\n", encoding="utf-8")

            errors = validate_markdown_file(source, temp_dir_path)
            self.assertEqual(len(errors), 1)
            self.assertIn("nonexistent.md", errors[0])

    def test_release_artifact_matching(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_dir_path = Path(tmp_dir)
            wf_dir = temp_dir_path / ".github" / "workflows"
            wf_dir.mkdir(parents=True)
            (wf_dir / "release.yml").write_text("build/App-Windows.zip\n", encoding="utf-8")

            source = temp_dir_path / "README.md"
            source.write_text(
                "[Windows](https://github.com/user/repo/releases/latest/download/App-Windows.zip)\n"
                "[Android](https://github.com/user/repo/releases/latest/download/Phantom-App.apk)\n",
                encoding="utf-8"
            )

            errors = validate_markdown_file(source, temp_dir_path)
            self.assertEqual(len(errors), 1)
            self.assertIn("Phantom-App.apk", errors[0])

    def test_ignores_links_inside_fenced_code_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_dir_path = Path(tmp_dir)
            source = temp_dir_path / "doc.md"
            source.write_text(
                "# Example\n\n```md\n[Example template](missing-example.md)\n```\n",
                encoding="utf-8",
            )
            errors = validate_markdown_file(source, temp_dir_path)
            self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
