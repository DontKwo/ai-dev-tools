"""Unit tests for token_compressor.py."""

from __future__ import annotations

import io
import sys
import unittest
from unittest.mock import patch

from scripts.token_compressor import (
    compress_command_output,
    compress_compiler_warnings,
    compress_git_status,
    compress_test_output,
    main as compressor_main,
)


class TestTokenCompressor(unittest.TestCase):

    def test_compress_git_status_verbose_and_short(self) -> None:
        raw_status = (
            "On branch main\n"
            "Changes not staged for commit:\n"
            "\tmodified:   app.py\n"
            "\tmodified:   config.json\n"
            "Untracked files:\n"
            "\tLICENSE\n"
        )
        res = compress_git_status(raw_status)
        self.assertIn("Branch: main", res)
        self.assertIn("app.py", res)
        self.assertIn("LICENSE", res)

        short_res = compress_git_status("## main...origin/main\n M src/ui.py\n?? README.md\n")
        self.assertIn("Branch: main", short_res)
        self.assertIn("src/ui.py", short_res)
        self.assertIn("README.md", short_res)

    def test_compress_test_output_pass_and_ansi_strip(self) -> None:
        raw_output = (
            "\x1b[32m............................................\x1b[0m\n"
            "----------------------------------------------------------------------\n"
            "Ran 44 tests in 0.814s\n\nOK\n"
        )
        res = compress_test_output(raw_output)
        self.assertIn("[PASS]", res)
        self.assertIn("Ran 44 tests in 0.814s", res)
        self.assertNotIn("\x1b[32m", res)

    def test_compress_test_output_failure(self) -> None:
        raw_output = (
            "....F....\n"
            "FAIL: test_something (tests.test_app)\n"
            "Traceback (most recent call last):\n"
            "  File 'test.py', line 10, in test_something\n"
            "    self.assertEqual(1, 2)\n"
            "AssertionError: 1 != 2\n"
            "FAILED (failures=1)\n"
        )
        res = compress_test_output(raw_output)
        self.assertIn("FAIL: test_something", res)
        self.assertIn("AssertionError", res)

    def test_compress_compiler_warnings_dedupes(self) -> None:
        raw_warnings = (
            "src/a.rs:10:5: warning: unused variable `x`\n"
            "src/b.rs:24:9: warning: unused variable `x`\n"
            "src/c.rs:3:1: warning: unused variable `x`\n"
        )
        res = compress_compiler_warnings(raw_warnings)
        self.assertIn("(x3)", res)

    def test_compress_command_output_savings_and_run_cli(self) -> None:
        long_pass = ".\n" * 200 + "Ran 200 tests in 2.0s\nOK\n"
        compressed, savings = compress_command_output("pytest", long_pass)
        self.assertIn("[PASS]", compressed)
        self.assertGreater(savings, 0.5)

        out_buf = io.StringIO()
        with patch.object(sys, "stdout", out_buf):
            code = compressor_main(["--run", "--", sys.executable, "-c", "print('ok\\nok')"])
        self.assertEqual(code, 0)
        self.assertIn("RTK-Filter", out_buf.getvalue())


if __name__ == "__main__":
    unittest.main()
