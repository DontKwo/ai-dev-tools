"""Unit test suite for claudemd_linter, lint_fixer, repo_map, and clean_encoding."""
import tempfile
import unittest
from pathlib import Path

from scripts.claudemd_linter import scan_file, noqa_codes, suppressed, parse_cli_args, LEVEL_RULES
from scripts.lint_fixer import fix_line, condense_docstrings
from scripts.repo_map import generate_map
from scripts.clean_encoding import clean_content
from scripts.prune_dead_code import find_unused_imports, prune_unused_imports_in_file
from scripts.boost_types import boost_file
from scripts.check_dependencies import scan_dependencies
from scripts.to_markdown import convert_file_to_markdown
from scripts.redact_diff import redact_diff_content
from scripts.rollback import save_checkpoint, restore_checkpoint, list_checkpoints


class TestClaudemdLinter(unittest.TestCase):

    def _scan_snippet(self, code_str: str, suffix: str = ".py") -> list[int]:
        with tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False, encoding="utf-8") as temp_file:
            temp_file.write(code_str)
            tmp_path = Path(temp_file.name)

        violations = []
        try:
            scan_file(tmp_path, violations)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

        return [v[2] for v in violations]

    def test_rule_1_em_dash(self) -> None:
        codes = self._scan_snippet("x = 10 — y = 20\n")
        self.assertIn(1, codes)

    def test_rule_2_unicode(self) -> None:
        codes = self._scan_snippet("text = ‘curly quote’\n")
        self.assertIn(2, codes)

    def test_rule_3_emoji(self) -> None:
        codes = self._scan_snippet("print('hello 🚀')\n")
        self.assertIn(3, codes)

    def test_rule_4_ai_phrases(self) -> None:
        codes1 = self._scan_snippet("# Let's delve into this function\n")
        self.assertIn(4, codes1)

        codes2 = self._scan_snippet("# This stands as a testament to the architecture\n")
        self.assertIn(4, codes2)

        codes3 = self._scan_snippet("# It marks a pivotal moment in the codebase\n")
        self.assertIn(4, codes3)

    def test_rule_5_negative_parallelism(self) -> None:
        codes = self._scan_snippet("# It is not just fast, but it is reliable\n")
        self.assertIn(5, codes)

    def test_rule_9_bare_except(self) -> None:
        code = "try:\n    x = 1\nexcept:\n    pass\n"
        codes = self._scan_snippet(code)
        self.assertIn(9, codes)

    def test_rule_10_bare_pass(self) -> None:
        code = "def stub_func() -> None:\n    pass\n"
        codes = self._scan_snippet(code)
        self.assertIn(10, codes)

    def test_rule_11_missing_type_hints(self) -> None:
        code = "def add(a, b):\n    return a + b\n"
        codes = self._scan_snippet(code)
        self.assertIn(11, codes)

    def test_rule_14_mutable_default(self) -> None:
        code = "def append_val(val: int, target: list = []) -> list:\n    target.append(val)\n    return target\n"
        codes = self._scan_snippet(code)
        self.assertIn(14, codes)

    def test_rule_15_equality_none(self) -> None:
        code = "def check(x: int | None) -> bool:\n    return x == None\n"
        codes = self._scan_snippet(code)
        self.assertIn(15, codes)

    def test_rule_16_string_formatting(self) -> None:
        code = "def fmt(name: str) -> str:\n    return 'Hello %s' % name\n"
        codes = self._scan_snippet(code)
        self.assertIn(16, codes)

    def test_rule_17_comment_blocks(self) -> None:
        code = "# Line 1\n# Line 2\n# Line 3\nx = 1\n"
        codes = self._scan_snippet(code)
        self.assertIn(17, codes)

    def test_rule_17_comment_block_exemption(self) -> None:
        code = "# long-comment-ok\n# Line 1\n# Line 2\n# Line 3\nx = 1\n"
        codes = self._scan_snippet(code)
        self.assertNotIn(17, codes)

    def test_rule_24_todos(self) -> None:
        for keyword in ("TODO", "FIXME", "HACK", "XXX"):
            with self.subTest(keyword=keyword):
                codes = self._scan_snippet(f"# {keyword}: mock comment\nx = 1\n")
                self.assertIn(24, codes)

    def test_rule_25_print_statement(self) -> None:
        codes = self._scan_snippet("def run() -> None:\n    print('debug')\n")
        self.assertIn(25, codes)

    def test_noqa_codes_parsing(self) -> None:
        self.assertIsNone(noqa_codes(""))
        self.assertIsNone(noqa_codes("some random text"))
        self.assertEqual(noqa_codes("# noqa"), "ALL")
        self.assertEqual(noqa_codes("# noqa: 25"), {25})
        self.assertEqual(noqa_codes("# noqa: 25, 30"), {25, 30})
        self.assertEqual(noqa_codes("// noqa: 10, 11"), {10, 11})
        self.assertEqual(noqa_codes("<!-- noqa: 41 -->"), {41})
        self.assertEqual(noqa_codes("# noqa: abc"), set())
        self.assertEqual(noqa_codes("#  noqa :  1  , 2 "), "ALL")
        self.assertEqual(noqa_codes("# NOQA: 10, 20"), {10, 20})
        self.assertEqual(noqa_codes("<!--noqa:41-->"), {41})

    def test_noqa_suppression(self) -> None:
        # Line with print and noqa: 25
        codes = self._scan_snippet("def run() -> None:\n    print('debug')  # noqa: 25\n")
        self.assertNotIn(25, codes)

        # Line with generic noqa
        codes_all = self._scan_snippet("def run() -> None:\n    print('debug')  # noqa\n")
        self.assertNotIn(25, codes_all)

    def test_rule_38_variable_naming(self) -> None:
        bad_code = "def process_data(items: list[int]) -> int:\n    temp = 10\n    return temp\n"
        codes_bad = self._scan_snippet(bad_code)
        self.assertIn(38, codes_bad)

        good_code = "def process_data(items: list[int]) -> int:\n    total_count = 10\n    return total_count\n"
        codes_good = self._scan_snippet(good_code)
        self.assertNotIn(38, codes_good)

    def test_rule_39_collapsed_equation(self) -> None:
        bad_code = "def calc_result(a: float, b: float, x: float, d: float, e: float) -> float:\n    return a + b * x / d - e\n"
        codes_bad = self._scan_snippet(bad_code)
        self.assertIn(39, codes_bad)

        good_code = "def calc_result(a: float, b: float, x: float) -> float:\n    term = b * x\n    return a + term\n"
        codes_good = self._scan_snippet(good_code)
        self.assertNotIn(39, codes_good)

    def test_rule_40_docstring_bloat(self) -> None:
        bloated = 'def add(a: int, b: int) -> int:\n    """Add two numbers.\n\n    Args:\n        a: First.\n        b: Second.\n\n    Returns:\n        Sum.\n    """\n    return a + b\n'
        codes = self._scan_snippet(bloated)
        self.assertIn(40, codes)

    def test_rule_41_divider_banners(self) -> None:
        code = "########################################\nx = 1\n"
        codes = self._scan_snippet(code)
        self.assertIn(41, codes)

    def test_rule_42_loop_micro_optimization(self) -> None:
        code = "res = [y for x in range(10) if (y := x * 2) > 5]\n"
        codes = self._scan_snippet(code)
        self.assertIn(42, codes)

    def test_rule_43_duplicate_dict_keys(self) -> None:
        bad_code = "d = {'a': 1, 'b': 2, 'a': 3, 1: 4, 1: 5}\n"
        codes_bad = self._scan_snippet(bad_code)
        self.assertIn(43, codes_bad)

        good_code = "d = {'a': 1, 'b': 2, 1: 3, 2: 4}\n"
        codes_good = self._scan_snippet(good_code)
        self.assertNotIn(43, codes_good)

    def test_rule_44_artificial_equation_line_break(self) -> None:
        bad_code = "total = (\n    a + b\n    + c\n)\n"
        codes_bad = self._scan_snippet(bad_code)
        self.assertIn(44, codes_bad)

    def test_rule_45_overengineered_oop(self) -> None:
        code = "from abc import ABC\nclass BasePropulsion(ABC):\n    pass\ndef calc_thrust() -> float:\n    return 1.0\n"
        codes = self._scan_snippet(code)
        self.assertIn(45, codes)

    def test_rule_92_unsafe_eval(self) -> None:
        codes = self._scan_snippet("result = eval('2 + 2')\n")
        self.assertIn(92, codes)

    def test_rule_93_unsafe_yaml(self) -> None:
        codes = self._scan_snippet("import yaml\nyaml.load('key: val')\n")
        self.assertIn(93, codes)

    def test_rule_94_sql_injection(self) -> None:
        codes = self._scan_snippet("cursor.execute(f'SELECT * FROM users WHERE id = {uid}')\n")
        self.assertIn(94, codes)

    def test_rule_95_secret_credential(self) -> None:
        codes = self._scan_snippet("token = 'ghp_123456789012345678901234567890123456'\n")
        self.assertIn(95, codes)

    def test_rule_96_tautological_assert(self) -> None:
        codes = self._scan_snippet("def run():\n    assert True\n")
        self.assertIn(96, codes)

    def test_rule_97_placeholder_token(self) -> None:
        codes = self._scan_snippet("key = 'your_api_key_here'\n")
        self.assertIn(97, codes)

    def test_rule_98_web_accessibility(self) -> None:
        codes = self._scan_snippet('<img src="avatar.png">\n', suffix=".jsx")
        self.assertIn(98, codes)

    def test_rule_99_ai_stub(self) -> None:
        codes = self._scan_snippet("# AI generated placeholder\n")
        self.assertIn(99, codes)

    def test_rule_100_hallucinated_import(self) -> None:
        codes = self._scan_snippet("from typing import String\n")
        self.assertIn(100, codes)

    def test_cli_levels_and_filters(self) -> None:
        target, level, skip, only, flags = parse_cli_args(["src", "--level", "standard", "--skip", "1,2", "--no-ruff"])
        self.assertEqual(target, "src")
        self.assertEqual(level, "standard")
        self.assertEqual(skip, {1, 2})
        self.assertTrue(flags["no_ruff"])

        target2, level2, skip2, only2, flags2 = parse_cli_args(["--only", "38,39"])
        self.assertEqual(level2, "strict")
        self.assertEqual(only2, {38, 39})


