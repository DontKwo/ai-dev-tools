"""Repository structure, README layout, companion doc, branding, and CI parity checks (Rules 101-112)."""

from __future__ import annotations

import ast
import hashlib
import re
from pathlib import Path
from typing import Callable

from scripts.tools_config import load_tools_config

REQUIRED_ROOT_FILES = (
    "README.md",
    "LICENSE",
    "SECURITY.md",
    "THIRD_PARTY_NOTICES.md",
    "AGENTS.md",
    "docs/USER_GUIDE.md",
    "docs/DEVELOPMENT.md",
    ".github/workflows/ci.yml",
)

BANNED_ROOT_FILES = (
    "PLAN.md",
    "DESIGN.md",
    "DECISIONS.md",
    "COPYRIGHT",
    "NOTICES.md",
    "REQUIREMENTS_TRACEABILITY.md",
    "tasks.json",
    ".orchestrator_state.json",
    "SHA256SUMS.txt",
)

TECH_LEAKAGE_PATTERNS = (
    re.compile(r"\bSHA256SUMS\b", re.IGNORECASE),
    re.compile(r"\bsha256\b", re.IGNORECASE),
    re.compile(r"\bgit\s+clone\b", re.IGNORECASE),
    re.compile(r"\b(?:pytest|vitest|cargo\s+test|gradlew|Invoke-Pester|pyinstaller)\b"),
    re.compile(r"\b(?:github/workflows|GitHub\s+Actions|CI/CD\s+pipeline)\b", re.IGNORECASE),
    re.compile(r"\buv\s+(?:run|sync)\b"),
)

UNLINKED_BACKTICK_DOC_RE = re.compile(
    r"(?<!\[)\b(?:see|under|refer to|check|read|inside|in)\s+`([^`]*(?:\.md|docs/)[^`]*)`",
    re.IGNORECASE,
)

DOWNLOAD_EXT_RE = re.compile(r"releases/latest/download/[^\s)>\"]+\.(?:exe|zip|tar\.gz|dmg|apk)")
DISALLOWED_GUI_IMPORTS = {"tkinter", "PyQt5", "PyQt6", "PySide2", "PySide6", "wx"}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _line_of_offset(text: str, offset: int) -> int:
    return text[:offset].count("\n") + 1


def _check_rule_101_hygiene(root: Path, no_qa: Callable[[Path, int, int], bool], violations: list[tuple[Path, int, int]]) -> None:
    anchor = root / "README.md" if (root / "README.md").is_file() else root
    for rel in REQUIRED_ROOT_FILES:
        if not (root / rel).is_file() and not no_qa(anchor, 1, 101):
            violations.append((anchor, 1, 101))

    for name in BANNED_ROOT_FILES:
        banned_path = root / name
        if banned_path.exists() and not no_qa(banned_path, 1, 101):
            violations.append((banned_path, 1, 101))

    for binary in list(root.glob("*.exe")) + list(root.glob("*.apk")):
        if not no_qa(binary, 1, 101):
            violations.append((binary, 1, 101))


def _check_rule_102_readme(
    readme_path: Path,
    content: str,
    lines: list[str],
    no_qa: Callable[[Path, int, int], bool],
    violations: list[tuple[Path, int, int]],
) -> None:
    if no_qa(readme_path, 1, 102):
        return
    if len(lines) > 120:
        violations.append((readme_path, len(lines), 102))
    if "assets/logo.png" not in content:
        violations.append((readme_path, 1, 102))
    if "via.placeholder.com" in content:
        violations.append((readme_path, _line_of_offset(content, content.index("via.placeholder.com")), 102))

    dl_idx = content.find("## Download")
    shot_idx = content.find("## Screenshots")
    safety_idx = content.find("## Safety & Disclaimers")
    docs_idx = content.find("## Documentation")
    for required_idx in (dl_idx, shot_idx, safety_idx, docs_idx):
        if required_idx == -1:
            violations.append((readme_path, 1, 102))
            return

    if not (dl_idx < shot_idx < safety_idx < docs_idx):
        violations.append((readme_path, _line_of_offset(content, shot_idx), 102))
    if "assets/screenshots/" not in content[shot_idx:docs_idx]:
        violations.append((readme_path, _line_of_offset(content, shot_idx), 102))

    docs_sec = content[docs_idx:]
    order_markers = ("### User Documentation", "### Developer Documentation", "### Legal & Security Policies")
    positions = [docs_sec.find(marker) for marker in order_markers]
    if any(pos == -1 for pos in positions) or not (positions[0] < positions[1] < positions[2]):
        violations.append((readme_path, _line_of_offset(content, docs_idx), 102))


