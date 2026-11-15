"""Shared utility functions for scripts."""
from __future__ import annotations

import os
import platform
import re
from pathlib import Path

IS_WINDOWS = platform.system() == "Windows"


def get_user_home() -> Path:
    return Path(os.environ.get("USERPROFILE" if IS_WINDOWS else "HOME", Path.home()))


def format_command_path(path: Path) -> str:
    home = get_user_home()
    home_str = str(home)
    path_str = str(path)
    if home_str and home_str not in ("/", "\\", "."):
        try:
            rel = path.resolve().relative_to(home.resolve())
            env_prefix = "%USERPROFILE%" if IS_WINDOWS else "$HOME"
            path_str = f"{env_prefix}{os.sep}{rel}" if str(rel) != "." else env_prefix
        except (ValueError, OSError):
            path_str = str(path)
    if " " in path_str:
        return f'"{path_str}"'
    return path_str


def _extract_brace_block(content: str, start_idx: int) -> str:
    depth = 0
    for idx in range(start_idx, len(content)):
        char = content[idx]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return content[start_idx : idx + 1]
    return content[start_idx:]


def detect_android_release_issues(repo_root: Path) -> list[tuple[Path, int, str]]:
    """Detect Android release signing or manifest cleartext security misconfigurations."""
    issues: list[tuple[Path, int, str]] = []
    android_dir = repo_root / "android"
    if not android_dir.is_dir():
        return issues

    for gradle_file in (android_dir / "app" / "build.gradle", android_dir / "app" / "build.gradle.kts"):
        if not gradle_file.is_file():
            continue
        try:
            content = gradle_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for match in re.finditer(r"\brelease\s*\{", content):
            block_start = match.end() - 1
            block = _extract_brace_block(content, block_start)
            debug_offset = block.find("signingConfigs.debug")
            if debug_offset != -1:
                lineno = content[: block_start + debug_offset].count("\n") + 1
                issues.append(
                    (gradle_file, lineno, "android/app/build.gradle uses signingConfigs.debug in release buildType")
                )

    for manifest_file in android_dir.rglob("AndroidManifest.xml"):
        try:
            content = manifest_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        cleartext_match = re.search(r'android:usesCleartextTraffic\s*=\s*["\']true["\']', content)
        if cleartext_match:
            lineno = content[: cleartext_match.start()].count("\n") + 1
            issues.append(
                (manifest_file, lineno, 'AndroidManifest.xml enables android:usesCleartextTraffic="true"')
            )

    return issues
