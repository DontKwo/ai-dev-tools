"""Unified CLI entry point for Developer AI Development Tools."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
from tools_config import generate_default_config  # noqa: 12

COMMAND_MAP: dict[str, str] = {
    "doctor": "doctor.py",
    "lint": "claudemd_linter.py",
    "fix": "lint_fixer.py",
    "ui": "aiui.py",
    "skills": "skills_manager.py",
    "config": "configure.py",
    "checkpoint": "rollback.py",
    "secrets": "secret_sanitizer.py",
    "test": "smart_test_runner.py",
    "deps": "check_dependencies.py",
    "boost": "boost_types.py",
    "clean": "clean_encoding.py",
    "repo-map": "repo_map.py",
    "tree": "dir_overview.py",
    "slice": "slice_file.py",
    "context": "pack_context.py",
    "tokens": "token_budget.py",
    "diff": "redact_diff.py",
    "search": "fast_search.py",
    "md": "to_markdown.py",
    "grill": "grill_user.py",
    "prune": "prune_dead_code.py",
    "vars": "check_variable_names.py",
    "spell": "spell_checker.py",
    "type-coverage": "type_coverage.py",
    "sync": "sync_rules.py",
    "hooks": "install_antigravity_hooks.py",
    "git-hooks": "install_hooks.py",
    "links": "link_checker.py",
    "todos": "todo_finder.py",
    "licenses": "license_checker.py",
    "complexity": "ast_complexity.py",
    "changelog": "changelog_generator.py",
    "imports": "import_graph.py",
    "branches": "branch_auditor.py",
    "env": "env_validator.py",
    "dead-assets": "dead_assets.py",
    "unused": "unused_symbols.py",
    "git-summary": "git_summary.py",
    "grep": "grep_keywords.py",
    "schema": "schema_validator.py",
    "tables": "format_tables.py",
    "minify": "minify_instructions.py",
    "benchmark": "benchmark_runner.py",
}

COMMAND_ALIASES: dict[str, str] = {
    "repo": "repo-map",
    "rollback": "checkpoint",
    "sec": "secrets",
    "types": "type-coverage",
    "types-coverage": "type-coverage",
}


def print_usage() -> None:
    print("aitools: Developer Unified AI Development Tools Suite\n")
    print("Usage: aitools <command> [options...]\n")
    print("Core & Verification:")
    print("  doctor        Run diagnostics on environment, tool configs, and skills")
    print("  lint          Run 90-rule AST, UI, and writing style linter")
    print("  fix           Run deterministic mechanical auto-fixers")
    print("  ui            Multi-framework UI manifest, evidence, and audit manager")
    print("  test          Run smart AST-driven test runner")
    print("  deps          Scan for hallucinated or missing dependencies")
    print("  secrets       Scan files for leaked credentials and sensitive tokens")
    print("  checkpoint    Manage workspace snapshot checkpoints (save, restore, diff)")
    print("  clean         Clean double-encoded UTF-8 and mojibake text\n")
    print("Codebase Health & Typing:")
    print("  boost         Auto-boost type annotations on Python files")
    print("  prune         Prune dead code and unreferenced functions")
    print("  vars          Audit single-letter and uninformative identifiers")
    print("  spell         Audit code identifiers and comments for spelling errors")
    print("  type-coverage Calculate type annotation coverage percentages")
    print("  grill         Interrogate plans, architecture, and tradeoffs\n")
    print("Context & Optimization:")
    print("  repo-map      Generate compact AST symbol and dependency trees")
    print("  tree          Display token-efficient directory hierarchy")
    print("  slice         Extract targeted line ranges from source files")
    print("  context       Bundle files into prompt packages with token counts")
    print("  tokens        Calculate token budgets and per-file token usage")
    print("  diff          Compress git diffs for prompt context")
    print("  search        Fast regex search with context lines and file filters")
    print("  links         Audit markdown links, anchors, and release download targets")
    print("  md            Convert documents (PDF, DOCX, XLSX, HTML) to Markdown\n")
    print("Configuration & Skills:")
    print("  skills        Inspect, toggle, and sync agent skills across editors")
    print("  config        Configure AI tool instruction files, MCP servers, and skills")
    print("  init-config   Generate default .aitools.toml declarative configuration file")
    print("  sync          Synchronize instruction files across all installed tools")
    print("  hooks         Install pre-commit and Antigravity task hooks")
    print("  git-hooks     Install or remove git pre-commit lint hook\n")
    print("Project Audits:")
    print("  todos         Find TODO/FIXME/HACK comments")  # noqa: 91
    print("  licenses      Check licenses of declared PyPI and npm dependencies")
    print("  complexity    Report AST cyclomatic complexity per function")
    print("  changelog     Generate a changelog between git refs")
    print("  imports       Build an import graph (optional DOT output)")
    print("  branches      Audit and prune merged git branches")
    print("  env           Compare .env against .env.example")
    print("  dead-assets   Find unreferenced asset files")
    print("  unused        Find unused private functions and local variables")
    print("  git-summary   Summarize git repository state")
    print("  grep          Keyword and regex search with skip-dir defaults")
    print("  schema        Validate JSON data against a JSON schema")
    print("  tables        Check or write aligned Markdown tables")
    print("  minify        Compact AI instruction files for token savings")
    print("  benchmark     Time a command over repeated iterations\n")
    print("Pass --help after any command for detailed options (e.g. 'aitools ui --help').")


def run_target_script(script_name: str, args: list[str]) -> int:
    script_path = SCRIPTS_DIR / script_name
    if not script_path.is_file():
        print(f"Error: Target script not found: {script_path}", file=sys.stderr)
        return 1

    cmd = [sys.executable, str(script_path)] + args
    result = subprocess.run(cmd, check=False)
    return result.returncode


def main() -> None:
    raw_args = sys.argv[1:]
    if not raw_args or raw_args[0] in ("-h", "--help", "help"):
        print_usage()
        return

    subcmd = raw_args[0].lower()
    subcmd = COMMAND_ALIASES.get(subcmd, subcmd)
    rest = raw_args[1:]

    if subcmd == "init-config":
        target = Path.cwd() / ".aitools.toml"
        if target.exists():
            print(f"[!] Target file already exists: {target}")
            return
        target.write_text(generate_default_config(), encoding="utf-8")
        print(f"[OK] Generated configuration template at: {target}")
        return

    if subcmd not in COMMAND_MAP:
        print(f"Unknown command: '{subcmd}'. Run 'aitools --help' for available commands.", file=sys.stderr)
        sys.exit(1)

    code = run_target_script(COMMAND_MAP[subcmd], rest)
    sys.exit(code)


if __name__ == "__main__":
    main()
