"""Agent skills manager: discovery, multi-editor installation, toggleability, and sync."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from tools_config import AiToolsConfig, load_tools_config, save_tools_config  # noqa: 12
from utils import get_user_home  # noqa: 12


@dataclass
class SkillInfo:
    name: str
    description: str
    path: Path
    user_invoked: bool = False


def _read_frontmatter_lines(skill_md_path: Path) -> list[str]:
    if not skill_md_path.is_file():
        return []
    try:
        content = skill_md_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    if not content.startswith("---"):
        return []
    parts = content.split("---", 2)
    if len(parts) < 3:
        return []
    return parts[1].splitlines()


def is_user_invoked_skill(skill_md_path: Path) -> bool:
    for line in _read_frontmatter_lines(skill_md_path):
        trimmed = line.strip()
        if trimmed.startswith("disable-model-invocation:"):
            raw_val = trimmed.split("disable-model-invocation:", 1)[1].strip().lower()
            return raw_val == "true"
    return False


def parse_skill_metadata(skill_md_path: Path) -> str:
    fm_lines = _read_frontmatter_lines(skill_md_path)
    if not fm_lines:
        return ""

    desc_lines: list[str] = []
    capture_desc = False

    for line in fm_lines:
        trimmed = line.strip()
        if trimmed.startswith("description:"):
            capture_desc = True
            desc_val = trimmed.split("description:", 1)[1].strip()
            if desc_val and desc_val not in (">-", ">", "|"):
                desc_lines.append(desc_val)
        elif capture_desc:
            if trimmed.startswith(("name:", "tags:", "disable-model-invocation:")) or (
                line and not line.startswith(" ")
            ):
                break
            if trimmed:
                desc_lines.append(trimmed)

    raw_description = " ".join(desc_lines)
    return raw_description.replace("  ", " ").strip()


def list_available_skills(repo_root: Path) -> list[SkillInfo]:
    source_dir = repo_root / "skills"
    if not source_dir.is_dir():
        return []

    results: list[SkillInfo] = []
    for entry in sorted(source_dir.iterdir()):
        if not entry.is_dir():
            continue
        skill_md = entry / "SKILL.md"
        desc = parse_skill_metadata(skill_md) if skill_md.is_file() else "No description available."
        user_only = is_user_invoked_skill(skill_md) if skill_md.is_file() else False
        results.append(SkillInfo(name=entry.name, description=desc, path=entry, user_invoked=user_only))

    return results


def get_tool_skill_dirs(home: Path, ws: Path, scope: str = "both") -> dict[str, list[Path]]:
    dirs: dict[str, list[Path]] = {
        "antigravity": [],
        "agents": [],
        "claude": [],
        "cursor": [],
        "windsurf": [],
        "cline": [],
        "codex": [],
    }

    if scope in ("global", "both"):
        dirs["antigravity"].append(home / ".gemini" / "antigravity" / "skills")
        dirs["agents"].append(home / ".agents" / "skills")
        dirs["claude"].append(home / ".claude" / "skills")
        dirs["cursor"].append(home / ".cursor" / "skills")
        dirs["windsurf"].append(home / ".codeium" / "windsurf" / "skills")
        dirs["cline"].append(home / ".cline" / "skills")
        dirs["codex"].append(home / ".codex" / "skills")

    if scope in ("workspace", "both"):
        dirs["antigravity"].append(ws / ".agent" / "skills")
        dirs["agents"].append(ws / ".agents" / "skills")
        dirs["claude"].append(ws / ".claude" / "skills")
        dirs["cursor"].append(ws / ".cursor" / "skills")
        dirs["windsurf"].append(ws / ".windsurf" / "skills")
        dirs["cline"].append(ws / ".cline" / "skills")
        dirs["codex"].append(ws / ".codex" / "skills")

    return dirs


def get_skill_status(
    repo_root: Path,
    home: Path,
    ws: Path | None = None,
    tools: list[str] | None = None,
    scope: str = "both",
) -> dict[str, dict[str, bool]]:
    active_ws = ws or Path.cwd()
    available = list_available_skills(repo_root)
    tool_dirs = get_tool_skill_dirs(home, active_ws, scope=scope)
    check_tools = tools or list(tool_dirs.keys())

    status: dict[str, dict[str, bool]] = {}
    for skill in available:
        status[skill.name] = {}
        for tool_name in check_tools:
            paths = tool_dirs.get(tool_name, [])
            installed = False
            for target_dir in paths:
                target_skill_md = target_dir / skill.name / "SKILL.md"
                if target_skill_md.is_file():
                    installed = True
                    break
            status[skill.name][tool_name] = installed

    return status


def install_single_skill(source_dir: Path, target_dir: Path, dry_run: bool = False, link: bool = False) -> None:
    dest_path = target_dir / source_dir.name
    if source_dir.resolve() == dest_path.resolve():
        return
    if dry_run:
        return
    target_dir.mkdir(parents=True, exist_ok=True)
    if link:
        if dest_path.is_symlink():
            dest_path.unlink()
        elif dest_path.exists():
            shutil.rmtree(dest_path, ignore_errors=True)
        try:
            os.symlink(source_dir.resolve(), dest_path, target_is_directory=True)
            return
        except OSError:
            shutil.copytree(source_dir, dest_path, dirs_exist_ok=True)
            return
    if dest_path.is_symlink():
        dest_path.unlink()
    shutil.copytree(source_dir, dest_path, dirs_exist_ok=True)


def remove_single_skill(skill_name: str, target_dir: Path, dry_run: bool = False) -> bool:
    dest_path = target_dir / skill_name
    if not dest_path.exists() and not dest_path.is_symlink():
        return False
    if not dry_run:
        if dest_path.is_symlink():
            dest_path.unlink()
        else:
            shutil.rmtree(dest_path, ignore_errors=True)
    return True


def format_display_name(skill_name: str) -> str:
    acronyms = {"tdd": "TDD", "ux": "UX", "aitools": "AI Tools", "ai": "AI", "pr": "PR"}
    parts = [acronyms.get(part.lower(), part.capitalize()) for part in skill_name.split("-")]
    return " ".join(parts)


def ensure_openai_yaml(skill_dir: Path, display_name: str, short_desc: str, user_invoked: bool) -> Path:
    agents_dir = skill_dir / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    escaped_name = display_name.replace('"', '\\"')
    short_line = short_desc.split(".", 1)[0].strip()
    if len(short_line) > 80:
        short_line = short_line[:77].rstrip() + "..."
    escaped_desc = short_line.replace('"', '\\"')
    lines = [
        "interface:",
        f'  display_name: "{escaped_name}"',
        f'  short_description: "{escaped_desc}"',
    ]
    if user_invoked:
        lines.extend(["policy:", "  allow_implicit_invocation: false"])
    yaml_path = agents_dir / "openai.yaml"
    yaml_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return yaml_path


def sync_skills(
    repo_root: Path,
    home: Path,
    ws: Path,
    config: AiToolsConfig,
    scope: str = "both",
    dry_run: bool = False,
    link: bool = False,
) -> dict[str, int]:
    available = list_available_skills(repo_root)
    tool_dirs = get_tool_skill_dirs(home, ws, scope=scope)

    installed_count = 0
    removed_count = 0

    target_tools = [tool for tool in config.skill_targets if tool in tool_dirs]

    for tool_name in target_tools:
        for dest_root in tool_dirs[tool_name]:
            for skill in available:
                is_enabled = config.is_skill_enabled(skill.name)
                if is_enabled:
                    install_single_skill(skill.path, dest_root, dry_run=dry_run, link=link)
                    installed_count += 1
                else:
                    did_remove = remove_single_skill(skill.name, dest_root, dry_run=dry_run)
                    if did_remove:
                        removed_count += 1

    return {"installed": installed_count, "removed": removed_count}


def toggle_skill_in_config(skill_name: str, enable: bool, config_path: Path | None = None) -> bool:
    cfg = load_tools_config(config_path)
    target_path = cfg.config_path or config_path or (Path.cwd() / ".aitools.toml")

    if enable:
        if skill_name in cfg.disabled_skills:
            cfg.disabled_skills.remove(skill_name)
        if cfg.enabled_skills and skill_name not in cfg.enabled_skills:
            cfg.enabled_skills.append(skill_name)
    else:
        if skill_name not in cfg.disabled_skills:
            cfg.disabled_skills.append(skill_name)
        if skill_name in cfg.enabled_skills:
            cfg.enabled_skills.remove(skill_name)

    save_tools_config(target_path, cfg)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage agent skills across AI editors.")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("list", help="List all available skills with descriptions.")

    status_parser = subparsers.add_parser("status", help="Show skill installation status across editors.")
    status_parser.add_argument("--tools", help="Comma-separated list of tools to check.")
    status_parser.add_argument("--scope", choices=["global", "workspace", "both"], default="both")

    enable_parser = subparsers.add_parser("enable", help="Enable a skill and sync across editors.")
    enable_parser.add_argument("skill", help="Name of skill to enable.")
    enable_parser.add_argument("--config", help="Path to .aitools.toml configuration file.")

    disable_parser = subparsers.add_parser("disable", help="Disable a skill and sync across editors.")
    disable_parser.add_argument("skill", help="Name of skill to disable.")
    disable_parser.add_argument("--config", help="Path to .aitools.toml configuration file.")

    sync_parser = subparsers.add_parser("sync", help="Synchronize skills based on current configuration.")
    sync_parser.add_argument("--scope", choices=["global", "workspace", "both"], default="both")
    sync_parser.add_argument("--workspace", help="Path to workspace root.")
    sync_parser.add_argument("--dry-run", action="store_true", help="Preview sync without making changes.")
    sync_parser.add_argument("--link", action="store_true", help="Symlink skills instead of copying files.")

    args = parser.parse_args()

    home = get_user_home()
    ws = Path(args.workspace).resolve() if getattr(args, "workspace", None) else Path.cwd()

    if args.command == "list":
        skills = list_available_skills(REPO_ROOT)
        print(f"Available Skills ({len(skills)} total):\n")
        for sk in skills:
            mode = "[user]" if sk.user_invoked else "[model]"
            print(f"  * {sk.name:<32} {mode:<8} {sk.description[:72]}")
        return

    if args.command == "status":
        selected_tools = [t.strip() for t in args.tools.split(",")] if args.tools else None
        status = get_skill_status(REPO_ROOT, home, ws=ws, tools=selected_tools, scope=args.scope)
        tools_list = selected_tools or ["antigravity", "agents", "claude", "cursor", "windsurf", "cline", "codex"]

        header = f"{'Skill Name':<32} " + " ".join(f"{t[:8]:<8}" for t in tools_list)
        print(header)
        print("-" * len(header))
        for skill_name, tool_map in status.items():
            row = f"{skill_name:<32} " + " ".join(f"{('OK' if tool_map.get(t) else '-'):<8}" for t in tools_list)
            print(row)
        return

    if args.command == "enable":
        cfg_path = Path(args.config) if args.config else None
        toggle_skill_in_config(args.skill, enable=True, config_path=cfg_path)
        cfg = load_tools_config(cfg_path)
        res = sync_skills(REPO_ROOT, home, ws, cfg)
        print(f"[OK] Enabled skill '{args.skill}'. Synced across editors (installed: {res['installed']}).")
        return

    if args.command == "disable":
        cfg_path = Path(args.config) if args.config else None
        toggle_skill_in_config(args.skill, enable=False, config_path=cfg_path)
        cfg = load_tools_config(cfg_path)
        res = sync_skills(REPO_ROOT, home, ws, cfg)
        print(f"[OK] Disabled skill '{args.skill}'. Removed from editors (removed: {res['removed']}).")
        return

    if args.command == "sync":
        cfg = load_tools_config()
        res = sync_skills(REPO_ROOT, home, ws, cfg, scope=args.scope, dry_run=args.dry_run, link=args.link)
        prefix = "[DRY-RUN] " if args.dry_run else "[OK] "
        print(f"{prefix}Skills synchronized: {res['installed']} installed, {res['removed']} removed.")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
