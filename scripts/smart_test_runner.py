#!/usr/bin/env python3
"""AST-aware test impact runner that executes tests for modified code."""
from __future__ import annotations

import argparse
import ast
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def get_git_modified_files(workspace: Path) -> list[Path]:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(workspace),
            capture_output=True,
            text=True,
            check=False,
        )
        modified_files: list[Path] = []
        for line in result.stdout.splitlines():
            clean_line = line.strip()
            if not clean_line:
                continue
            parts = clean_line.split(maxsplit=1)
            if len(parts) == 2:
                file_path = workspace / parts[1].strip()
                if file_path.suffix == ".py" and file_path.is_file():
                    modified_files.append(file_path)
        return modified_files
    except Exception:
        return []


def extract_symbols_from_file(file_path: Path) -> set[str]:
    try:
        syntax_tree = ast.parse(file_path.read_text(encoding="utf-8", errors="replace"))
        symbols: set[str] = set()
        for node in ast.walk(syntax_tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                symbols.add(node.name)
        return symbols
    except Exception:
        return set()


def get_all_tests(workspace: Path) -> list[Path]:
    test_directory = workspace / "tests"
    if not test_directory.is_dir():
        test_directory = workspace
    return sorted(
        [
            candidate
            for candidate in test_directory.rglob("*.py")
            if candidate.is_file() and (candidate.name.startswith("test_") or candidate.name.endswith("_test.py"))
        ]
    )


def find_matching_tests(workspace: Path, modified_files: list[Path]) -> list[Path]:
    test_files = get_all_tests(workspace)
    matched_tests: set[Path] = set()

    for modified_file in modified_files:
        if modified_file.name.startswith("test_") or modified_file.name.endswith("_test.py"):
            matched_tests.add(modified_file)

    for modified_file in modified_files:
        if modified_file in matched_tests:
            continue
        file_stem = modified_file.stem
        symbols = extract_symbols_from_file(modified_file)
        for test_file in test_files:
            try:
                content = test_file.read_text(encoding="utf-8", errors="replace")
                if test_file.stem == f"test_{file_stem}" or file_stem in content:
                    matched_tests.add(test_file)
                    continue
                if any(symbol_name in content for symbol_name in symbols):
                    matched_tests.add(test_file)
            except Exception:
                continue

    return sorted(matched_tests)


def find_venv_python(start_dir: Path) -> Path | None:
    current_directory = start_dir.resolve()
    is_windows = platform.system() == "Windows"
    rel_exe = Path("Scripts/python.exe") if is_windows else Path("bin/python")

    for parent in [current_directory] + list(current_directory.parents):
        for candidate_name in (".venv", "venv"):
            candidate_binary = parent / candidate_name / rel_exe
            if candidate_binary.is_file():
                return candidate_binary

    if "VIRTUAL_ENV" in os.environ:
        env_directory = Path(os.environ["VIRTUAL_ENV"]).resolve()
        candidate_binary = env_directory / rel_exe
        if candidate_binary.is_file():
            return candidate_binary

    return None


def run_tests(test_files: list[Path], workspace: Path, test_runner: str = "unittest") -> int:
    if not test_files:
        print("[*] No matching tests found.")
        return 0

    venv_python = find_venv_python(workspace)
    if shutil.which("uv"):
        if venv_python:
            runner_binary = ["uv", "run", "--no-project", "--python", str(venv_python)]
        else:
            runner_binary = ["uv", "run", "--no-project", "python"]
    else:
        runner_binary = [str(venv_python)] if venv_python else [sys.executable]

    if test_runner == "pytest":
        command = runner_binary + ["-m", "pytest"] + [str(target) for target in test_files]
    else:
        command = runner_binary + ["-m", "unittest"] + [str(target) for target in test_files]

    execution_result = subprocess.run(command, cwd=str(workspace))
    return execution_result.returncode


def find_impacted_tests(changed_files: list[str]) -> list[str]:
    workspace = Path.cwd()
    modified_paths = [workspace / file_name for file_name in changed_files if file_name.endswith(".py")]
    matched = find_matching_tests(workspace, modified_paths)
    result_paths: list[str] = []
    for test_path in matched:
        try:
            result_paths.append(str(test_path.relative_to(workspace).as_posix()))
        except ValueError:
            result_paths.append(str(test_path.as_posix()))
    return result_paths


def main() -> None:
    parser = argparse.ArgumentParser(description="AST-aware test impact runner.")
    parser.add_argument("files", nargs="*", type=Path, help="Specific files or tests to run")
    parser.add_argument("--workspace", type=Path, default=Path.cwd(), help="Workspace directory")
    parser.add_argument("--all", action="store_true", help="Run all discoverable tests")
    parser.add_argument("--impacted", action="store_true", help="Run tests impacted by git diff")
    parser.add_argument("--runner", choices=["unittest", "pytest"], default="unittest", help="Test runner")
    parser.add_argument(
        "--no-fallback",
        action="store_true",
        help="Disable full-suite fallback when impact mapping is uncertain",
    )
    args = parser.parse_args()

    workspace = args.workspace.resolve()
    all_tests = get_all_tests(workspace)

    if args.all:
        print(f"[*] Running full test suite ({len(all_tests)} test files):")
        for test_file in all_tests:
            print(f"  + {test_file.relative_to(workspace)}")
        sys.exit(run_tests(all_tests, workspace, args.runner))

    if args.impacted:
        try:
            diff_proc = subprocess.run(
                ["git", "diff", "--name-only"],
                cwd=str(workspace),
                capture_output=True,
                text=True,
                check=False,
            )
            changed_names = [line.strip() for line in diff_proc.stdout.splitlines() if line.strip()]
            impacted_strings = find_impacted_tests(changed_names)
            matched = [workspace / path_str for path_str in impacted_strings]
        except Exception:
            matched = []
        sys.exit(run_tests(matched, workspace, args.runner))

    if args.files:
        modified = [target.resolve() for target in args.files if target.is_file()]
    else:
        modified = get_git_modified_files(workspace)

    if not modified:
        print("[*] No modified Python files found. Use --all to run all tests.")
        sys.exit(0)

    matched = find_matching_tests(workspace, modified)

    if not matched and modified and not args.no_fallback:
        print(f"[!] Dependency mapping uncertain: 0 targeted tests matched {len(modified)} modified file(s).")
        print("    Conservative fallback active: running all tests to guarantee test coverage.")
        matched = all_tests

    omitted = [test_target for test_target in all_tests if test_target not in matched]

    print(f"[*] Impacted tests selected ({len(matched)}):")
    for selected_test in matched:
        try:
            rel_path = selected_test.relative_to(workspace)
        except ValueError:
            rel_path = selected_test
        print(f"  + {rel_path}")

    if omitted:
        print(f"[*] Tests omitted ({len(omitted)}):")
        for omitted_test in omitted:
            try:
                rel_path = omitted_test.relative_to(workspace)
            except ValueError:
                rel_path = omitted_test
            print(f"  - {rel_path}")

    sys.exit(run_tests(matched, workspace, args.runner))


if __name__ == "__main__":
    main()