class TestLintFixer(unittest.TestCase):

    def test_auto_fixer_skips_em_dash(self) -> None:
        line = "Sentence with em dash — must not change.\n"
        fixed, changes = fix_line(line, 1, Path("test.py"), fix_emojis=True)
        self.assertIn("—", fixed)  # Must still contain em dash
        self.assertEqual(len(changes), 0)

    def test_auto_fixer_rule_15(self) -> None:
        line = "    if val == None or val != None:\n"
        fixed, changes = fix_line(line, 1, Path("test.py"), fix_emojis=False)
        self.assertEqual(fixed, "    if val is None or val is not None:\n")
        self.assertEqual(len(changes), 2)

    def test_auto_fixer_rule_2_unicode(self) -> None:
        line = "title = “smart quotes and ellipsis…”\n"
        fixed, changes = fix_line(line, 1, Path("test.py"), fix_emojis=False)
        self.assertEqual(fixed, 'title = "smart quotes and ellipsis..."\n')
        self.assertGreater(len(changes), 0)

    def test_auto_fixer_rule_41_banner(self) -> None:
        line = "########################################\n"
        fixed, changes = fix_line(line, 1, Path("test.py"), fix_emojis=False, fix_banners=True)
        self.assertEqual(fixed, "# ---\n")
        self.assertGreater(len(changes), 0)

    def test_auto_fixer_rule_40_docstring(self) -> None:
        content = 'def helper():\n    """Quick sum.\n\n    Args:\n        x: value\n    """\n    return x\n'
        cleaned, count = condense_docstrings(content)
        self.assertEqual(count, 1)
        self.assertNotIn("Args:", cleaned)


