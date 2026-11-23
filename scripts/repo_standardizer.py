"""Audit and scaffold unified README, legal, doc, logo, and CI standards across repositories."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
BLUEPRINT_DIR = REPO_ROOT / "templates" / "repo_blueprint"
LINTER_SCRIPT = REPO_ROOT / "scripts" / "claudemd_linter.py"
LINK_CHECKER_SCRIPT = REPO_ROOT / "scripts" / "link_checker.py"

IGNORED_OWNED_REPOS = {"portfolio", "corpus", "lastbook", "stabileo"}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def discover_project_repos(projects_dir: Path) -> list[Path]:
    """Return sorted git repositories under projects_dir excluding ignored/external clones."""
    repos: list[Path] = []
    for child in sorted(projects_dir.iterdir(), key=lambda p: p.name.lower()):
        if not child.is_dir() or child.name in IGNORED_OWNED_REPOS:
            continue
        if (child / ".git").exists():
            repos.append(child)
    return repos


def check_repo_standard_compliance(repo_dir: Path) -> dict[str, Any]:
    """Inspect one repository for required files, dual branding, license, and workflow compliance."""
    required_files = [
        "README.md",
        "LICENSE",
        "SECURITY.md",
        "THIRD_PARTY_NOTICES.md",
        "AGENTS.md",
        "docs/USER_GUIDE.md",
        "docs/DEVELOPMENT.md",
        ".github/workflows/ci.yml",
        "assets/logo.png",
        "assets/icon.png",
    ]
    missing = [rel for rel in required_files if not (repo_dir / rel).is_file()]
    banned_root = [
        name
        for name in ("PLAN.md", "DESIGN.md", "DECISIONS.md", "COPYRIGHT", "NOTICES.md", "REQUIREMENTS_TRACEABILITY.md", "tasks.json")
        if (repo_dir / name).exists()
    ]
    license_ok = False
    lic_path = repo_dir / "LICENSE"
    if lic_path.is_file():
        lic_txt = lic_path.read_text(encoding="utf-8", errors="ignore")
        license_ok = "MIT License" in lic_txt and "DontKwo" in lic_txt

    dual_brand_ok = False
    logo_path = repo_dir / "assets" / "logo.png"
    icon_path = repo_dir / "assets" / "icon.png"
    if logo_path.is_file() and icon_path.is_file():
        dual_brand_ok = _sha256(logo_path) != _sha256(icon_path)

    screenshots = list((repo_dir / "assets" / "screenshots").glob("*.png")) if (repo_dir / "assets" / "screenshots").is_dir() else []

    return {
        "name": repo_dir.name,
        "missing": missing,
        "banned_root": banned_root,
        "license_mit": license_ok,
        "dual_brand": dual_brand_ok,
        "screenshots": len(screenshots),
        "compliant": not missing and not banned_root and license_ok and dual_brand_ok and len(screenshots) > 0,
    }


def standardize_repo(repo_dir: Path, app_name: str, dry_run: bool = False) -> list[str]:
    """Scaffold missing MIT LICENSE, SECURITY.md, and Installation guides from repo_blueprint."""
    actions: list[str] = []
    repo_slug = repo_dir.name
    replacements = {
        "<Repo>": repo_slug,
        "<AppName>": app_name,
    }

    def render(template_name: str) -> str:
        content = (BLUEPRINT_DIR / template_name).read_text(encoding="utf-8")
        for placeholder, value in replacements.items():
            content = content.replace(placeholder, value)
        return content

    license_dest = repo_dir / "LICENSE"
    mit_text = (BLUEPRINT_DIR / "LICENSE_MIT.txt").read_text(encoding="utf-8")
    if not license_dest.is_file() or license_dest.read_text(encoding="utf-8", errors="ignore") != mit_text:
        actions.append("Write LICENSE (MIT)")
        if not dry_run:
            license_dest.write_text(mit_text, encoding="utf-8")

    security_dest = repo_dir / "SECURITY.md"
    sec_text = render("SECURITY_TEMPLATE.md")
    if not security_dest.is_file():
        actions.append("Create SECURITY.md")
        if not dry_run:
            security_dest.write_text(sec_text, encoding="utf-8")

    readme_dest = repo_dir / "README.md"
    if not readme_dest.is_file():
        actions.append("Create README.md from blueprint")
        if not dry_run:
            readme_dest.write_text(render("README_TEMPLATE.md"), encoding="utf-8")

    docs_dir = repo_dir / "docs"
    if not dry_run:
        docs_dir.mkdir(parents=True, exist_ok=True)

    install_dest = docs_dir / "INSTALLATION.md"
    if not install_dest.is_file():
        actions.append("Create docs/INSTALLATION.md")
        if not dry_run:
            install_dest.write_text(render("INSTALLATION.md"), encoding="utf-8")

    readme_text = readme_dest.read_text(encoding="utf-8", errors="ignore") if readme_dest.is_file() else ""
    if ".apk" in readme_text.lower() or (repo_dir / "android").is_dir() or (repo_dir / "app" / "build.gradle.kts").is_file():
        apk_dest = docs_dir / "APK_INSTALLATION.md"
        if not apk_dest.is_file():
            actions.append("Create docs/APK_INSTALLATION.md")
            if not dry_run:
                apk_dest.write_text(render("APK_INSTALLATION.md"), encoding="utf-8")

    if (repo_dir / "pyproject.toml").is_file() or "uv run" in ((repo_dir / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8", errors="ignore") if (repo_dir / ".github" / "workflows" / "ci.yml").is_file() else ""):
        uv_dest = docs_dir / "UV_INSTALLATION.md"
        if not uv_dest.is_file():
            actions.append("Create docs/UV_INSTALLATION.md")
            if not dry_run:
                uv_dest.write_text(render("UV_INSTALLATION.md"), encoding="utf-8")

    return actions


def _fetch_live_github_status(repo_slug: str, owner: str = "DontKwo") -> tuple[str, str]:
    """Query latest CI conclusion and latest release tag/assets via gh CLI."""
    if not shutil.which("gh"):
        return "N/A", "N/A"
    ci_state = "N/A"
    rel_state = "N/A"
    full_repo = f"{owner}/{repo_slug}"
    run_res = subprocess.run(
        ["gh", "run", "list", "-R", full_repo, "--limit", "1", "--json", "conclusion,status"],
        capture_output=True,
        text=True,
        check=False,
    )
    if run_res.returncode == 0 and run_res.stdout.strip():
        try:
            runs = json.loads(run_res.stdout)
            if runs:
                ci_state = str(runs[0].get("conclusion") or runs[0].get("status") or "unknown")
        except json.JSONDecodeError:
            ci_state = "ERR"

    rel_res = subprocess.run(
        ["gh", "release", "view", "-R", full_repo, "--json", "tagName,assets"],
        capture_output=True,
        text=True,
        check=False,
    )
    if rel_res.returncode == 0 and rel_res.stdout.strip():
        try:
            rel_data = json.loads(rel_res.stdout)
            tag_name = str(rel_data.get("tagName") or "none")
            asset_count = len(rel_data.get("assets", []))
            rel_state = f"{tag_name} ({asset_count})"
        except json.JSONDecodeError:
            rel_state = "ERR"
    return ci_state, rel_state


def init_repo(repo_dir: Path, app_name: str, dry_run: bool = False) -> list[str]:
    """Initialize a complete repository structure conforming to Rules 101-112."""
    actions = standardize_repo(repo_dir, app_name, dry_run=dry_run)
    repo_slug = repo_dir.name
    ci_template = (BLUEPRINT_DIR / "ci-template.yml").read_text(encoding="utf-8")
    rendered_ci = ci_template.replace("<AppName>", app_name).replace("<Repo>", repo_slug)

    starter_files: dict[str, str] = {
        ".aitools.toml": (
            '[linter]\nprofile = "strict"\nlevel = "strict"\ndiff_only = true\n'
            'ui_evidence = "tests/ui_evidence.json"\n\n[ui]\nframeworks = ["web"]\n'
        ),
        "AGENTS.md": f"# AI Agent Reference\n\nRepository instructions for {app_name}.\n",
        "THIRD_PARTY_NOTICES.md": f"# Third-Party Notices\n\nAttributions for {app_name} dependencies.\n",
        "docs/USER_GUIDE.md": (
            f"# User Guide\n\nDownload {app_name} from [Latest Releases]"
            f"(https://github.com/DontKwo/{repo_slug}/releases/latest).\n\n"
            "## Related Documentation\n\n"
            "- [Project Overview](../README.md)\n"
            "- [Desktop Installation Guide](INSTALLATION.md)\n"
            "- [Security Policy](../SECURITY.md)\n"
        ),
        "docs/DEVELOPMENT.md": (
            f"# Developer Guide\n\nLocal build and test workflows for {app_name}.\n\n"
            "## Related Documentation\n\n"
            "- [Project Overview](../README.md)\n"
            "- [User Guide](USER_GUIDE.md)\n"
            "- [Security Policy](../SECURITY.md)\n"
        ),
        "docs/FAQ.md": (
            f"# Frequently Asked Questions\n\nCommon questions for {app_name}.\n\n"
            "## Related Documentation\n\n"
            "- [Project Overview](../README.md)\n"
            "- [User Guide](USER_GUIDE.md)\n"
            "- [Security Policy](../SECURITY.md)\n"
        ),
        ".github/workflows/ci.yml": rendered_ci,
    }

    for rel_path, content in starter_files.items():
        dest = repo_dir / rel_path
        if not dest.is_file():
            actions.append(f"Create {rel_path}")
            if not dry_run:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(content, encoding="utf-8")
    return actions


def run_status_all(projects_dir: Path, run_linter: bool = True, as_json: bool = False, check_live: bool = False) -> int:
    """Print cross-repository unification compliance table across all owned repositories."""
    repos = discover_project_repos(projects_dir)
    rows: list[dict[str, Any]] = []
    for repo_dir in repos:
        info = check_repo_standard_compliance(repo_dir)
        lint_status = "SKIP"
        link_status = "SKIP"
        if run_linter:
            runner = ["uv", "run", "--no-project", "python"] if shutil.which("uv") else [sys.executable]
            lint_res = subprocess.run(runner + [str(LINTER_SCRIPT), ".", "--level", "strict", "--full", "--no-cache"], cwd=repo_dir, capture_output=True, text=True, check=False)
            lint_status = "CLEAN" if lint_res.returncode == 0 else "FAIL"
            link_res = subprocess.run(runner + [str(LINK_CHECKER_SCRIPT), "."], cwd=repo_dir, capture_output=True, text=True, check=False)
            link_status = "OK" if link_res.returncode == 0 else "FAIL"
        info["lint"] = lint_status
        info["links"] = link_status
        if check_live:
            ci_state, rel_state = _fetch_live_github_status(repo_dir.name)
            info["ci"] = ci_state
            info["release"] = rel_state
        rows.append(info)

    if as_json:
        print(json.dumps(rows, indent=2))  # noqa: 25
    else:
        header = f"{'Repository':<20} {'MIT':<5} {'Brand':<6} {'Shots':<6} {'Lint':<6} {'Links':<6}"
        if check_live:
            header += f" {'CI':<10} {'Release':<14}"
        header += " Missing/Root Issues"
        print(header)  # noqa: 25
        print("-" * (118 if check_live else 92))  # noqa: 25
        for row in rows:
            issues = ", ".join(row["missing"] + [f"BANNED:{item}" for item in row["banned_root"]]) or "None"
            line = (
                f"{row['name']:<20} "
                f"{'YES' if row['license_mit'] else 'NO':<5} "
                f"{'YES' if row['dual_brand'] else 'NO':<6} "
                f"{row['screenshots']:<6} "
                f"{row['lint']:<6} "
                f"{row['links']:<6}"
            )
            if check_live:
                line += f" {row.get('ci', 'N/A'):<10} {row.get('release', 'N/A'):<14}"
            line += f" {issues}"
            print(line)  # noqa: 25
    return 0 if all(item["compliant"] and item["lint"] in ("CLEAN", "SKIP") and item["links"] in ("OK", "SKIP") for item in rows) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Standardize or audit repositories against the unified blueprint.")
    sub = parser.add_subparsers(dest="cmd")

    std_p = sub.add_parser("standardize", help="Scaffold missing standard files in a target repo")
    std_p.add_argument("target", nargs="?", default=".")
    std_p.add_argument("--app-name", default="")
    std_p.add_argument("--dry-run", action="store_true")

    init_p = sub.add_parser("init-repo", help="Initialize full standard scaffold, docs, and CI workflow in a repo")
    init_p.add_argument("target", nargs="?", default=".")
    init_p.add_argument("--app-name", default="")
    init_p.add_argument("--dry-run", action="store_true")

    stat_p = sub.add_parser("status-all", help="Audit all repositories in parent projects directory")
    stat_p.add_argument("--projects-dir", type=Path, default=REPO_ROOT.parent)
    stat_p.add_argument("--no-lint", action="store_true")
    stat_p.add_argument("--live", action="store_true", help="Include live GitHub CI and release status")
    stat_p.add_argument("--json", action="store_true")

    args = parser.parse_args()
    if args.cmd == "status-all":
        return run_status_all(args.projects_dir, run_linter=not args.no_lint, as_json=args.json, check_live=args.live)

    target_dir = Path(getattr(args, "target", ".")).resolve()
    app_name = getattr(args, "app_name", "") or target_dir.name
    if args.cmd == "init-repo":
        actions = init_repo(target_dir, app_name, dry_run=getattr(args, "dry_run", False))
    else:
        actions = standardize_repo(target_dir, app_name, dry_run=getattr(args, "dry_run", False))
    for action in actions:
        print(f"[+] {action}")  # noqa: 25
    if not actions:
        print("[OK] Target repository already has all scaffolded files.")  # noqa: 25
    return 0


if __name__ == "__main__":
    sys.exit(main())
