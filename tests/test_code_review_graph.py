"""Unit tests for code_review_graph.py."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from scripts.code_review_graph import (
    analyze_blast_radius,
    build_code_graph,
    calculate_risk,
    find_repo_root,
    parse_file_symbols,
    save_graph_sqlite,
)


class TestCodeReviewGraph(unittest.TestCase):

    def test_parse_file_symbols(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as temp_file:
            temp_file.write("import os\nfrom math import sqrt\ndef compute():\n    return sqrt(4)\n")
            tmp_path = Path(temp_file.name)

        try:
            defs, imps, calls = parse_file_symbols(tmp_path)
            self.assertIn("compute", defs)
            self.assertIn("os", imps)
            self.assertIn("sqrt", calls)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_calculate_risk(self) -> None:
        self.assertEqual(calculate_risk(1, True), "Low")
        self.assertEqual(calculate_risk(4, True), "Medium")
        self.assertEqual(calculate_risk(10, True), "High")
        self.assertEqual(calculate_risk(1, False), "High")

    def test_transitive_bfs_generic_filtering_and_sqlite(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
            scripts_dir = root / "scripts"
            tests_dir = root / "tests"
            scripts_dir.mkdir()
            tests_dir.mkdir()

            helper = scripts_dir / "helper.py"
            helper.write_text("def compute_delta() -> int:\n    return 42\n\ndef main() -> None:\n    pass\n", encoding="utf-8")

            mid = scripts_dir / "mid.py"
            mid.write_text("import helper\ndef bridge() -> int:\n    return helper.compute_delta()\n", encoding="utf-8")

            app = scripts_dir / "app.py"
            app.write_text("import mid\ndef run_flow() -> int:\n    return mid.bridge()\n", encoding="utf-8")

            unrelated = scripts_dir / "unrelated.py"
            unrelated.write_text("def main() -> None:\n    pass\n\ndef caller() -> None:\n    main()\n", encoding="utf-8")

            test_app = tests_dir / "test_app.py"
            test_app.write_text("import app\ndef test_flow() -> None:\n    app.run_flow()\n", encoding="utf-8")

            self.assertEqual(find_repo_root(helper), root.resolve())
            res = analyze_blast_radius(root, helper)
            self.assertIn("scripts/mid.py", res["direct_dependents"])
            self.assertIn("scripts/app.py", res["transitive_dependents"])
            self.assertIn("tests/test_app.py", res["affectedTests"])
            self.assertNotIn("scripts/unrelated.py", res["direct_dependents"])

            db_path = root / ".ai_code_graph.sqlite"
            save_graph_sqlite(build_code_graph(root), db_path)
            self.assertTrue(db_path.is_file())


if __name__ == "__main__":
    unittest.main()
