"""Unit tests for code_review_graph.py."""

import tempfile
import unittest
from pathlib import Path
from scripts.code_review_graph import (
    analyze_blast_radius,
    build_code_graph,
    calculate_risk,
    parse_file_symbols,
)


class TestCodeReviewGraph(unittest.TestCase):

    def test_parse_file_symbols(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as temp_file:
            temp_file.write("import os\nfrom math import sqrt\ndef compute():\n    return sqrt(4)\n")
            tmp_path = Path(temp_file.name)

        try:
            defs, imps, cls = parse_file_symbols(tmp_path)
            self.assertIn("compute", defs)
            self.assertIn("os", imps)
            self.assertIn("sqrt", cls)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_calculate_risk(self) -> None:
        self.assertEqual(calculate_risk(1, True), "Low")
        self.assertEqual(calculate_risk(4, True), "Medium")
        self.assertEqual(calculate_risk(10, True), "High")
        self.assertEqual(calculate_risk(1, False), "High")

    def test_blast_radius_analysis(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            helper = root / "helper.py"
            helper.write_text("def assist() -> int:\n    return 42\n", encoding="utf-8")

            app = root / "app.py"
            app.write_text("import helper\ndef run() -> None:\n    helper.assist()\n", encoding="utf-8")

            test_file = root / "test_app.py"
            test_file.write_text("import app\ndef test_run():\n    pass\n", encoding="utf-8")

            res = analyze_blast_radius(root, helper)
            self.assertIn("app.py", res["direct_dependents"])
            self.assertIn("test_app.py", res["affectedTests"])


if __name__ == "__main__":
    unittest.main()
