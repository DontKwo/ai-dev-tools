"""Token compressor for agent terminal commands.
Compresses command outputs by 60% to 90% to prevent context bloat.
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import re
import subprocess
import sys

ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def strip_ansi(raw_text: str) -> str:
    """Remove terminal ANSI color and control sequences from command text."""
    return ANSI_ESCAPE_RE.sub("", raw_text)


def compress_git_status(raw: str) -> str:
    """Compress verbose or short git status output into a concise summary."""
    cleaned = strip_ansi(raw)
    lines = [line.rstrip() for line in cleaned.splitlines() if line.strip()]
    staged: list[str] = []
    modified: list[str] = []
    untracked: list[str] = []
    branch = "unknown"
    section = ""

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            branch = stripped[3:].split("...", 1)[0].strip()
            continue
        if stripped.startswith("# On branch") or stripped.startswith("On branch"):
            branch = stripped.split()[-1]
            continue
        if stripped.startswith("Changes to be committed:"):
            section = "staged"
            continue
        if stripped.startswith("Changes not staged"):
            section = "modified"
            continue
        if stripped.startswith("Untracked files:"):
            section = "untracked"
            continue
        if stripped.startswith("(") or stripped.startswith("no changes added"):
            continue

        short_match = re.match(r"^([ MADRCU?!]{2})\s+(.+)$", line)
        if short_match:
            code, rel_path = short_match.groups()
            if code == "??":
                untracked.append(rel_path)
            elif code[0] != " ":
                staged.append(rel_path)
            else:
                modified.append(rel_path)
            continue

        for prefix in ("modified:", "new file:", "deleted:", "renamed:"):
            if stripped.startswith(prefix):
                target = stripped.split(prefix, 1)[1].strip()
                if section == "staged":
                    staged.append(target)
                else:
                    modified.append(target)
                break
        else:
            if section == "untracked" and " " not in stripped:
                untracked.append(stripped)

    summary = [f"Branch: {branch}"]
    for label, entries in (("Staged", staged), ("Modified", modified), ("Untracked", untracked)):
        if entries:
            summary.append(f"{label} ({len(entries)}): " + ", ".join(entries[:10]))
            if len(entries) > 10:
                summary.append(f"  ... and {len(entries) - 10} more {label.lower()}")
    if not staged and not modified and not untracked:
        summary.append("Working tree clean.")
    return "\n".join(summary)


def compress_test_output(raw: str) -> str:
    """Condense test runner logs, keeping failures while trimming passing noise."""
    cleaned = strip_ansi(raw)
    lines = cleaned.splitlines()
    if not lines:
        return ""

    failure_markers = ("FAILED", "FAIL:", "FAIL ", "ERROR:", "Traceback", "AssertionError", "test result: FAILED")
    has_failures = any(any(marker in line for marker in failure_markers) for line in lines)
    if not has_failures:
        pass_patterns = (
            r"Ran \d+ tests? in",
            r"\d+ passed",
            r"Test Files\s+\d+ passed",
            r"Tests\s+\d+ passed",
            r"test result:\s+ok\.",
            r"BUILD SUCCESSFUL",
            r"Tests run:\s+\d+,\s+Passed:",
        )
        summary_lines = [line.strip() for line in lines if any(re.search(pat, line) for pat in pass_patterns)]
        if summary_lines:
            return "[PASS] " + " | ".join(summary_lines[-2:])
        return "[PASS] All tests passed."

    failure_lines: list[str] = []
    capturing = False
    for line in lines:
        if any(marker in line for marker in ("FAIL:", "FAIL ", "ERROR:", "Traceback", "FAILED", "AssertionError", "E   ")):
            capturing = True
        if capturing:
            failure_lines.append(line)
        if line.startswith("Ran ") or line.startswith("FAILED (") or line.startswith("==="):
            if capturing and line not in failure_lines:
                failure_lines.append(line)
            capturing = False
    return "\n".join(failure_lines[:120]) if failure_lines else cleaned


def compress_compiler_warnings(raw: str) -> str:
    """Deduplicate repeated compiler or static-check warnings with occurrence counts."""
    cleaned = strip_ansi(raw)
    warning_counts: Counter[str] = Counter()
    important_lines: list[str] = []
    for line in cleaned.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if re.search(r"\bwarning(\[[^\]]+\])?:", stripped, re.IGNORECASE):
            normalized = re.sub(r"^\S+?:\d+(?::\d+)?:", "<loc>:", stripped)
            warning_counts[normalized] += 1
        else:
            important_lines.append(line)
    for warning_text, count in warning_counts.most_common(25):
        suffix = f" (x{count})" if count > 1 else ""
        important_lines.append(f"{warning_text}{suffix}")
    return "\n".join(important_lines)


def _compress_git_diff(raw: str) -> str:
    """Compress raw git diff output by removing context filler and blank churn."""
    cleaned = strip_ansi(raw)
    kept: list[str] = []
    for line in cleaned.splitlines():
        if line.startswith(("diff --git", "@@", "+", "-")):
            if line.startswith(("+++", "---")):
                continue
            if line in ("+", "-"):
                continue
            kept.append(line)
    if len(kept) > 200:
        omitted = len(kept) - 200
        kept = kept[:200] + [f"... [{omitted} diff lines truncated]"]
    return "\n".join(kept)


def compress_command_output(command: str, raw_output: str) -> tuple[str, float]:
    """Compress terminal output based on command type and return savings ratio."""
    cmd_lower = command.lower()
    original_len = len(raw_output)
    if original_len == 0:
        return "", 0.0

    cleaned = strip_ansi(raw_output)
    if "git status" in cmd_lower:
        compressed = compress_git_status(cleaned)
    elif "git diff" in cmd_lower:
        compressed = _compress_git_diff(cleaned)
    elif any(runner in cmd_lower for runner in ("pytest", "unittest", "cargo test", "npm test", "vitest", "jest", "gradlew", "pester")):
        compressed = compress_test_output(cleaned)
    elif any(builder in cmd_lower for builder in ("cargo build", "cargo check", "tsc", "mypy", "ruff", "gcc", "clang")):
        compressed = compress_compiler_warnings(cleaned)
    else:
        seen_lines: set[str] = set()
        deduped: list[str] = []
        for line in cleaned.splitlines():
            stripped = line.strip()
            if stripped and stripped not in seen_lines:
                deduped.append(line)
                seen_lines.add(stripped)
        compressed = "\n".join(deduped)

    new_len = len(compressed)
    savings = max(0.0, 1.0 - (new_len / max(1, original_len)))
    return compressed, savings


def run_and_compress(cmd: list[str], cwd: Path | None = None, timeout_sec: int = 120) -> tuple[int, str, float]:
    """Execute a terminal command directly without a shell and compress its output."""
    if not cmd:
        return 1, "No command provided.", 0.0
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_sec,
        check=False,
    )
    combined = proc.stdout + (("\n" + proc.stderr) if proc.stderr else "")
    compressed, savings = compress_command_output(" ".join(cmd), combined)
    return proc.returncode, compressed, savings


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint supporting both piped stdin filtering and --run execution."""
    parser = argparse.ArgumentParser(description="Compress command output for token efficiency.")
    parser.add_argument("--run", action="store_true", help="Execute command tokens and compress its output")
    parser.add_argument("--cwd", type=Path, default=None, help="Working directory when executing with --run")
    parser.add_argument("command_parts", nargs=argparse.REMAINDER, help="Command name (stdin) or command args (--run)")
    args = parser.parse_args(argv)

    parts = [part for part in args.command_parts if part != "--"]
    if args.run:
        code, result, savings = run_and_compress(parts, cwd=args.cwd)
        header = f"[RTK-Filter: {savings * 100:.1f}% token savings | exit={code}]\n"
        sys.stdout.write(header + result + "\n")
        return code

    if not parts:
        return 0
    command_name = " ".join(parts)
    if not sys.stdin.isatty():
        input_text = sys.stdin.read()
        result, savings = compress_command_output(command_name, input_text)
        header = f"[RTK-Filter: {savings * 100:.1f}% token savings]\n"
        sys.stdout.write(header + result + "\n")
        return 0

    code, result, savings = run_and_compress(parts, cwd=args.cwd)
    header = f"[RTK-Filter: {savings * 100:.1f}% token savings | exit={code}]\n"
    sys.stdout.write(header + result + "\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
