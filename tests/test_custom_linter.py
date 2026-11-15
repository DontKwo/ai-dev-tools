"""Unit and integration tests for custom YAML linter configuration (Rule 91 & Rule 38)."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts import claudemd_linter, custom_linter, lint_fixer


class TestCustomYamlParser(unittest.TestCase):
    def test_parses_all_supported_categories_and_scalar_forms(self) -> None:
        token_name = "j" + "osh"
        drive_tok = "D" + ":"
        raw_yaml = "\n".join([
            "# Top-level comment",
            "remove:",
            f'  - "{token_name}"  # inline comment stripped outside quotes',
            f'  - pattern: "{drive_tok}"',
            "    case-sensitive: true",
            "    word-boundary: true",
            "    include-tests: false",
            "replace:",
            '  - pattern: "old-tool #v1"',
            '    replacement: "new-tool"',
            "    auto-fix: true",
            'allowed_vars: ["Pr", "Nu", "AoA"]',
            "banned_vars:",
            "  - cursed_name",
            "banned_imports:",
            "  - module: deprecated_pkg",
            '    reason: "Use stdlib instead"',
            "file_guards:",
            '  - glob: "src/**/*.py"',
            '    must-contain:',
            '      - "from __future__ import annotations"',
            '    must-not-contain: ["DO_NOT_SHIP"]',
            'ignore_paths: ["vendor/**", "generated/"]',
            "rule_overrides:",
            '  - glob: "tests/**/*.py"',
            "    skip: [11, 25]",
        ])

        parsed = custom_linter.parse_custom_yaml(raw_yaml)
        cfg = custom_linter.CustomLinterConfig()
        custom_linter._merge_yaml_dict(cfg, parsed)

        self.assertEqual(len(cfg.remove), 2)
        self.assertEqual(cfg.remove[0].pattern, token_name)
        self.assertFalse(cfg.remove[0].case_sensitive)
        self.assertEqual(cfg.remove[1].pattern, drive_tok)
        self.assertTrue(cfg.remove[1].case_sensitive)
        self.assertFalse(cfg.remove[1].include_tests)

        self.assertEqual(len(cfg.replace), 1)
        self.assertEqual(cfg.replace[0].pattern, "old-tool #v1")
        self.assertEqual(cfg.replace[0].replacement, "new-tool")
        self.assertTrue(cfg.replace[0].auto_fix)

        self.assertEqual(cfg.allowed_vars, {"Pr", "Nu", "AoA"})
        self.assertEqual(cfg.banned_vars, {"cursed_name"})
        self.assertEqual([item.module for item in cfg.banned_imports], ["deprecated_pkg"])
        self.assertEqual(len(cfg.file_guards), 1)
        self.assertEqual(cfg.file_guards[0].must_contain, ["from __future__ import annotations"])
        self.assertEqual(cfg.file_guards[0].must_not_contain, ["DO_NOT_SHIP"])
        self.assertEqual(cfg.ignore_paths, ["vendor/**", "generated/"])
        self.assertEqual(cfg.rule_overrides[0].skip, {11, 25})

    def test_tracked_example_template_parses_clean_and_empty(self) -> None:
        example_path = _REPO_ROOT / custom_linter.CUSTOM_EXAMPLE_FILENAME
        self.assertTrue(example_path.is_file())
        parsed = custom_linter.parse_custom_yaml(example_path.read_text(encoding="utf-8"))
        cfg = custom_linter.CustomLinterConfig()
        custom_linter._merge_yaml_dict(cfg, parsed)
        self.assertEqual(cfg.remove, [])
        self.assertEqual(cfg.replace, [])
        self.assertEqual(cfg.allowed_vars, set())
        self.assertEqual(cfg.banned_vars, set())
        self.assertEqual(cfg.banned_imports, [])
        self.assertEqual(cfg.file_guards, [])
        self.assertEqual(cfg.ignore_paths, [])
        self.assertEqual(cfg.rule_overrides, [])


class TestCustomRuleMatching(unittest.TestCase):
    def test_remove_case_sensitivity_and_word_boundary_table(self) -> None:
        token_name = "j" + "osh"
        upper_token = token_name.upper()
        mixed_token = token_name.capitalize()
        d_drive = "D" + ":"
        d_drive_low = "d" + ":"
        e_drive = "E" + ":"
        lan_ip = "192.168." + "1.44"
        ts_ip = "100.64." + "12.9"
        local_host = "node1." + "local"
        ts_host = "box.tail1234." + "ts.net"
        personal_email = "dev@" + "gmail.com"
        phone_num = "555-" + "234-5678"
        handle_url = "discord." + "gg/invite123"
        todo_note = "# TO" + "DO(owner): clean this up"
        cases = [
            # (pattern, case_sensitive, word_boundary, regex, line_text, expected_match)
            (token_name, False, True, False, f"owner = {upper_token}", True),
            (token_name, False, True, False, f"author: {mixed_token}", True),
            (token_name, True, True, False, f"owner = {upper_token}", False),
            (token_name, True, True, False, f"owner = {token_name}", True),
            (token_name, False, True, False, f"prefix{token_name}suffix", False),
            (token_name, False, False, False, f"prefix{token_name}suffix", True),
            (d_drive, False, True, False, f"root = '{d_drive}\\workspace\\app'", True),
            (d_drive, False, True, False, f"root = '{d_drive_low}/workspace/app'", True),
            (d_drive, False, True, False, "method: str = 'ok'", False),
            (d_drive, False, True, False, "record_id: int = 1", False),
            (d_drive, False, True, False, "def fn(d: float, e: float) -> float:", False),
            (e_drive, False, True, False, f"bak = '{e_drive}\\backups\\run1'", True),
            (e_drive, False, True, False, "except Exception as e:", False),
            (e_drive, False, True, False, "fn = lambda e: e.name", False),
            (r"\b192\.168\.\d{1,3}\.\d{1,3}\b", False, True, True, f"host = '{lan_ip}'", True),
            (r"\b192\.168\.\d{1,3}\.\d{1,3}\b", False, True, True, "version = '192.168.1'", False),
            (r"\b100\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", False, True, True, f"ts = '{ts_ip}'", True),
            (r"\b100\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", False, True, True, "pct = '100.5'", False),
            (r"\b[a-zA-Z0-9-]+\.(?:local|internal|lan|home\.arpa|tail[a-z0-9]+\.ts\.net)\b", False, True, True, f"h = '{local_host}'", True),
            (r"\b[a-zA-Z0-9-]+\.(?:local|internal|lan|home\.arpa|tail[a-z0-9]+\.ts\.net)\b", False, True, True, f"h = '{ts_host}'", True),
            (r"\b[a-zA-Z0-9-]+\.(?:local|internal|lan|home\.arpa|tail[a-z0-9]+\.ts\.net)\b", False, True, True, "url = 'example.com'", False),
            (r"\b[A-Za-z0-9._%+-]+@(?:gmail|yahoo|outlook|hotmail|icloud|protonmail|proton)\.[A-Za-z]{2,}\b", False, True, True, f"mail = '{personal_email}'", True),
            (r"\b[A-Za-z0-9._%+-]+@(?:gmail|yahoo|outlook|hotmail|icloud|protonmail|proton)\.[A-Za-z]{2,}\b", False, True, True, "mail = 'noreply@example.org'", False),
            (r"(?<![\d.])(?:\+1[-.\s]?)?\(?[2-9]\d{2}\)?[-.\s]\d{3}[-.\s]\d{4}\b", False, True, True, f"tel = '{phone_num}'", True),
            (r"(?<![\d.])(?:\+1[-.\s]?)?\(?[2-9]\d{2}\)?[-.\s]\d{3}[-.\s]\d{4}\b", False, True, True, "ts = '2026-11-15'", False),
            (r"(?:https?://)?(?:t\.me|wa\.me|discord\.gg)/[A-Za-z0-9_+-]+", False, True, True, f"inv = 'https://{handle_url}'", True),
            (r"(?:https?://)?(?:t\.me|wa\.me|discord\.gg)/[A-Za-z0-9_+-]+", False, True, True, "url = 'https://github.com/org/repo'", False),
            (r"\bTODO\s*\([^)]+\)", False, True, True, todo_note, True),
            (r"\bTODO\s*\([^)]+\)", False, True, True, "normal comment without tag", False),
        ]

        for pat, case_sens, boundary, is_regex, sample_line, expected in cases:
            with self.subTest(pattern=pat, case_sensitive=case_sens, line=sample_line):
                compiled = custom_linter.compile_pattern_regex(pat, case_sens, boundary, is_regex)
                self.assertIsNotNone(compiled)
                self.assertEqual(bool(compiled.search(sample_line)), expected)  # type: ignore[union-attr]

    def test_invalid_regex_returns_none_safely(self) -> None:
        self.assertIsNone(custom_linter.compile_pattern_regex("[unclosed(", regex=True))

    def test_remove_include_tests_and_noqa_suppression(self) -> None:
        d_drive = "D" + ":"
        d_drive_low = "d" + ":"
        cfg = custom_linter.CustomLinterConfig(
            remove=[
                custom_linter.RemoveRule(pattern=d_drive, case_sensitive=False, include_tests=False),
                custom_linter.RemoveRule(pattern="secret_marker", include_tests=True),
            ]
        )
        lines = [
            f"path_one = '{d_drive_low}/alpha'",
            "path_two = 'secret_marker'",
            "path_three = 'secret_marker'  # noqa: 91",
        ]
        source = "\n".join(lines)

        test_violations = custom_linter.scan_custom_rules_for_file(
            Path("tests/test_sample.py"),
            source,
            lines,
            cfg,
            claudemd_linter.suppressed,
        )
        self.assertEqual([(v[1], v[2]) for v in test_violations], [(2, 91)])

        src_violations = custom_linter.scan_custom_rules_for_file(
            Path("scripts/module.py"),
            source,
            lines,
            cfg,
            claudemd_linter.suppressed,
        )
        self.assertEqual([(v[1], v[2]) for v in src_violations], [(1, 91), (2, 91)])

    def test_replace_and_lint_fixer_auto_fix(self) -> None:
        cfg = custom_linter.CustomLinterConfig(
            replace=[
                custom_linter.ReplaceRule(pattern="legacy_brand", replacement="modern_brand", auto_fix=True),
                custom_linter.ReplaceRule(pattern="manual_only", replacement="modern_manual", auto_fix=False),
            ]
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            sample = workspace / "app.py"
            sample.write_text('TITLE = "LEGACY_BRAND vs manual_only"\n', encoding="utf-8")

            matches = custom_linter.scan_custom_rules_for_file(
                sample,
                sample.read_text(encoding="utf-8"),
                sample.read_text(encoding="utf-8").splitlines(),
                cfg,
                claudemd_linter.suppressed,
                root=workspace,
            )
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0][2], 91)

            fix_count = lint_fixer.fix_file(
                sample,
                dry_run=False,
                fix_emojis=False,
                fix_banners=False,
                custom_config=cfg,
            )
            self.assertEqual(fix_count, 1)
            self.assertEqual(sample.read_text(encoding="utf-8"), 'TITLE = "modern_brand vs manual_only"\n')

            yaml_cfg_file = workspace / custom_linter.CUSTOM_CONFIG_FILENAME
            yaml_cfg_file.write_text('replace: "legacy_brand"\n', encoding="utf-8")
            skipped_fixes = lint_fixer.fix_file(
                yaml_cfg_file,
                dry_run=False,
                fix_emojis=False,
                custom_config=cfg,
            )
            self.assertEqual(skipped_fixes, 0)

    def test_allowed_and_banned_vars_hook_into_rule_38(self) -> None:
        source = "\n".join([
            "def compute_ratio(cursed_arg: float, special_k: float) -> float:",
            "    Z = special_k * 2.0",
            "    return cursed_arg + Z",
        ])
        lines = source.splitlines()
        sample_path = Path("solver.py")

        default_violations: list[tuple[Path, int, int]] = []
        claudemd_linter.scan_python_ast(
            sample_path,
            source,
            lines,
            default_violations,
            custom_cfg=custom_linter.CustomLinterConfig(),
        )
        default_rule_38 = [(lineno, code) for _, lineno, code in default_violations if code == 38]
        self.assertEqual(default_rule_38, [(2, 38)])

        custom_cfg = custom_linter.CustomLinterConfig(
            allowed_vars={"Z"},
            banned_vars={"cursed_arg"},
        )
        custom_violations: list[tuple[Path, int, int]] = []
        claudemd_linter.scan_python_ast(
            sample_path,
            source,
            lines,
            custom_violations,
            custom_cfg=custom_cfg,
        )
        custom_rule_38 = [(lineno, code) for _, lineno, code in custom_violations if code == 38]
        self.assertEqual(custom_rule_38, [(1, 38)])

    def test_banned_imports_and_file_guards_and_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            src_dir = workspace / "src"
            src_dir.mkdir()
            target_file = src_dir / "service.py"
            source = "\n".join([
                "import forbidden_lib.client",
                "from pathlib import Path",
                "FLAG = 'DO_NOT_SHIP'",
                "x = Path('ok')  # comment without annotation needed here",
            ])
            target_file.write_text(source, encoding="utf-8")

            cfg = custom_linter.CustomLinterConfig(
                banned_imports=[custom_linter.BannedImportRule(module="forbidden_lib")],
                file_guards=[
                    custom_linter.FileGuardRule(
                        glob="src/**/*.py",
                        must_contain=["def health_check"],
                        must_not_contain=["DO_NOT_SHIP"],
                    )
                ],
                ignore_paths=["vendor/**"],
                rule_overrides=[custom_linter.RuleOverride(glob="src/**/*.py", skip={11})],
            )
            violations = custom_linter.scan_custom_rules_for_file(
                target_file,
                source,
                source.splitlines(),
                cfg,
                claudemd_linter.suppressed,
                root=workspace,
            )
            self.assertEqual([(v[1], v[2]) for v in violations], [(1, 91), (1, 91), (3, 91)])

            ignored = workspace / "vendor" / "third_party.py"
            ignored.parent.mkdir()
            ignored.write_text("import forbidden_lib\n", encoding="utf-8")
            self.assertTrue(custom_linter.is_ignored_by_custom_config(ignored, cfg, root=workspace))

            filtered = custom_linter.filter_overridden_violations(
                [(target_file, 1, 11), (target_file, 1, 91)],
                cfg,
                root=workspace,
            )
            self.assertEqual(filtered, [(target_file, 1, 91)])


class TestCustomLinterEndToEnd(unittest.TestCase):
    def test_cli_main_applies_workspace_custom_config_and_clean_pass(self) -> None:
        d_drive = "D" + ":"
        d_drive_low = "d" + ":"
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            cfg_file = workspace / custom_linter.CUSTOM_CONFIG_FILENAME
            cfg_file.write_text(
                "\n".join([
                    "remove:",
                    f'  - "{d_drive}"',
                    "  - pattern: custom_forbidden",
                    "    case-sensitive: false",
                    "allowed_vars: [Ma]",
                    "rule_overrides:",
                    '  - glob: "src/*.py"',
                    "    skip: [25]",
                ]),
                encoding="utf-8",
            )
            src_dir = workspace / "src"
            src_dir.mkdir()
            py_file = src_dir / "module.py"
            py_file.write_text(
                "\n".join([
                    '"""Doc."""',
                    "",
                    "def compute_mach(Ma: float) -> str:",
                    '    print(Ma)',
                    f'    bad_path = "{d_drive_low}/builds/custom_forbidden/out.txt"',
                    "    return bad_path",
                ]),
                encoding="utf-8",
            )
            report_path = workspace / "report.txt"

            had_custom_env = "AI_DEV_TOOLS_CUSTOM_CONFIG" in os.environ
            prev_custom_env = os.environ.get("AI_DEV_TOOLS_CUSTOM_CONFIG")
            prev_argv = sys.argv[:]
            os.environ["AI_DEV_TOOLS_CUSTOM_CONFIG"] = str(cfg_file)
            try:
                sys.argv = [
                    "claudemd_linter.py",
                    str(workspace),
                    "--full",
                    "--no-cache",
                    "--no-ruff",
                    "--no-parallel",
                    "--report",
                    str(report_path),
                ]
                exit_code = claudemd_linter.main()
                self.assertEqual(exit_code, 1)
                report_text = report_path.read_text(encoding="utf-8")
                self.assertIn("code=91", report_text)
                self.assertNotIn("code=25", report_text)
                self.assertNotIn("code=38", report_text)

                py_file.write_text(
                    "\n".join([
                        '"""Doc."""',
                        "",
                        "def compute_mach(Ma: float) -> str:",
                        "    print(Ma)",
                        '    clean_path = "builds/out.txt"',
                        "    return clean_path",
                    ]),
                    encoding="utf-8",
                )
                clean_exit = claudemd_linter.main()
                self.assertEqual(clean_exit, 0)
                self.assertFalse(report_path.exists())
            finally:
                sys.argv = prev_argv
                if not had_custom_env:
                    os.environ.pop("AI_DEV_TOOLS_CUSTOM_CONFIG", None)
                elif prev_custom_env is not None:
                    os.environ["AI_DEV_TOOLS_CUSTOM_CONFIG"] = prev_custom_env


if __name__ == "__main__":
    unittest.main()
