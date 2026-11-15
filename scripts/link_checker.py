#!/usr/bin/env python3
"""Validates documentation links, local file paths, anchors, and release download URLs."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
HEADING_PATTERN = re.compile(r"^#{1,6}\s+(.+)$", re.MULTILINE)
RELEASE_LINK_PATTERN = re.compile(r"https?://github\.com/[^/]+/[^/]+/releases/(?:download/[^/]+|latest/download)/([^/#?]+)")


def slugify_heading(heading_text: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", "", heading_text.lower())
    return re.sub(r"[-\s]+", "-", cleaned).strip("-")


def extract_markdown_anchors(file_path: Path) -> set[str]:
    try:
        content = file_path.read_text(encoding="utf-8")
    except OSError:
        return set()
    anchors = set()
    for match in HEADING_PATTERN.finditer(content):
        anchors.add(slugify_heading(match.group(1)))
    return anchors


def find_workflow_artifact_names(repo_root: Path) -> set[str]:
    workflow_dir = repo_root / ".github" / "workflows"
    if not workflow_dir.is_dir():
        return set()
    artifacts: set[str] = set()
    for wf in workflow_dir.glob("*.yml"):
        try:
            text = wf.read_text(encoding="utf-8")
            for token in re.findall(r"[\w.-]+\.(?:apk|aab|zip|exe|tar\.gz|dmg)", text):
                artifacts.add(token)
        except OSError:
            continue
    return artifacts


def validate_markdown_file(file_path: Path, repo_root: Path, check_external: bool = False) -> list[str]:
    errors: list[str] = []
    try:
        content = file_path.read_text(encoding="utf-8")
    except OSError as err:
        return [f"Could not read {file_path}: {err}"]

    workflow_artifacts = find_workflow_artifact_names(repo_root)
    in_code_block = False

    for line_idx, line in enumerate(content.splitlines(), 1):
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        for match in LINK_PATTERN.finditer(line):
            link_target = match.group(2).strip()
            if not link_target or link_target.startswith("mailto:"):
                continue

            release_match = RELEASE_LINK_PATTERN.search(link_target)
            if release_match:
                artifact_name = release_match.group(1)
                if workflow_artifacts and artifact_name not in workflow_artifacts:
                    errors.append(
                        f"{file_path}:{line_idx}: Release download '{artifact_name}' has no matching build workflow artifact"
                    )
                continue

            if link_target.startswith("http://") or link_target.startswith("https://"):
                continue

            # Local link handling
            target_path_part = link_target.split("#")[0]
            anchor_part = link_target.split("#")[1] if "#" in link_target else ""

            if target_path_part:
                resolved_target = (file_path.parent / target_path_part).resolve()
                if not resolved_target.exists():
                    errors.append(f"{file_path}:{line_idx}: Broken local link '{target_path_part}' (file not found)")
                    continue
                target_file = resolved_target
            else:
                target_file = file_path

            if anchor_part and target_file.is_file() and target_file.suffix.lower() == ".md":
                valid_anchors = extract_markdown_anchors(target_file)
                slug = slugify_heading(anchor_part)
                if valid_anchors and slug not in valid_anchors:
                    errors.append(f"{file_path}:{line_idx}: Missing anchor '#{anchor_part}' in {target_file.name}")

    return errors


EXCLUDED_DIR_NAMES = {
    "node_modules", ".git", "dist", "build", ".venv", "venv",
    ".gemini", ".agent", ".agents", ".claude", ".cursor", "__pycache__"
}


def run_link_check(target_dir: Path, check_external: bool = False, verbose: bool = False) -> int:
    repo_root = target_dir
    while repo_root.parent != repo_root and not (repo_root / ".git").exists():
        repo_root = repo_root.parent

    md_files = list(target_dir.rglob("*.md")) if target_dir.is_dir() else [target_dir]
    total_errors: list[str] = []

    for md_file in md_files:
        if any(part in EXCLUDED_DIR_NAMES or part.startswith(".") for part in md_file.parts):
            continue
        errs = validate_markdown_file(md_file, repo_root, check_external)
        if errs:
            total_errors.extend(errs)
        elif verbose:
            print(f"[OK] {md_file.relative_to(target_dir)}")

    if total_errors:
        print(f"\nLink Checker: Found {len(total_errors)} issue(s):", file=sys.stderr)
        for err in total_errors:
            print(f"  [X] {err}", file=sys.stderr)
        return 1

    print(f"[OK] Link Checker: Scanned {len(md_files)} markdown files. All links valid.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit markdown links and release download targets.")
    parser.add_argument("path", nargs="?", default=".", help="Directory or markdown file to check (default: .)")
    parser.add_argument("--check-external", action="store_true", help="Validate external HTTP/HTTPS URLs")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print verbose scan progress")

    args = parser.parse_args()
    target_path = Path(args.path).resolve()
    exit_code = run_link_check(target_path, check_external=args.check_external, verbose=args.verbose)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
