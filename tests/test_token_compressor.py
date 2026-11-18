"""Unit tests for token_compressor.py."""

import unittest
from scripts.token_compressor import (
    compress_command_output,
    compress_git_status,
    compress_test_output,
)


class TestTokenCompressor(unittest.TestCase):

    def test_compress_git_status(self) -> None:
        raw_status = (
            "On branch main\n"
            "Changes not staged for commit:\n"
            "  (use \"git add <file>...\" to update what will be committed)\n"
            "\tmodified:   app.py\n"
            "\tmodified:   config.json\n\n"
            "Untracked files:\n"
            "  (use \"git add <file>...\" to include in what will be committed)\n"
            "\tnew_feature.py\n"
        )
        res = compress_git_status(raw_status)
        self.assertIn("Branch: main", res)
        self.assertIn("app.py", res)
        self.assertIn("new_feature.py", res)

    def test_compress_test_output_pass(self) -> None:
        raw_output = (
            "............................................\n"
            "----------------------------------------------------------------------\n"
            "Ran 44 tests in 0.814s\n\n"
            "OK\n"
        )
        res = compress_test_output(raw_output)
        self.assertIn("[PASS]", res)
        self.assertIn("Ran 44 tests in 0.814s", res)

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

    def test_compress_command_output_savings(self) -> None:
        long_pass = ".\n" * 200 + "Ran 200 tests in 2.0s\nOK\n"
        compressed, savings = compress_command_output("pytest", long_pass)
        self.assertIn("[PASS]", compressed)
        self.assertGreater(savings, 0.5)


if __name__ == "__main__":
    unittest.main()