class TestCleanEncoding(unittest.TestCase):

    def test_mojibake_replacement(self) -> None:
        corrupted = "Itâ€™s a test with â€œquotesâ€\x9d and Â° symbols."
        cleaned, changes = clean_content(corrupted)
        self.assertIn("It's", cleaned)
        self.assertIn('"quotes"', cleaned)
        self.assertIn("°", cleaned)
        self.assertGreater(len(changes), 0)




class TestRepoMap(unittest.TestCase):

    def test_symbol_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            sample_file = Path(tmpdir) / "sample.py"
            sample_file.write_text("class MyService:\n    def execute(self, val: int) -> bool:\n        return True\n", encoding="utf-8")
            result = generate_map(Path(tmpdir))
            self.assertIn("class MyService", result)
            self.assertIn("def execute", result)


class TestPruneDeadCode(unittest.TestCase):

    def test_detect_and_prune_unused(self) -> None:
        code = "import os, sys\nfrom math import sqrt, sin\nprint(sqrt(4))\nprint(os.name)\n"
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as temp_file:
            temp_file.write(code)
            tmp_path = Path(temp_file.name)

        try:
            unused = find_unused_imports(tmp_path)
            unused_names = {unused_item.symbol for unused_item in unused}
            self.assertIn("sys", unused_names)
            self.assertIn("sin", unused_names)
            self.assertNotIn("os", unused_names)
            self.assertNotIn("sqrt", unused_names)

            count, changes = prune_unused_imports_in_file(tmp_path, dry_run=False)
            self.assertEqual(count, 2)
            content = tmp_path.read_text(encoding="utf-8")
            self.assertIn("import os\n", content)
            self.assertIn("from math import sqrt\n", content)
            self.assertNotIn("sys", content)
            self.assertNotIn("sin", content)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_preserve_noqa(self) -> None:
        code = "import unused_mod  # noqa\nx = 1\n"
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as temp_file:
            temp_file.write(code)
            tmp_path = Path(temp_file.name)

        try:
            unused = find_unused_imports(tmp_path)
            self.assertEqual(len(unused), 0)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()


