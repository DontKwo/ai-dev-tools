"""Unit tests for context_mode.py (sandboxed exec, FTS5 search, and compaction continuity)."""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

from scripts.context_mode import (
    build_continuity_summary,
    ctx_execute,
    index_workspace,
    record_session_event,
    search_index,
)


class TestContextMode(unittest.TestCase):

    def test_ctx_execute_bounds_and_compresses(self) -> None:
        script = "for idx in range(120): print(f'row_{idx}_unique')"
        result = ctx_execute([sys.executable, "-c", script], max_lines=16)
        self.assertEqual(result["exit_code"], 0)
        self.assertIn("omitted by ctx_execute", result["summary"])

    def test_fts5_index_and_bm25_search(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "aerospace.py").write_text(
                "def nozzle_expansion_ratio(pressure_bar: float) -> float:\n    return pressure_bar * 2.5\n",
                encoding="utf-8",
            )
            (root / "README.md").write_text("# Demo Guide\nUse nozzle_expansion_ratio for engine sizing.\n", encoding="utf-8")
            db_path = root / "test_ctx.sqlite"
            stats = index_workspace(root, db_path=db_path)
            self.assertEqual(stats["indexed"], 2)

            second = index_workspace(root, db_path=db_path)
            self.assertEqual(second["indexed"], 0)
            self.assertEqual(second["unchanged"], 2)

            hits = search_index("nozzle_expansion_ratio", root, db_path=db_path)
            self.assertGreaterEqual(len(hits), 1)
            punct_hits = search_index("nozzle-expansion!?", root, db_path=db_path)
            self.assertIsInstance(punct_hits, list)

    def test_session_continuity_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            db_path = root / "test_ctx.sqlite"
            record_session_event(root, "edit", "Refactored token compressor", files=["scripts/token_compressor.py"], db_path=db_path)
            summary = build_continuity_summary(root, db_path=db_path)
            self.assertIn("Refactored token compressor", summary)
            self.assertIn("scripts/token_compressor.py", summary)


if __name__ == "__main__":
    unittest.main()
