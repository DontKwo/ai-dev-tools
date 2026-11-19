#!/usr/bin/env python3
"""Pre-prompt secret and credential scanner and masker."""
import argparse
import re
import subprocess
import sys
from pathlib import Path

IGNORED_DIRS = {
    ".git", ".venv", "venv", "__pycache__", "node_modules", "dist",
    "build", ".ai_checkpoints", ".cache",
}

SECRET_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("OpenAI API Key", re.compile(r"\bsk-[a-zA-Z0-9]{20,}\b")),
    ("Anthropic API Key", re.compile(r"\bsk-ant-[a-zA-Z0-9\-_]{20,}\b")),
    ("GitHub Personal Access Token", re.compile(r"\bghp_[a-zA-Z0-9]{36}\b")),
    ("GitHub OAuth / App Token", re.compile(r"\bgh[ousr]_[a-zA-Z0-9]{36}\b")),
    ("AWS Access Key ID", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Slack Token", re.compile(r"\bxox[baprs]-[0-9a-zA-Z\-]{10,}\b")),
    ("Private Key Header", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("Database URL with Password", re.compile(r"[a-zA-Z0-9+]+://[^:\s]+:[^@\s]+@[^/\s]+/\w+")),
    ("Generic Bearer Token", re.compile(r"\bBearer\s+[a-zA-Z0-9\-_\.]{24,}\b", re.IGNORECASE)),
]


def mask_secrets(text: str) -> str:
    masked = text
    for name, pattern in SECRET_PATTERNS:
        def repl(match: re.Match) -> str:
            matched_val = match.group(0)
            if len(matched_val) <= 8:
                return "[REDACTED]"
            return matched_val[:4] + "..." + matched_val[-4:] + f"[{name}]"
        masked = pattern.sub(repl, masked)
    return masked


def scan_file(path: Path) -> list[tuple[int, str, str]]:
    findings: list[tuple[int, str, str]] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return findings

    for i, line in enumerate(lines, 1):
        if "# noqa" in line or "# pragma: allowlist" in line:
            continue
        for name, pattern in SECRET_PATTERNS:
            if pattern.search(line):
                findings.append((i, name, line.strip()))
    return findings


def scan_directory(target: Path) -> dict[Path, list[tuple[int, str, str]]]:
    all_findings: dict[Path, list[tuple[int, str, str]]] = {}
    if target.is_file():
        hits = scan_file(target)
        if hits:
            all_findings[target] = hits
        return all_findings

    for p in target.rglob("*"):
        if not p.is_file():
            continue
        if p.name.startswith(".lint_cache") or any(part in IGNORED_DIRS for part in p.parts):
            continue
        hits = scan_file(p)
        if hits:
            all_findings[p] = hits
    return all_findings


def get_git_files(staged_only: bool = False) -> list[Path]:
    cmd = ["git", "diff", "--name-only", "--cached"] if staged_only else ["git", "diff", "--name-only"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        files = [Path(line.strip()) for line in res.stdout.splitlines() if line.strip()]
        return [f.resolve() for f in files if f.is_file()]
    except Exception:
        return []


def _report_findings(findings: dict[Path, list[tuple[int, str, str]]], base_path: Path) -> None:
    total_leaks = sum(len(hits) for hits in findings.values())
    print("=" * 68)
    print(f"  [!] SECURITY WARNING: {total_leaks} sensitive credential(s) detected!")
    print("=" * 68)
    for path, hits in findings.items():
        try:
            rel = str(path.relative_to(base_path))
        except ValueError:
            rel = str(path)
        print(f"\n{rel}:")
        for lineno, name, snippet in hits:
            masked = snippet[:15] + "..." + snippet[-10:] if len(snippet) > 30 else snippet
            print(f"  Line {lineno:<4} [{name}]: {masked}")
    print("=" * 68)


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan and mask credentials before AI prompt transmission.")
    parser.add_argument("target", nargs="?", default=None, help="Target file or directory")
    parser.add_argument("--mask", action="store_true", help="Print file content with secrets masked")
    parser.add_argument("--stdin", action="store_true", help="Read text from standard input and mask it")
    parser.add_argument("--staged", action="store_true", help="Scan only git staged files")
    parser.add_argument("--diff", action="store_true", help="Scan modified git files")
    parser.add_argument("--exclude", action="append", default=[], help="Directory or pattern to exclude")
    parser.add_argument("--include-tests", action="store_true", help="Include test folders during git scan")
    args = parser.parse_args()

    if args.stdin:
        input_text = sys.stdin.read()
        sys.stdout.write(mask_secrets(input_text))
        sys.exit(0)

    if args.staged or args.diff:
        git_files = get_git_files(staged_only=args.staged)
        findings: dict[Path, list[tuple[int, str, str]]] = {}
        excludes = set(args.exclude)
        if not args.include_tests:
            excludes.update({"tests", "test"})
        for file_path in git_files:
            if file_path.is_file() and not file_path.name.startswith(".lint_cache"):
                if any(part in IGNORED_DIRS or part in excludes for part in file_path.parts):
                    continue
                hits = scan_file(file_path)
                if hits:
                    findings[file_path] = hits
        total_leaks = sum(len(hits) for hits in findings.values())
        if not total_leaks:
            print("[OK] Clean. No exposed credentials detected in git diff.")
            sys.exit(0)
        _report_findings(findings, Path.cwd())
        sys.exit(1)

    raw_target = args.target or "."
    target_path = Path(raw_target).resolve()
    if not target_path.exists():
        sys.stderr.write(f"Error: Target path does not exist: {target_path}\n")
        sys.exit(1)

    if args.mask and target_path.is_file():
        content = target_path.read_text(encoding="utf-8", errors="replace")
        sys.stdout.write(mask_secrets(content))
        sys.exit(0)

    findings = scan_directory(target_path)
    total_leaks = sum(len(hits) for hits in findings.values())

    if not total_leaks:
        print("[OK] Clean. No exposed credentials detected.")
        sys.exit(0)

    _report_findings(findings, target_path)
    sys.exit(1)


if __name__ == "__main__":
    main()