def _check_rule_103_readme_leakage(
    readme_path: Path,
    lines: list[str],
    no_qa: Callable[[Path, int, int], bool],
    violations: list[tuple[Path, int, int]],
) -> None:
    for idx, line in enumerate(lines, 1):
        if no_qa(readme_path, idx, 103):
            continue
        for pat in TECH_LEAKAGE_PATTERNS:
            if pat.search(line):
                violations.append((readme_path, idx, 103))
                break


def _check_rule_104_circular_docs(
    root: Path,
    no_qa: Callable[[Path, int, int], bool],
    violations: list[tuple[Path, int, int]],
) -> None:
    md_targets: list[Path] = []
    if (root / "README.md").is_file():
        md_targets.append(root / "README.md")
    if (root / "docs").is_dir():
        md_targets.extend(sorted((root / "docs").rglob("*.md")))

    for md_file in md_targets:
        try:
            text = md_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        in_fence = False
        for idx, line in enumerate(text.splitlines(), 1):
            if line.strip().startswith("```"):
                in_fence = not in_fence
                continue
            if not in_fence:
                stripped_links = re.sub(r"\[[^\]]*\]\([^)]*\)", "", line)
                if UNLINKED_BACKTICK_DOC_RE.search(stripped_links) and not no_qa(md_file, idx, 104):
                    violations.append((md_file, idx, 104))

        if md_file.parent.name != root.name and "docs" in md_file.parts:
            if no_qa(md_file, 1, 104):
                continue
            rel_parts = md_file.relative_to(root).parts
            up_prefix = "../" * (len(rel_parts) - 1)
            expected_readme_link = f"{up_prefix}README.md"
            if "## Related Documentation" not in text or expected_readme_link not in text:
                violations.append((md_file, max(1, len(text.splitlines())), 104))


def _check_rule_105_minimal_downloads(
    readme_path: Path,
    content: str,
    no_qa: Callable[[Path, int, int], bool],
    violations: list[tuple[Path, int, int]],
) -> None:
    dl_match = re.search(r"## Download\s*(.*?)(?:\n## |\Z)", content, re.DOTALL)
    if not dl_match:
        return
    dl_body = dl_match.group(1)
    seen_platforms: set[str] = set()
    base_line = _line_of_offset(content, dl_match.start())
    for offset_idx, row in enumerate(dl_body.splitlines()):
        lineno = base_line + offset_idx
        stripped = row.strip()
        if not stripped.startswith("|") or stripped.startswith("| Platform") or stripped.startswith("| Operating") or stripped.startswith("| :---"):
            continue
        if no_qa(readme_path, lineno, 105):
            continue
        links = DOWNLOAD_EXT_RE.findall(stripped)
        if len(links) > 1:
            violations.append((readme_path, lineno, 105))
            continue
        row_lower = stripped.lower()
        for plat in ("windows", "macos", "linux", "android"):
            if plat in row_lower:
                if plat in seen_platforms:
                    violations.append((readme_path, lineno, 105))
                seen_platforms.add(plat)


