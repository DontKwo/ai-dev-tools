#!/usr/bin/env python3
"""Environment Doctor & Self-Healing Path Synchronizer.
Inspects all AI instruction configurations, verifies toolpaths, checks dependencies,
and repairs broken/stale paths across Claude, Cursor, Cline, Antigravity, and Codex.
"""

import argparse
import importlib.util
import json
import re

import shutil
import subprocess
import sys
from typing import Union
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from configure import configure_skills
from custom_linter import load_custom_linter_config
from skills_manager import get_tool_skill_dirs
from tools_config import load_tools_config
from utils import IS_WINDOWS, detect_android_release_issues, format_command_path, get_user_home

REPO_ROOT = Path(__file__).resolve().parent.parent
LINTER_SCRIPT = REPO_ROOT / "scripts" / "claudemd_linter.py"
ENGINEERING_PATH = REPO_ROOT / "templates" / "ENGINEERING_RULES.md"
PYTHON_RULES_PATH = REPO_ROOT / "templates" / "PYTHON_RULES.md"



def check_ui_helpers(repo_root: Path) -> dict[str, bool]:
    ui_templates = repo_root / "templates" / "ui_audit"
    frameworks = ("pyqt", "web", "android", "flutter", "ios", "tkinter", "wxpython", "kivy", "textual", "dotnet")
    return {fw: (ui_templates / fw).is_dir() for fw in frameworks}


def _inspect_release_workflow(repo_root: Path, release_file: Path, info: dict[str, Union[bool, list[str]]]) -> None:
    try:
        content = release_file.read_text(encoding="utf-8")
    except OSError as err:
        info["warnings"].append(f"Failed to read release.yml: {err}")
        return

    warnings_list: list[str] = info["warnings"]  # type: ignore[assignment]
    ok_list: list[str] = info["ok"]  # type: ignore[assignment]

    has_push = "push:" in content
    has_pull_request = "pull_request:" in content
    if has_push and has_pull_request:
        ok_list.append("release.yml triggers on both push and pull_request")
    else:
        if not has_push:
            warnings_list.append("release.yml: missing 'push:' trigger")
        if not has_pull_request:
            warnings_list.append("release.yml: missing 'pull_request:' trigger")

    if re.search(r"tag_name:.*['\"]latest['\"]", content):
        warnings_list.append(
            "release.yml: static 'latest' tag_name overwrites release in-place instead of publishing versioned releases"
        )

    if (repo_root / "android").is_dir():
        if "assembleRelease" in content or ".apk" in content:
            ok_list.append("Android project has native APK build step in release workflow")
        else:
            warnings_list.append("Android project release workflow missing native APK compilation")
        android_issues = detect_android_release_issues(repo_root)
        if android_issues:
            for _, _, msg in android_issues:
                warnings_list.append(msg)
        else:
            ok_list.append("Android release signing and manifest security settings look clean")

    has_tauri_or_win_installer = (repo_root / "src-tauri").is_dir() or ".exe" in content or ".msi" in content
    if has_tauri_or_win_installer:
        has_exe = ".exe" in content
        has_msi = ".msi" in content
        if has_exe and has_msi:
            ok_list.append("release.yml references both .exe and .msi installer artifacts")
        else:
            if not has_exe:
                warnings_list.append("release.yml: missing .exe installer artifact pattern")
            if not has_msi:
                warnings_list.append("release.yml: missing .msi installer artifact pattern")

    pkg_file = repo_root / "package.json"
    if pkg_file.is_file():
        try:
            pkg_version = str(json.loads(pkg_file.read_text(encoding="utf-8")).get("version", "")).strip()
        except (OSError, json.JSONDecodeError):
            pkg_version = ""
        if pkg_version:
            ver_matches = re.findall(
                r"[-_](\d+\.\d+\.\d+)(?:[-_][^/\s'\"]*)?\.(?:exe|msi|dmg|AppImage|apk)",
                content,
            )
            mismatched = [ver for ver in ver_matches if ver != pkg_version]
            if mismatched:
                warnings_list.append(
                    f"release.yml: hardcoded installer version {', '.join(sorted(set(mismatched)))} mismatches package.json {pkg_version}"
                )
            elif ver_matches:
                ok_list.append(f"release.yml installer artifact version matches package.json ({pkg_version})")