class TestBoostTypes(unittest.TestCase):

    def test_infer_defaults_and_return(self) -> None:
        code = "def calculate(count=10, name='guest', is_admin=False):\n    return True\n"
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as temp_file:
            temp_file.write(code)
            tmp_path = Path(temp_file.name)

        try:
            count, items = boost_file(tmp_path, fix=True)
            self.assertEqual(count, 1)
            content = tmp_path.read_text(encoding="utf-8")
            self.assertIn("def calculate(count: int = 10, name: str = 'guest', is_admin: bool = False) -> bool:", content)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_skip_self_and_infer_none(self) -> None:
        code = "class Worker:\n    def run(self):\n        print('running')\n"
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as temp_file:
            temp_file.write(code)
            tmp_path = Path(temp_file.name)

        try:
            count, items = boost_file(tmp_path, fix=True)
            self.assertEqual(count, 1)
            content = tmp_path.read_text(encoding="utf-8")
            self.assertIn("def run(self) -> None:", content)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()


class TestCheckDependencies(unittest.TestCase):

    def test_detect_hallucinated_package(self) -> None:
        code = "import nonexistent_phantom_package_12345\nimport json\n"
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as temp_file:
            temp_file.write(code)
            tmp_path = Path(temp_file.name)

        try:
            res = scan_dependencies(tmp_path)
            self.assertIn("nonexistent_phantom_package_12345", res["hallucinated"])
            self.assertNotIn("json", res["hallucinated"])
        finally:
            if tmp_path.exists():
                tmp_path.unlink()



class TestNewLinterRules(unittest.TestCase):

    def _scan_snippet(self, code_str: str, suffix: str = ".py") -> list[int]:
        with tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False, encoding="utf-8") as temp_file:
            temp_file.write(code_str)
            tmp_path = Path(temp_file.name)

        violations = []
        try:
            scan_file(tmp_path, violations)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

        return [v[2] for v in violations]

    def test_rule_36_ai_metadata(self) -> None:
        codes1 = self._scan_snippet("# Reference :contentReference[oaicite:0]{index=0}\n")
        self.assertIn(36, codes1)

        codes2 = self._scan_snippet("# Based on [cite: 1] and turn0search0\n")
        self.assertIn(36, codes2)

        codes3 = self._scan_snippet("# Link: https://en.wikipedia.org?utm_source=chatgpt.com\n")
        self.assertIn(36, codes3)

    def test_rule_37_conversational_fluff(self) -> None:
        codes = self._scan_snippet("# Certainly! Here is the updated implementation\n")
        self.assertIn(37, codes)