def _check_rule_106_and_107(
    root: Path,
    readme_text: str,
    no_qa: Callable[[Path, int, int], bool],
    violations: list[tuple[Path, int, int]],
) -> None:
    readme_path = root / "README.md"
    if not readme_path.is_file():
        return
    lower_readme = readme_text.lower()
    if (".apk" in lower_readme or (root / "android").is_dir()) and not (root / "docs" / "APK_INSTALLATION.md").is_file():
        if not no_qa(readme_path, 1, 106):
            violations.append((readme_path, 1, 106))
    if any(tok in lower_readme for tok in (".exe", ".zip", ".tar.gz", ".dmg")) and not (root / "docs" / "INSTALLATION.md").is_file():
        if not no_qa(readme_path, 1, 106):
            violations.append((readme_path, 1, 106))

    uses_uv = (root / "pyproject.toml").is_file() or "uv run" in (
        (root / "docs" / "DEVELOPMENT.md").read_text(encoding="utf-8", errors="ignore")
        if (root / "docs" / "DEVELOPMENT.md").is_file()
        else ""
    )
    if uses_uv and not (root / "docs" / "UV_INSTALLATION.md").is_file() and not no_qa(readme_path, 1, 106):
        violations.append((readme_path, 1, 106))

    uses_openfoam = "openfoam" in readme_text.lower() or any((root / name).exists() for name in ("openfoam", "cases"))
    if not uses_openfoam and (root / "src").is_dir():
        uses_openfoam = any(
            "simplefoam" in py_file.read_text(encoding="utf-8", errors="ignore").lower()
            for py_file in (root / "src").rglob("*.py")
        )
    if uses_openfoam and not (root / "docs" / "OPENFOAM_INSTALLATION.md").is_file() and not no_qa(readme_path, 1, 106):
        violations.append((readme_path, 1, 106))

    logo_path = root / "assets" / "logo.png"
    icon_path = root / "assets" / "icon.png"
    if (not logo_path.is_file() or not icon_path.is_file()) and not no_qa(readme_path, 1, 107):
        violations.append((readme_path, 1, 107))
    elif logo_path.is_file() and icon_path.is_file() and _sha256(logo_path) == _sha256(icon_path):
        if not no_qa(readme_path, 1, 107):
            violations.append((readme_path, 1, 107))
    if ".exe" in lower_readme and not (root / "assets" / "icon.ico").is_file() and not no_qa(readme_path, 1, 107):
        violations.append((readme_path, 1, 107))


def _check_rule_108_ci(root: Path, no_qa: Callable[[Path, int, int], bool], violations: list[tuple[Path, int, int]]) -> None:
    wf_dir = root / ".github" / "workflows"
    if not wf_dir.is_dir():
        return
    ymls = sorted(wf_dir.glob("*.yml"))
    ci_path = wf_dir / "ci.yml"
    for wf_file in ymls:
        if wf_file.name != "ci.yml" and not no_qa(wf_file, 1, 108):
            violations.append((wf_file, 1, 108))
    if not ci_path.is_file() or no_qa(ci_path, 1, 108):
        return
    content = ci_path.read_text(encoding="utf-8", errors="ignore")
    if "push:" not in content or "pull_request:" not in content:
        violations.append((ci_path, 1, 108))
    if "paths-ignore:" in content:
        violations.append((ci_path, _line_of_offset(content, content.index("paths-ignore:")), 108))
    if "claudemd_linter.py" not in content or "link_checker.py" not in content:
        violations.append((ci_path, 1, 108))
    if "action-gh-release" in content:
        if "prerelease: true" in content or "make_latest: true" not in content and 'make_latest: "true"' not in content:
            violations.append((ci_path, _line_of_offset(content, content.index("action-gh-release")), 108))


def _check_rule_109_legal(root: Path, no_qa: Callable[[Path, int, int], bool], violations: list[tuple[Path, int, int]]) -> None:
    lic_path = root / "LICENSE"
    if lic_path.is_file() and not no_qa(lic_path, 1, 109):
        lic_text = lic_path.read_text(encoding="utf-8", errors="ignore")
        if "MIT License" not in lic_text or "Copyright (c) 2026 DontKwo" not in lic_text:
            violations.append((lic_path, 1, 109))

    sec_path = root / "SECURITY.md"
    if sec_path.is_file() and not no_qa(sec_path, 1, 109):
        sec_text = sec_path.read_text(encoding="utf-8", errors="ignore").lower()
        if "main" not in sec_text or "fork" not in sec_text:
            violations.append((sec_path, 1, 109))