def check_ci_workflows(repo_root: Path) -> dict[str, Union[bool, list[str]]]:
    workflow_dir = repo_root / ".github" / "workflows"
    info: dict[str, Union[bool, list[str]]] = {
        "has_workflows": workflow_dir.is_dir(),
        "warnings": [],
        "ok": []
    }
    if not workflow_dir.is_dir():
        return info

    pages_file = workflow_dir / "pages.yml"
    if pages_file.is_file():
        try:
            content = pages_file.read_text(encoding="utf-8")
            if "actions/configure-pages" in content and "enablement: true" in content:
                info["ok"].append("GitHub Pages workflow configured with automated enablement")  # type: ignore[union-attr]
            elif "actions/configure-pages" in content:
                info["warnings"].append("pages.yml: actions/configure-pages missing 'enablement: true'")  # type: ignore[union-attr]
        except OSError as err:
            info["warnings"].append(f"Failed to read pages.yml: {err}")  # type: ignore[union-attr]

    release_file = workflow_dir / "release.yml"
    if release_file.is_file():
        _inspect_release_workflow(repo_root, release_file, info)

    return info


def check_git_tracking(repo_root: Path) -> dict[str, Union[str, bool]]:
    info: dict[str, Union[str, bool]] = {"has_git": False, "is_repo": False, "has_tracking": False, "branch": ""}
    git_bin = shutil.which("git")
    if not git_bin:
        return info

    info["has_git"] = True
    try:
        subprocess.run(
            [git_bin, "rev-parse", "--is-inside-work-tree"],
            cwd=str(repo_root),
            capture_output=True,
            check=True,
            text=True,
        )
        info["is_repo"] = True

        result = subprocess.run(
            [git_bin, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            info["has_tracking"] = True
            info["branch"] = result.stdout.strip()
    except (subprocess.CalledProcessError, OSError):
        return info

    return info


def check_python_version(repo_root: Path) -> dict[str, Union[str, bool]]:
    info: dict[str, Union[str, bool]] = {"has_toml": False, "requires_python": "", "meets_req": False}
    toml_path = repo_root / "pyproject.toml"
    if not toml_path.is_file():
        return info

    info["has_toml"] = True
    try:
        content = toml_path.read_text(encoding="utf-8")
        match = re.search(r'requires-python\s*=\s*[\"\']([^\"\']+)[\"\']', content)
        if match:
            req = match.group(1)
            info["requires_python"] = req

            ver_match = re.search(r'>=\s*(\d+)\.(\d+)', req)
            if ver_match:
                req_major, req_minor = int(ver_match.group(1)), int(ver_match.group(2))
                info["meets_req"] = (sys.version_info.major, sys.version_info.minor) >= (req_major, req_minor)
            else:
                info["meets_req"] = True
        else:
            info["meets_req"] = True
    except OSError:
        return info

    return info


def inspect_mcp_config(mcp_path: Path) -> dict:
    info = {
        "exists": mcp_path.is_file(),
        "is_registered": False,
        "corrupted": False,
        "command_valid": False,
        "script_valid": False,
    }
    if not info["exists"]:
        return info

    try:
        mcp_data = json.loads(mcp_path.read_text(encoding="utf-8"))
        dev_tools = mcp_data.get("mcpServers", {}).get("ai-dev-tools")
        if dev_tools:
            info["is_registered"] = True

            cmd = dev_tools.get("command")
            if cmd and Path(cmd).is_file():
                info["command_valid"] = True

            args = dev_tools.get("args", [])
            for arg in args:
                if arg.endswith("server.py"):
                    if Path(arg).is_file():
                        info["script_valid"] = True
                    break
    except Exception:
        info["corrupted"] = True

    return info


def check_installed_skills(repo_root: Path, home: Path, target_tool: str = "antigravity") -> dict[str, bool]:
    installed_status: dict[str, bool] = {}
    source_skills = repo_root / "skills"
    tool_dirs = get_tool_skill_dirs(home, repo_root, scope="global")
    dest_candidates = tool_dirs.get(target_tool, [home / ".gemini" / "antigravity" / "skills"])
    dest_dir = dest_candidates[0] if dest_candidates else (home / ".gemini" / "antigravity" / "skills")

    if not source_skills.is_dir():
        return installed_status

    for skill_dir in source_skills.iterdir():
        if not skill_dir.is_dir():
            continue

        skill_name = skill_dir.name
        dest_skill_dir = dest_dir / skill_name
        dest_skill_md = dest_skill_dir / "SKILL.md"

        installed_status[skill_name] = dest_skill_dir.is_dir() and dest_skill_md.is_file()

    return installed_status


def check_tools_config(root: Path) -> dict[str, Union[str, bool, int, list[str], None]]:
    cfg = load_tools_config(root)
    return {
        "has_config": cfg.config_path is not None,
        "path": str(cfg.config_path) if cfg.config_path else "",
        "level": cfg.linter_level,
        "skill_targets": cfg.skill_targets,
        "disabled_count": len(cfg.disabled_skills),
    }


def get_all_config_paths() -> list[tuple[str, Path]]:
    home = get_user_home()
    return [
        ("Claude Code", home / ".claude" / "CLAUDE.md"),
        ("Cursor IDE", home / ".cursor" / "rules" / "developer-rules.mdc"),
        ("Cursor IDE (.cursorrules)", home / ".cursorrules"),
        ("Cline / Roo Code", home / ".clinerules"),
        ("Google Antigravity", home / ".gemini" / "antigravity" / "rules" / "user_rules.md"),
        ("Google Antigravity (Agents)", home / ".gemini" / "config" / "AGENTS.md"),
        ("OpenAI Codex", home / ".codex" / "instructions.md"),
        ("Windsurf IDE", home / ".windsurfrules"),
        ("Aider CLI", home / ".aider.conventions.md"),
    ]


def inspect_config_file(name: str, path: Path) -> dict:
    info = {
        "name": name,
        "path": path,
        "exists": path.is_file(),
        "has_linter_ref": False,
        "linter_path_valid": False,
        "extracted_path": None,
        "has_unexpanded_tokens": False,
        "has_stale_ref": False,
    }

    if not path.is_file():
        return info

    try:
        content = path.read_text(encoding="utf-8", errors="replace")
        if any(tok in content for tok in ("{{LINTER_COMMAND}}", "{{ENGINEERING_RULES_PATH}}", "{{PYTHON_RULES_PATH}}")):
            info["has_unexpanded_tokens"] = True

        if "<project_root>" in content or "lint_report.txt" in content:
            info["has_stale_ref"] = True

        pattern = r'(?:uv\s+run\s+--no-project\s+python|python(?:3)?)\s+["\']?([^"\'\n]+claudemd_linter\.py)["\']?'
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            info["has_linter_ref"] = True
            raw_ref = match.group(1).strip()
            home_str = str(get_user_home())
            expanded_ref = raw_ref.replace("%USERPROFILE%", home_str).replace("$HOME", home_str)
            ref_path = Path(expanded_ref).expanduser()
            if not ref_path.is_absolute():
                ref_path = (REPO_ROOT / ref_path).resolve()
            info["extracted_path"] = ref_path
            if ref_path.resolve() != LINTER_SCRIPT.resolve():
                info["has_stale_ref"] = True
            info["linter_path_valid"] = (
                ref_path.is_file() and not info["has_unexpanded_tokens"] and not info["has_stale_ref"]
            )
    except OSError:
        return info

    return info


def heal_config_file(info: dict) -> bool:
    path = info["path"]
    if not path.is_file():
        return False

    try:
        content = path.read_text(encoding="utf-8", errors="replace")
        target_linter_str = format_command_path(LINTER_SCRIPT)
        eng_str = format_command_path(ENGINEERING_PATH)
        py_str = format_command_path(PYTHON_RULES_PATH)

        if shutil.which("uv"):
            new_cmd = f"uv run --no-project python {target_linter_str}"
        else:
            py_bin = "python" if IS_WINDOWS else "python3"
            new_cmd = f"{py_bin} {target_linter_str}"

        pattern = re.compile(
            r'(?:uv\s+run\s+--no-project\s+python|python(?:3)?)\s+["\']?[^"\'\n]+claudemd_linter\.py["\']?',
            re.IGNORECASE,
        )
        new_content = pattern.sub(new_cmd, content)
        new_content = new_content.replace("{{LINTER_COMMAND}}", new_cmd)
        new_content = new_content.replace("{{ENGINEERING_RULES_PATH}}", eng_str)
        new_content = new_content.replace("{{PYTHON_RULES_PATH}}", py_str)
        new_content = new_content.replace("<project_root>", ".")
        new_content = re.sub(
            r"Then read [^\n]*lint_report\.txt in full\.",
            "When violations occur, inspect the report file path printed in terminal output.",
            new_content,
        )
        path.write_text(new_content, encoding="utf-8")
        return True
    except OSError as err:
        print(f"  [!] Failed to heal {path}: {err}")
        return False


def clean_stale_reports_and_cache(dry_run: bool = False) -> int:
    removed_count = 0
    targets = list((REPO_ROOT / "scripts").glob("lint_report*.txt"))
    targets.extend(REPO_ROOT.glob("lint_report*.txt"))
    cache_file = REPO_ROOT / "scripts" / ".lint_cache.json"
    if cache_file.is_file():
        targets.append(cache_file)

    for path in targets:
        if path.is_file():
            if dry_run:
                print(f"  [DRY-RUN] Would remove: {path}")
            else:
                try:
                    path.unlink()
                    print(f"  [+] Removed: {path.name}")
                    removed_count += 1
                except OSError as err:
                    print(f"  [!] Failed to delete {path.name}: {err}")
    return removed_count


def run_diagnostics(auto_heal: bool = False, clean_cache: bool = False, repair: bool = False) -> None:
    print("Developer AI Tools Health & Diagnostic Doctor")
    print(f"Current Repo Root:  {REPO_ROOT}")
    print(f"Current Linter:     {LINTER_SCRIPT}")
    print("")

    # 1. Check Python Environment
    print("[1] Python Runtime:")
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    py_info = check_python_version(REPO_ROOT)

    if py_info["has_toml"] and py_info["requires_python"]:
        req = py_info["requires_python"]
        if py_info["meets_req"]:
            print(f"  [OK] Python {py_ver} (meets project requirement: {req})")
        else:
            print(f"  [FAIL] Python {py_ver} (does not meet project requirement: {req})")
    else:
        if sys.version_info >= (3, 9):
            print(f"  [OK] Python {py_ver} (>= 3.9 requirement met)")
        else:
            print(f"  [FAIL] Python {py_ver} is too old! Please upgrade to Python 3.9+.")

    # 2. Check uv Package Manager
    print("\n[2] uv Package Manager:")
    uv_bin = shutil.which("uv")
    if uv_bin:
        print(f"  [OK] uv executable found at: {uv_bin}")
    else:
        print("  [WARN] uv executable not found in PATH.")

    # 3. Check Git
    print("\n[3] Git Availability:")
    git_info = check_git_tracking(REPO_ROOT)

    if not git_info["has_git"]:
        print("  [WARN] Git executable not found in PATH.")
    elif not git_info["is_repo"]:
        print(f"  [WARN] Git is installed, but {REPO_ROOT.name} is not a git repository.")
    elif git_info["has_tracking"]:
        print(f"  [OK] Git remote tracking branch configured: {git_info['branch']}")
    else:
        print("  [WARN] Git repo has no remote tracking branch. Set up a remote to avoid sync issues.")

    # 4. Check Vulture
    print("\n[4] Optional AST Dependencies:")
    vulture_ok = importlib.util.find_spec("vulture") is not None
    if not vulture_ok and shutil.which("vulture"):
        vulture_ok = True

    if vulture_ok:
        print("  [OK] 'vulture' is installed (used for Rule 21 dead code detection).")
    else:
        print("  [INFO] 'vulture' is not installed. Install with 'uv tool install vulture' if desired.")

    # 5. Check Configured AI Tools
    print("\n[5] Configured AI Tools:")
    configs = get_all_config_paths()
    needs_heal = []

    for name, path in configs:
        info = inspect_config_file(name, path)
        if not info["exists"]:
            print(f"  [-] {name:20}: Not installed ({path.name} not found)")
        elif not info["has_linter_ref"] and not info["has_unexpanded_tokens"]:
            print(f"  [WARN] {name:20}: Installed, but has no claudemd_linter.py instruction")
        elif info["linter_path_valid"]:
            print(f"  [OK] {name:20}: Healthy (points to {info['extracted_path']})")
        else:
            if info["has_unexpanded_tokens"]:
                reason = "Unexpanded template tokens"
            elif info["has_stale_ref"]:
                reason = "Stale report or <project_root> reference"
            else:
                reason = f"Points to missing path: {info['extracted_path']}"
            print(f"  [BROKEN] {name:16}: {reason}")
            info["type"] = "config"
            needs_heal.append(info)

    # 6. Check Antigravity Skills
    print("\n[6] Antigravity Skills Status:")
    home = get_user_home()
    skills_status = check_installed_skills(REPO_ROOT, home)
    missing_skills = False

    if not skills_status:
        print("  [-] No skills found in repository.")
    else:
        for skill_name, is_installed in sorted(skills_status.items()):
            if is_installed:
                print(f"  [OK] {skill_name:20}: Installed")
            else:
                print(f"  [-] {skill_name:20}: Missing")
                missing_skills = True

    if missing_skills and repair:
        print("\nRepairing missing Antigravity Skills...")
        configure_skills(REPO_ROOT, scope="global")
        print("  [+] Repair complete.")

    # 7. Check Configured MCP Servers
    print("\n[7] Configured Model Context Protocol (MCP) Servers:")
    mcp_configs = [
        ("Claude Desktop", home / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json" if IS_WINDOWS else home / ".config" / "Claude" / "claude_desktop_config.json"),  # noqa: 91
        ("Claude Code CLI", home / ".claude.json"),
        ("Cursor IDE", home / ".cursor" / "mcp.json"),
        (
            "Google Antigravity (Config)",
            home / ".gemini" / "config" / "mcp_config.json",
        ),
        (
            "Google Antigravity (App)",
            home / ".gemini" / "antigravity" / "mcp_config.json",
        ),
        ("Windsurf IDE", home / ".codeium" / "windsurf" / "mcp_config.json"),
    ]

    for mcp_name, mcp_path in mcp_configs:
        mcp_info = inspect_mcp_config(mcp_path)
        if not mcp_info["exists"]:
            print(f"  [-] {mcp_name:20}: Not installed ({mcp_path.name} not found)")
        elif mcp_info["corrupted"]:
            print(f"  [WARN] {mcp_name:18}: Corrupted JSON file")
        elif not mcp_info["is_registered"]:
            print(f"  [-] {mcp_name:20}: Present, but ai-dev-tools not registered")
        elif not mcp_info["command_valid"] or not mcp_info["script_valid"]:
            print(f"  [BROKEN] {mcp_name:16}: Registered, but points to missing paths")
            needs_heal.append({"name": mcp_name, "path": mcp_path, "type": "mcp"})
        else:
            print(f"  [OK] {mcp_name:20}: Active (ai-dev-tools registered and valid)")

    # 8. Check UI Audit Test Helpers
    print("\n[8] UI Audit Helpers:")
    ui_status = check_ui_helpers(REPO_ROOT)
    installed_count = sum(1 for v in ui_status.values() if v)
    if installed_count == len(ui_status):
        print(f"  [OK] UI audit helpers installed for all {installed_count} frameworks ({', '.join(ui_status.keys())})")
    else:
        missing = [k for k, v in ui_status.items() if not v]
        print(f"  [WARN] Missing UI audit helper templates for: {', '.join(missing)}")

    # 9. Declarative Configuration
    print("\n[9] Project Configuration (.aitools.toml & linter_custom.yaml):")
    config_info = check_tools_config(REPO_ROOT)
    if config_info["has_config"]:
        print(f"  [OK] Detected: {config_info['path']} (level={config_info['level']})")
    else:
        print("  [INFO] No .aitools.toml detected; using built-in defaults (generate with 'aitools init-config').")
    custom_cfg = load_custom_linter_config(target_root=REPO_ROOT)
    if custom_cfg.loaded_files:
        loaded_names = ", ".join(str(cfg_path) for cfg_path in custom_cfg.loaded_files)
        rule_summary = (
            f"remove={len(custom_cfg.remove)}, "
            f"replace={len(custom_cfg.replace)}, "
            f"allowed_vars={len(custom_cfg.allowed_vars)}, "
            f"banned_vars={len(custom_cfg.banned_vars)}, "
            f"banned_imports={len(custom_cfg.banned_imports)}, "
            f"file_guards={len(custom_cfg.file_guards)}, "
            f"ignore_paths={len(custom_cfg.ignore_paths)}, "
            f"rule_overrides={len(custom_cfg.rule_overrides)}"
        )
        print(f"  [OK] Custom Linter YAML: {loaded_names} ({rule_summary})")
    else:
        print("  [INFO] No linter_custom.yaml active (copy linter_custom.example.yaml to customize rules).")

    # 10. Unified CLI Status
    print("\n[10] Unified CLI Status:")
    aitools_bin = shutil.which("aitools") or shutil.which("aitools.cmd")
    aiui_bin = shutil.which("aiui") or shutil.which("aiui.cmd")
    if aitools_bin:
        print(f"  [OK] 'aitools' found on PATH at: {aitools_bin}")
    else:
        print(f"  [INFO] 'aitools' wrapper available in: {REPO_ROOT / 'bin'}")
    if aiui_bin:
        print(f"  [OK] 'aiui' found on PATH at: {aiui_bin}")
    else:
        print(f"  [INFO] 'aiui' wrapper available in: {REPO_ROOT / 'bin'}")

    # 11. CI/CD Workflow Health & Artifact Parity
    print("\n[11] CI/CD Workflow Health & Artifact Parity:")
    cwd_root = Path.cwd().resolve()
    target_ci_root = cwd_root if (cwd_root / ".github" / "workflows").is_dir() else REPO_ROOT
    ci_info = check_ci_workflows(target_ci_root)
    if not ci_info["has_workflows"]:
        print("  [INFO] No .github/workflows directory detected.")
    else:
        for ok_msg in ci_info["ok"]:
            print(f"  [OK] {ok_msg}")
        for warn_msg in ci_info["warnings"]:
            print(f"  [WARN] {warn_msg}")

    # 12. Healing action
    if needs_heal:
        print(f"\n[!] Found {len(needs_heal)} configuration(s) pointing to stale or missing linter paths.")
        if auto_heal:
            do_heal = True
        else:
            choice = input("    Repair and heal these paths to point to this repository? [Y/n]: ").strip().lower()
            do_heal = choice in ("", "y", "yes")

        if do_heal:
            print("\nHealing configurations...")
            for info in needs_heal:
                if info.get("type") == "config" and heal_config_file(info):
                    print(f"  [+] Repaired: {info['name']} -> {LINTER_SCRIPT}")
                elif info.get("type") == "mcp":
                    print(f"  [!] MCP Repair not yet implemented for {info['name']}")
            print("\n[OK] All broken configurations successfully healed!")
    else:
        print("\n[OK] All installed AI tool configurations are healthy and synchronized.")

    if clean_cache:
        print("\nCleaning lint reports and cache...")
        count = clean_stale_reports_and_cache()
        print(f"[OK] Cleaned {count} file(s).")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run diagnostics and heal stale AI tool paths.")
    parser.add_argument("--heal", action="store_true", help="Automatically heal stale paths without asking")
    parser.add_argument("--clean", action="store_true", help="Remove stale lint reports and .lint_cache.json")
    parser.add_argument("--repair", action="store_true", help="Automated repair to reinstall missing skills")
    args = parser.parse_args()

    run_diagnostics(auto_heal=args.heal, clean_cache=args.clean, repair=args.repair)


if __name__ == "__main__":
    main()