class TestToMarkdown(unittest.TestCase):

    def test_csv_conversion(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as temp_file:
            temp_file.write("name,role\nAlice,Lead\nBob,Dev\n")
            tmp_path = Path(temp_file.name)

        try:
            res = convert_file_to_markdown(tmp_path)
            self.assertIn("| name | role |", res)
            self.assertIn("| Alice | Lead |", res)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_html_conversion(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as temp_file:
            temp_file.write("<h2>Module Architecture</h2><p>Overview of components.</p>")
            tmp_path = Path(temp_file.name)

        try:
            res = convert_file_to_markdown(tmp_path)
            self.assertIn("## Module Architecture", res)
            self.assertIn("Overview of components", res)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()


class TestRedactDiff(unittest.TestCase):

    def test_redact_diff(self) -> None:
        sample_diff = (
            "diff --git a/app.py b/app.py\n"
            "index 1234..5678 100644\n"
            "--- a/app.py\n"
            "+++ b/app.py\n"
            "@@ -10,4 +10,4 @@ def calculate():\n"
            "     x = 1\n"
            "-    return x + 1\n"
            "+    return x + 2\n"
        )
        redacted, orig_lines, new_lines = redact_diff_content(sample_diff)
        self.assertIn("File: `app.py`", redacted)
        self.assertIn("Scope: `def calculate():`", redacted)
        self.assertIn("+    return x + 2", redacted)


class TestRollback(unittest.TestCase):

    def test_checkpoint_save_and_restore(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = Path(tmpdir)
            f = ws / "data.txt"
            f.write_text("version 1", encoding="utf-8")

            # Save checkpoint
            cp_name = save_checkpoint(ws, "v1")
            cps = list_checkpoints(ws)
            self.assertEqual(len(cps), 1)

            # Modify file
            f.write_text("version 2 (corrupted by AI)", encoding="utf-8")
            self.assertEqual(f.read_text(encoding="utf-8"), "version 2 (corrupted by AI)")

            # Restore checkpoint
            success = restore_checkpoint(ws, cp_name)
            self.assertTrue(success)
            self.assertEqual(f.read_text(encoding="utf-8"), "version 1")


class TestRepoStandardsRules(unittest.TestCase):
    """Validates Rules 101-112 for unified repository structure, docs, icons, and CI."""

    def test_rules_101_to_112_detection_and_clean_repo(self) -> None:
        from scripts.repo_standards_rules import detect_repo_standard_issues

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".git").mkdir()
            (root / "PLAN.md").write_text("# scratch\n", encoding="utf-8")
            (root / "README.md").write_text(
                "# Demo\n\nCheck SHA256SUMS.txt and see `docs/USER_GUIDE.md`.\n",
                encoding="utf-8",
            )
            violations: list[tuple[Path, int, int]] = []
            all_codes = set(range(101, 113))
            detect_repo_standard_issues(root, [], all_codes, lambda _p, _ln, _c: False, violations)
            found = {code for _, _, code in violations}
            self.assertTrue({101, 102, 103, 104, 107}.issubset(found))

            # Build compliant repo and verify 0 violations
            (root / "PLAN.md").unlink()
            (root / "docs").mkdir(exist_ok=True)
            (root / "assets" / "screenshots").mkdir(parents=True, exist_ok=True)
            (root / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
            (root / "assets" / "logo.png").write_bytes(b"LOGO_BYTES")
            (root / "assets" / "icon.png").write_bytes(b"ICON_BYTES")
            (root / "assets" / "icon.ico").write_bytes(b"ICO_BYTES")
            (root / "assets" / "screenshots" / "01_main.png").write_bytes(b"SHOT")
            (root / "LICENSE").write_text("MIT License\n\nCopyright (c) 2026 DontKwo\n", encoding="utf-8")
            (root / "SECURITY.md").write_text("# Security\n\nOnly `main` releases; do not download forked builds.\n", encoding="utf-8")
            (root / "THIRD_PARTY_NOTICES.md").write_text("# Notices\n", encoding="utf-8")
            (root / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
            for doc_name in ("USER_GUIDE.md", "DEVELOPMENT.md", "INSTALLATION.md"):
                (root / "docs" / doc_name).write_text(
                    f"# {doc_name}\n\n## Windows\nwin\n\n## macOS\nmac\n\n## Linux\nlin\n\n"
                    "## Related Documentation\n- [Overview](../README.md)\n",
                    encoding="utf-8",
                )
            (root / ".github" / "workflows" / "ci.yml").write_text(
                "on:\n  push:\n    branches: [main]\n  pull_request:\n    branches: [main]\n"
                "steps:\n  - run: python claudemd_linter.py . && python link_checker.py . && ./app --self-test\n"
                "uses: softprops/action-gh-release@v2\nwith:\n  tag_name: ${{ steps.version.outputs.tag }}\n"
                "  prerelease: false\n  make_latest: true\n",
                encoding="utf-8",
            )
            (root / "README.md").write_text(
                '<p align="center"><img src="assets/logo.png" width="240" /></p>\n\n# Demo\n\n'
                "## Download\n\n"
                "| Platform | Download |\n| :--- | :--- |\n"
                "| Windows | [Demo-Windows.exe](https://github.com/DontKwo/demo/releases/latest/download/Demo-Windows.exe) |\n\n"
                "## Screenshots\n\n<img src=\"assets/screenshots/01_main.png\" />\n\n"
                "## Documentation\n\n"
                "### User Documentation\n- [User Guide](docs/USER_GUIDE.md)\n\n"
                "### Developer Documentation\n- [Developer Guide](docs/DEVELOPMENT.md)\n\n"
                "### Legal & Security Policies\n- [Security Policy](SECURITY.md)\n\n"
                "## Safety & Disclaimers\n\nOfficial `main` only.\n",
                encoding="utf-8",
            )
            clean_violations: list[tuple[Path, int, int]] = []
            detect_repo_standard_issues(root, [], all_codes, lambda _p, _ln, _c: False, clean_violations)
            self.assertEqual(clean_violations, [])

            # Safety placed before Documentation must trigger Rule 102
            (root / "README.md").write_text(
                '<p align="center"><img src="assets/logo.png" width="240" /></p>\n\n# Demo\n\n'
                "## Download\n\n"
                "| Platform | Download |\n| :--- | :--- |\n"
                "| Windows | [Demo-Windows.exe](https://github.com/DontKwo/demo/releases/latest/download/Demo-Windows.exe) |\n\n"
                "## Screenshots\n\n<img src=\"assets/screenshots/01_main.png\" />\n\n"
                "## Safety & Disclaimers\n\nOfficial `main` only.\n\n"
                "## Documentation\n\n"
                "### User Documentation\n- [User Guide](docs/USER_GUIDE.md)\n\n"
                "### Developer Documentation\n- [Developer Guide](docs/DEVELOPMENT.md)\n\n"
                "### Legal & Security Policies\n- [Security Policy](SECURITY.md)\n",
                encoding="utf-8",
            )
            order_violations: list[tuple[Path, int, int]] = []
            detect_repo_standard_issues(root, [], {102}, lambda _p, _ln, _c: False, order_violations)
            self.assertEqual([c for _, _, c in order_violations], [102])

    def _build_minimal_repo(self, root: Path) -> None:
        (root / ".git").mkdir(exist_ok=True)
        (root / "docs").mkdir(exist_ok=True)
        (root / "assets" / "screenshots").mkdir(parents=True, exist_ok=True)
        (root / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
        (root / "assets" / "logo.png").write_bytes(b"LOGO_BYTES")
        (root / "assets" / "icon.png").write_bytes(b"ICON_BYTES")
        (root / "assets" / "icon.ico").write_bytes(b"ICO_BYTES")
        (root / "assets" / "screenshots" / "01_main.png").write_bytes(b"SHOT")
        (root / "LICENSE").write_text("MIT License\n\nCopyright (c) 2026 DontKwo\n", encoding="utf-8")
        (root / "SECURITY.md").write_text("# Security\n\nOnly `main` releases; do not download forked builds.\n", encoding="utf-8")
        (root / "THIRD_PARTY_NOTICES.md").write_text("# Notices\n", encoding="utf-8")
        (root / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
        for doc_name in ("USER_GUIDE.md", "DEVELOPMENT.md", "INSTALLATION.md"):
            (root / "docs" / doc_name).write_text(
                f"# {doc_name}\n\n### Windows\nwin\n\n### macOS\nmac\n\n### Linux\nlin\n\n"
                "## Related Documentation\n- [Overview](../README.md)\n",
                encoding="utf-8",
            )
        (root / ".github" / "workflows" / "ci.yml").write_text(
            "on:\n  push:\n    branches: [main]\n  pull_request:\n    branches: [main]\n"
            "steps:\n  - run: python claudemd_linter.py . && python link_checker.py . && ./app --self-test\n"
            "uses: softprops/action-gh-release@v2\nwith:\n  tag_name: ${{ steps.version.outputs.tag }}\n"
            "  prerelease: false\n  make_latest: true\n",
            encoding="utf-8",
        )
        (root / "README.md").write_text(
            '<p align="center"><img src="assets/logo.png" width="240" /></p>\n\n# Demo\n\n'
            "## Download\n\n"
            "| Platform | Download |\n| :--- | :--- |\n"
            "| Windows | [Demo-Windows.exe](https://github.com/DontKwo/demo/releases/latest/download/Demo-Windows.exe) |\n\n"
            "## Screenshots\n\n<img src=\"assets/screenshots/01_main.png\" />\n\n"
            "## Documentation\n\n"
            "### User Documentation\n- [User Guide](docs/USER_GUIDE.md)\n\n"
            "### Developer Documentation\n- [Developer Guide](docs/DEVELOPMENT.md)\n\n"
            "### Legal & Security Policies\n- [Security Policy](SECURITY.md)\n\n"
            "## Safety & Disclaimers\n\nOfficial `main` only.\n",
            encoding="utf-8",
        )

    def test_rules_105_106_108_109_110_111_and_init_repo(self) -> None:
        from scripts.repo_standards_rules import detect_repo_standard_issues
        from scripts.repo_standardizer import init_repo

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._build_minimal_repo(root)

            # Rule 105 (duplicate Windows links) & Rule 106 (missing APK/UV/OpenFOAM guides)
            (root / "README.md").write_text(
                (root / "README.md").read_text(encoding="utf-8").replace(
                    "| Windows | [Demo-Windows.exe](https://github.com/DontKwo/demo/releases/latest/download/Demo-Windows.exe) |",
                    "| Windows | [Demo-Windows.exe](https://github.com/DontKwo/demo/releases/latest/download/Demo-Windows.exe) |\n"
                    "| Windows | [Demo-Windows.zip](https://github.com/DontKwo/demo/releases/latest/download/Demo-Windows.zip) |\n"
                    "| Android | [Demo-Android.apk](https://github.com/DontKwo/demo/releases/latest/download/Demo-Android.apk) |",
                ),
                encoding="utf-8",
            )
            (root / "pyproject.toml").write_text('[project]\nname = "demo"\n# uses uv and simpleFoam OpenFOAM\n', encoding="utf-8")

            # Rule 108 & Rule 109 violations
            (root / ".github" / "workflows" / "ci.yml").write_text(
                "on:\n  push:\n    branches: [main]\n    paths-ignore: ['*.md']\n"
                "uses: softprops/action-gh-release@v2\nwith:\n  tag_name: main\n  prerelease: true\n",
                encoding="utf-8",
            )
            (root / "LICENSE").write_text("GNU General Public License v3\n", encoding="utf-8")
            (root / "SECURITY.md").write_text("# Security\n\nReport bugs.\n", encoding="utf-8")

            # Rule 110 missing macOS/Linux headings without single_os override
            (root / "docs" / "INSTALLATION.md").write_text(
                "# Install\n\n### Windows\nwin\n\n## Related Documentation\n- [Overview](../README.md)\n",
                encoding="utf-8",
            )

            # Rule 111 disallowed legacy GUI import
            gui_file = root / "app_gui.py"
            gui_file.write_text("import tkinter as tk\n", encoding="utf-8")

            violations: list[tuple[Path, int, int]] = []
            all_codes = set(range(101, 113))
            detect_repo_standard_issues(root, [gui_file], all_codes, lambda _p, _ln, _c: False, violations)
            found_codes = {code for _, _, code in violations}
            self.assertTrue({105, 106, 108, 109, 110, 111}.issubset(found_codes))

            # Verify single_os exemption silences Rule 110
            (root / ".aitools.toml").write_text('[project]\nsingle_os = "windows"\n', encoding="utf-8")
            win_only_violations: list[tuple[Path, int, int]] = []
            detect_repo_standard_issues(root, [], {110}, lambda _p, _ln, _c: False, win_only_violations)
            self.assertEqual(win_only_violations, [])

        with tempfile.TemporaryDirectory() as scaffold_dir:
            repo_path = Path(scaffold_dir) / "MySampleApp"
            repo_path.mkdir()
            actions = init_repo(repo_path, "MySampleApp")
            self.assertGreater(len(actions), 5)
            for req_file in ("README.md", "LICENSE", "SECURITY.md", "THIRD_PARTY_NOTICES.md", "AGENTS.md", "docs/USER_GUIDE.md", ".github/workflows/ci.yml"):
                self.assertTrue((repo_path / req_file).is_file(), f"Missing {req_file}")


if __name__ == "__main__":
    unittest.main()