def _check_rule_110_cross_platform(root: Path, single_os: str, no_qa: Callable[[Path, int, int], bool], violations: list[tuple[Path, int, int]]) -> None:
    multi_os_docs = [root / "docs" / "UV_INSTALLATION.md", root / "docs" / "OPENFOAM_INSTALLATION.md"]
    if not single_os:
        multi_os_docs.append(root / "docs" / "INSTALLATION.md")
    for doc_path in multi_os_docs:
        if not doc_path.is_file() or no_qa(doc_path, 1, 110):
            continue
        text = doc_path.read_text(encoding="utf-8", errors="ignore")
        for os_heading in ("Windows", "macOS", "Linux"):
            if not re.search(rf"^#{{2,3}}\s+.*{os_heading}\b", text, re.MULTILINE | re.IGNORECASE):
                violations.append((doc_path, 1, 110))
                break


def _check_rule_111_and_112_gui(
    root: Path,
    readme_text: str,
    files: list[Path],
    no_qa: Callable[[Path, int, int], bool],
    violations: list[tuple[Path, int, int]],
) -> None:
    for py_file in files:
        if py_file.suffix != ".py":
            continue
        if any(part in ("tests", "ui_adapters") for part in py_file.parts) or py_file.name == "claudemd_linter.py":
            continue
        try:
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top_mod = alias.name.split(".", 1)[0]
                    if top_mod in DISALLOWED_GUI_IMPORTS and not no_qa(py_file, node.lineno, 111):
                        violations.append((py_file, node.lineno, 111))
            elif isinstance(node, ast.ImportFrom) and node.module:
                top_mod = node.module.split(".", 1)[0]
                if top_mod in DISALLOWED_GUI_IMPORTS and not no_qa(py_file, node.lineno, 111):
                    violations.append((py_file, node.lineno, 111))

    has_desktop = any(ext in readme_text.lower() for ext in (".exe", ".dmg", ".tar.gz", "-macos.zip"))
    if has_desktop:
        ci_path = root / ".github" / "workflows" / "ci.yml"
        if ci_path.is_file() and not no_qa(ci_path, 1, 112):
            ci_text = ci_path.read_text(encoding="utf-8", errors="ignore")
            if "--self-test" not in ci_text and "--configure" not in ci_text:
                violations.append((ci_path, 1, 112))


def detect_repo_standard_issues(
    root: Path,
    files: list[Path],
    active_codes: set[int],
    no_qa: Callable[[Path, int, int], bool],
    violations: list[tuple[Path, int, int]],
) -> None:
    """Evaluate unified repository, README, doc, icon, CI, and GUI Rules 101-112."""
    cfg = load_tools_config(root)
    single_os = getattr(cfg, "single_os", "")
    readme_path = root / "README.md"
    readme_text = readme_path.read_text(encoding="utf-8", errors="ignore") if readme_path.is_file() else ""
    readme_lines = readme_text.splitlines() if readme_text else []

    if 101 in active_codes:
        _check_rule_101_hygiene(root, no_qa, violations)
    if 102 in active_codes and readme_path.is_file():
        _check_rule_102_readme(readme_path, readme_text, readme_lines, no_qa, violations)
    if 103 in active_codes and readme_path.is_file():
        _check_rule_103_readme_leakage(readme_path, readme_lines, no_qa, violations)
    if 104 in active_codes:
        _check_rule_104_circular_docs(root, no_qa, violations)
    if 105 in active_codes and readme_path.is_file():
        _check_rule_105_minimal_downloads(readme_path, readme_text, no_qa, violations)
    if 106 in active_codes or 107 in active_codes:
        _check_rule_106_and_107(root, readme_text, no_qa, violations)
    if 108 in active_codes:
        _check_rule_108_ci(root, no_qa, violations)
    if 109 in active_codes:
        _check_rule_109_legal(root, no_qa, violations)
    if 110 in active_codes:
        _check_rule_110_cross_platform(root, single_os, no_qa, violations)
    if 111 in active_codes or 112 in active_codes:
        _check_rule_111_and_112_gui(root, readme_text, files, no_qa, violations)
