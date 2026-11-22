"""Applies declarative YAML configuration to setup AI tools, skills, and hooks."""
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import shutil
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

REPO_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from configure import (
    SKILL_BUNDLES,
    _split_frontmatter,
    build_instructions,
    configure_mcp_servers,
    configure_skills,
    get_tool_definitions,
)
from install_hooks import install_hook, uninstall_hook
from tools_config import BUILTIN_PROFILES
from utils import get_user_home
from yaml_utils import load_yaml_file, validate_config_schema

STATE_MANIFEST_FILE = ".adt-state.json"
BEGIN_MARKER = "<!-- BEGIN AI-DEV-TOOLS -->"
END_MARKER = "<!-- END AI-DEV-TOOLS -->"


@dataclass
class RuleActionItem:
    tool_key: str
    target_path: str
    action_type: str
    file_exists: bool
    existing_bytes: int
    data_loss_risk: bool
    risk_description: str
    explanation: str
    content: str
    planned_content: str = ""
    diff: str = ""


@dataclass
class ConfigExecutionPlan:
    workspace_path: str
    scope: str
    write_mode: str
    profile_name: str
    rule_actions: list[RuleActionItem]
    mcp_enabled: bool
    skills_enabled: bool
    skill_bundle: str
    git_hook_enabled: bool
    git_hook_command: str


def validate_workspace_path(target_path: Path, workspace_dir: Path) -> Path:
    resolved_target = target_path.resolve()
    resolved_workspace = workspace_dir.resolve()
    try:
        resolved_target.relative_to(resolved_workspace)
    except ValueError as exc:
        raise ValueError(
            f"Security error: target '{target_path}' escapes workspace boundary '{workspace_dir}'"
        ) from exc
    return resolved_target


def atomic_write_text(dest: Path, content: str, encoding: str = "utf-8") -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    temp_name = f".{dest.name}.adt_tmp_{os.getpid()}_{uuid4().hex[:6]}"
    temp_file = dest.parent / temp_name
    try:
        with open(temp_file, "w", encoding=encoding, newline="") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_file, dest)
    except Exception:
        if temp_file.exists():
            try:
                temp_file.unlink()
            except OSError as cleanup_err:
                _ = cleanup_err
        raise


def create_safe_backup(target_file: Path) -> Path:
    base_backup = target_file.with_suffix(target_file.suffix + ".bak")
    if not base_backup.exists():
        backup_destination = base_backup
    else:
        counter = 1
        while True:
            candidate = target_file.with_name(f"{target_file.name}.bak.{counter}")
            if not candidate.exists():
                backup_destination = candidate
                break
            counter += 1

    shutil.copy2(target_file, backup_destination)
    if backup_destination.stat().st_size != target_file.stat().st_size:
        backup_destination.unlink()
        raise OSError(f"Backup verification failed: byte mismatch on {backup_destination}")
    return backup_destination


def detect_workspace_integrations(workspace_dir: Path) -> dict[str, Any]:
    resolved_workspace = workspace_dir.resolve()
    detected_tools: list[str] = []
    tool_reasons: dict[str, str] = {}

    indicators: list[tuple[str, str, list[str]]] = [
        ("claude", "Found Claude configuration", ["CLAUDE.md", ".claude"]),
        ("cursor", "Found Cursor rules directory", [".cursorrules", ".cursor"]),
        ("antigravity", "Found Antigravity or Agent workspace", ["AGENTS.md", ".agent", ".agents", ".gemini"]),
        ("windsurf", "Found Windsurf configuration", [".windsurfrules", ".windsurf"]),
        ("cline", "Found Cline configuration", [".clinerules", ".cline"]),
        ("codex", "Found Codex configuration", [".codex"]),
        ("copilot", "Found GitHub workflows or Copilot folder", [".github"]),
    ]

    for tool_name, reason_label, marker_names in indicators:
        for marker_name in marker_names:
            if (resolved_workspace / marker_name).exists():
                detected_tools.append(tool_name)
                tool_reasons[tool_name] = f"{reason_label} ({marker_name})"
                break

    has_git = (resolved_workspace / ".git").is_dir()
    is_python = (
        (resolved_workspace / "pyproject.toml").is_file()
        or (resolved_workspace / "requirements.txt").is_file()
        or (resolved_workspace / "setup.py").is_file()
    )

    return {
        "detected_tools": detected_tools,
        "tool_reasons": tool_reasons,
        "has_git": has_git,
        "is_python": is_python,
    }


def calculate_planned_content(
    target_dest: Path,
    instructions_body: str,
    action_type: str,
) -> tuple[str, str, str]:
    frontmatter, body = _split_frontmatter(instructions_body)
    bounded_body = f"{BEGIN_MARKER}\n{body.rstrip()}\n{END_MARKER}"
    full_bounded = f"{frontmatter}{bounded_body}\n"

    if not target_dest.exists():
        existing_text = ""
        planned_text = full_bounded
    else:
        existing_text = target_dest.read_text(encoding="utf-8", errors="replace")
        if action_type == "overwrite":
            planned_text = full_bounded
        elif action_type == "append":
            if BEGIN_MARKER in existing_text and END_MARKER in existing_text:
                pattern = rf"{re.escape(BEGIN_MARKER)}.*?{re.escape(END_MARKER)}"
                planned_text = re.sub(pattern, lambda _m: bounded_body, existing_text, count=1, flags=re.DOTALL)
                if not planned_text.endswith("\n"):
                    planned_text += "\n"
            elif not existing_text.strip():
                planned_text = full_bounded
            elif frontmatter and not _split_frontmatter(existing_text)[0]:
                planned_text = f"{frontmatter}{existing_text.rstrip()}\n\n{bounded_body}\n"
            else:
                planned_text = f"{existing_text.rstrip()}\n\n{bounded_body}\n"
        else:
            planned_text = existing_text

    diff_lines = list(
        difflib.unified_diff(
            existing_text.splitlines(keepends=True),
            planned_text.splitlines(keepends=True),
            fromfile=f"a/{target_dest.name}",
            tofile=f"b/{target_dest.name}",
        )
    )
    diff_text = "".join(diff_lines)
    return existing_text, planned_text, diff_text


def build_plan_from_config(
    config_dict: dict[str, Any],
    workspace_dir: Path,
    home_dir: Path | None = None,
    mode_override: str | None = None,
    tools_override: list[str] | None = None,
    profile_override: str | None = None,
    disable_hooks: bool = False,
    disable_mcp: bool = False,
    disable_skills: bool = False,
    detect_tools: bool = False,
) -> ConfigExecutionPlan:
    user_home = home_dir or get_user_home()
    scope_val = str(config_dict.get("scope", "workspace")).lower()
    active_mode = mode_override or str(config_dict.get("write_mode", "append")).lower()
    if active_mode not in ("append", "overwrite", "skip"):
        active_mode = "append"

    prof_data = config_dict.get("profile", {})
    if isinstance(prof_data, dict):
        prof_name = profile_override or str(prof_data.get("level", "strict"))
        skip_codes = list(prof_data.get("skip_rules", []))
    else:
        prof_name = profile_override or str(prof_data or "strict")
        skip_codes = []

    if prof_name in BUILTIN_PROFILES and not skip_codes:
        skip_codes = list(BUILTIN_PROFILES[prof_name].get("skip", []))

    all_tool_defs = get_tool_definitions(workspace_dir)
    tools_config = config_dict.get("tools", {})

    chosen_tools: list[str] = []
    if tools_override:
        chosen_tools = [tool_id.strip().lower() for tool_id in tools_override if tool_id.strip()]
    elif detect_tools:
        detection_result = detect_workspace_integrations(workspace_dir)
        chosen_tools = detection_result["detected_tools"]
        if not chosen_tools:
            chosen_tools = ["claude", "cursor", "antigravity"]
    elif isinstance(tools_config, dict):
        for tool_name, is_enabled in tools_config.items():
            if is_enabled:
                chosen_tools.append(tool_name.lower())
    elif isinstance(tools_config, list):
        chosen_tools = [str(tool_item).lower() for tool_item in tools_config]
    else:
        chosen_tools = list(all_tool_defs.keys())

    targets_toggle = config_dict.get("targets", {})
    rule_items: list[RuleActionItem] = []

    for tool_key in chosen_tools:
        if tool_key not in all_tool_defs:
            continue
        definition = all_tool_defs[tool_key]
        dest_candidates = definition["global_paths"] if scope_val == "global" else definition["workspace_paths"]

        for target_dest in dest_candidates:
            if isinstance(targets_toggle, dict) and targets_toggle:
                fname_key = target_dest.name.lower().replace(".", "_").replace("-", "_")
                stripped_key = fname_key.strip("_")
                stem_key = stripped_key[:-3] if stripped_key.endswith("_md") else stripped_key
                if (
                    targets_toggle.get(fname_key) is False
                    or targets_toggle.get(stripped_key) is False
                    or targets_toggle.get(stem_key) is False
                ):
                    continue

            exists_flag = target_dest.exists()
            size_val = target_dest.stat().st_size if exists_flag else 0
            instructions_body = build_instructions(
                frontmatter=definition.get("frontmatter", ""),
                workspace=workspace_dir,
            )

            _, planned_text, diff_text = calculate_planned_content(target_dest, instructions_body, active_mode)

            if not exists_flag:
                loss_flag = False
                desc_text = "New file: clean creation with zero data loss."
                expl_text = f"Creates standard instructions for {definition['name']} at {target_dest.name}."
            elif active_mode == "overwrite":
                loss_flag = True
                desc_text = (
                    f"DATA LOSS RISK: {target_dest.name} exists ({size_val} bytes). "
                    f"Overwriting replaces file content. Backup saved to {target_dest.name}.bak."
                )
                expl_text = f"Full rewrite of {target_dest.name} with {prof_name} rule profile."
            elif active_mode == "append":
                loss_flag = False
                desc_text = "Safe append: preserves user rules outside markers; updates bounded block."
                expl_text = f"Updates instructions in {target_dest.name} while retaining custom rules."
            else:
                loss_flag = False
                desc_text = "Skip mode: existing file preserved as-is with no modifications."
                expl_text = f"File {target_dest.name} exists and will not be touched."

            rule_items.append(
                RuleActionItem(
                    tool_key=tool_key,
                    target_path=str(target_dest),
                    action_type=active_mode,
                    file_exists=exists_flag,
                    existing_bytes=size_val,
                    data_loss_risk=loss_flag,
                    risk_description=desc_text,
                    explanation=expl_text,
                    content=instructions_body,
                    planned_content=planned_text,
                    diff=diff_text,
                )
            )

    mcp_section = config_dict.get("mcp", {})
    mcp_active = (
        False
        if disable_mcp
        else bool(mcp_section.get("enabled", True) if isinstance(mcp_section, dict) else mcp_section)
    )

    skills_section = config_dict.get("skills", {})
    skills_active = (
        False
        if disable_skills
        else bool(skills_section.get("enabled", True) if isinstance(skills_section, dict) else skills_section)
    )
    bundle_selected = (
        str(skills_section.get("bundle", "all")) if isinstance(skills_section, dict) else "all"
    )

    hooks_section = config_dict.get("hooks", {})
    hook_active = (
        False
        if disable_hooks
        else bool(hooks_section.get("git_pre_commit", True) if isinstance(hooks_section, dict) else hooks_section)
    )
    hook_cmd = (
        str(hooks_section.get("command", "uv run --no-project python scripts/claudemd_linter.py . --diff"))
        if isinstance(hooks_section, dict)
        else "uv run --no-project python scripts/claudemd_linter.py . --diff"
    )

    return ConfigExecutionPlan(
        workspace_path=str(workspace_dir),
        scope=scope_val,
        write_mode=active_mode,
        profile_name=prof_name,
        rule_actions=rule_items,
        mcp_enabled=mcp_active,
        skills_enabled=skills_active,
        skill_bundle=bundle_selected,
        git_hook_enabled=hook_active,
        git_hook_command=hook_cmd,
    )


def format_plan_preview(plan: ConfigExecutionPlan, show_diff: bool = False) -> str:
    lines: list[str] = [
        "=" * 72,
        "                    AI-DEV-TOOLS CONFIGURATION PLAN",
        "=" * 72,
        f"Workspace  : {plan.workspace_path}",
        f"Scope      : {plan.scope}",
        f"Write Mode : {plan.write_mode.upper()}",
        f"Profile    : {plan.profile_name}",
        "-" * 72,
        "[1. Instruction Rules & Target Files]",
    ]

    loss_warnings: list[str] = []
    for item_index, item in enumerate(plan.rule_actions, start=1):
        target_name = Path(item.target_path).name
        status_label = "NEW FILE" if not item.file_exists else f"EXISTS ({item.existing_bytes} bytes)"
        lines.append(f"  {item_index:2d}. [{item.tool_key.upper()}] -> {target_name} ({status_label})")
        lines.append(f"      Action      : {item.action_type.upper()}")
        lines.append(f"      Explanation : {item.explanation}")
        lines.append(f"      Safety Note : {item.risk_description}")
        if item.data_loss_risk:
            loss_warnings.append(f"  - {target_name}: {item.risk_description}")

    lines.append("-" * 72)
    lines.append("[2. Model Context Protocol (MCP)]")
    mcp_text = "Enabled (Registers repository MCP tools)" if plan.mcp_enabled else "Disabled"
    lines.append(f"  Status: {mcp_text}")

    lines.append("-" * 72)
    lines.append("[3. Agent Skills]")
    skills_text = f"Enabled (Bundle: '{plan.skill_bundle}')" if plan.skills_enabled else "Disabled"
    lines.append(f"  Status: {skills_text}")

    lines.append("-" * 72)
    lines.append("[4. Git Hooks]")
    hook_text = f"Enabled -> {plan.git_hook_command}" if plan.git_hook_enabled else "Disabled"
    lines.append(f"  Status: {hook_text}")

    if loss_warnings:
        lines.append("=" * 72)
        lines.append("                 POTENTIAL DATA LOSS WARNINGS")
        lines.append("=" * 72)
        for warn_item in loss_warnings:
            lines.append(warn_item)

    if show_diff:
        lines.append("=" * 72)
        lines.append("                    DETAILED FILE DIFFS")
        lines.append("=" * 72)
        diff_count = 0
        for item in plan.rule_actions:
            if item.diff.strip():
                lines.append(f"--- File: {Path(item.target_path).name} ---")
                lines.append(item.diff.rstrip())
                lines.append("")
                diff_count += 1
        if diff_count == 0:
            lines.append("No textual differences detected.")

    lines.append("=" * 72)
    return "\n".join(lines)


def execute_plan(plan: ConfigExecutionPlan, dry_run: bool = False) -> tuple[int, int]:
    workspace_directory = Path(plan.workspace_path)
    user_home = get_user_home()
    success_count = 0
    failure_count = 0
    recorded_files: list[dict[str, Any]] = []

    print(f"\n>>> Applying AI-Dev-Tools Configuration ({'DRY-RUN' if dry_run else 'LIVE'})...")

    for item in plan.rule_actions:
        target_file = Path(item.target_path)
        try:
            if plan.scope == "workspace":
                validate_workspace_path(target_file, workspace_directory)

            backup_path_str: str | None = None
            if item.file_exists and item.action_type == "overwrite" and not dry_run:
                backup_dest = create_safe_backup(target_file)
                backup_path_str = str(backup_dest.relative_to(workspace_directory))
                print(f"[BACKUP] Created collision-safe backup: {backup_dest}")

            if dry_run:
                action_label = "create" if not item.file_exists else item.action_type
                print(f"[DRY-RUN] Would {action_label}: {target_file}")
            else:
                atomic_write_text(target_file, item.planned_content)
                print(f"[+] Wrote instructions to: {target_file}")

            recorded_files.append(
                {
                    "path": str(target_file.relative_to(workspace_directory)),
                    "action": "created" if not item.file_exists else item.action_type,
                    "backup_path": backup_path_str,
                    "owned_markers": True,
                }
            )
            success_count += 1
        except Exception as exc:
            sys.stderr.write(f"[ERROR] Failed to write {target_file}: {exc}\n")
            failure_count += 1

    if plan.mcp_enabled:
        try:
            configure_mcp_servers(REPO_ROOT, scope=plan.scope, workspace=workspace_directory, dry_run=dry_run)
            success_count += 1
        except Exception as exc:
            sys.stderr.write(f"[ERROR] Failed to configure MCP servers: {exc}\n")
            failure_count += 1

    if plan.skills_enabled:
        try:
            chosen_bundle_skills = SKILL_BUNDLES.get(plan.skill_bundle, None) if plan.skill_bundle != "all" else None
            configure_skills(
                REPO_ROOT,
                scope=plan.scope,
                workspace=workspace_directory,
                dry_run=dry_run,
                enabled_skills=chosen_bundle_skills,
            )
            success_count += 1
        except Exception as exc:
            sys.stderr.write(f"[ERROR] Failed to configure skills: {exc}\n")
            failure_count += 1

    if plan.git_hook_enabled:
        try:
            if not dry_run:
                install_hook(workspace_directory, action="append")
            else:
                print(f"[DRY-RUN] Would install git pre-commit hook in {workspace_directory}")
            success_count += 1
        except Exception as exc:
            sys.stderr.write(f"[ERROR] Failed to configure git pre-commit hook: {exc}\n")
            failure_count += 1

    if not dry_run and failure_count == 0:
        manifest_data = {
            "schema_version": 1,
            "applied_at": datetime.now(timezone.utc).isoformat(),
            "workspace_path": str(workspace_directory),
            "scope": plan.scope,
            "write_mode": plan.write_mode,
            "profile_name": plan.profile_name,
            "files": recorded_files,
            "skills_enabled": plan.skills_enabled,
            "skill_bundle": plan.skill_bundle,
            "mcp_enabled": plan.mcp_enabled,
            "git_hook_enabled": plan.git_hook_enabled,
        }
        manifest_path = workspace_directory / STATE_MANIFEST_FILE
        try:
            atomic_write_text(manifest_path, json.dumps(manifest_data, indent=2))
        except OSError as manifest_err:
            _ = manifest_err

    return success_count, failure_count


def uninstall_configuration(
    workspace_dir: Path,
    restore_backups: bool = True,
    dry_run: bool = False,
) -> tuple[int, int]:
    resolved_workspace = workspace_dir.resolve()
    manifest_path = resolved_workspace / STATE_MANIFEST_FILE
    success_count = 0
    failure_count = 0

    print(f"\n>>> Uninstalling AI-Dev-Tools Configuration ({'DRY-RUN' if dry_run else 'LIVE'})...")

    files_to_process: list[dict[str, Any]] = []
    if manifest_path.is_file():
        try:
            manifest_dict = json.loads(manifest_path.read_text(encoding="utf-8"))
            files_to_process = list(manifest_dict.get("files", []))
        except Exception:
            files_to_process = []

    if not files_to_process:
        all_defs = get_tool_definitions(resolved_workspace)
        for defn in all_defs.values():
            for target_path in defn["workspace_paths"]:
                if target_path.exists():
                    files_to_process.append({"path": str(target_path.relative_to(resolved_workspace))})

    for file_record in files_to_process:
        relative_path = file_record.get("path", "")
        if not relative_path:
            continue
        target_path = resolved_workspace / relative_path
        if not target_path.exists():
            continue

        try:
            backup_rel = file_record.get("backup_path")
            backup_file = resolved_workspace / backup_rel if backup_rel else None

            if restore_backups and backup_file and backup_file.is_file():
                if dry_run:
                    print(f"[DRY-RUN] Would restore backup {backup_file} -> {target_path}")
                else:
                    shutil.copy2(backup_file, target_path)
                    backup_file.unlink()
                    print(f"[OK] Restored backup: {target_path}")
                success_count += 1
                continue

            current_text = target_path.read_text(encoding="utf-8", errors="replace")
            if BEGIN_MARKER in current_text and END_MARKER in current_text:
                pattern = rf"\n*{re.escape(BEGIN_MARKER)}.*?{re.escape(END_MARKER)}\n*"
                cleaned_text = re.sub(pattern, "\n\n", current_text, flags=re.DOTALL)
                _, remaining_body = _split_frontmatter(cleaned_text.strip())
                if not remaining_body.strip():
                    if dry_run:
                        print(f"[DRY-RUN] Would remove owned instruction file: {target_path}")
                    else:
                        target_path.unlink()
                        print(f"[OK] Removed owned instruction file: {target_path}")
                else:
                    if dry_run:
                        print(f"[DRY-RUN] Would excise owned block from: {target_path}")
                    else:
                        atomic_write_text(target_path, cleaned_text.strip() + "\n")
                        print(f"[OK] Excised owned block from: {target_path}")
                success_count += 1
            else:
                print(f"[-] No owned block found in: {target_path}")
        except Exception as exc:
            sys.stderr.write(f"[ERROR] Failed to clean {target_path}: {exc}\n")
            failure_count += 1

    try:
        configure_skills(REPO_ROOT, scope="workspace", workspace=resolved_workspace, dry_run=dry_run, remove=True)
        success_count += 1
    except Exception as exc:
        sys.stderr.write(f"[ERROR] Failed to remove skills: {exc}\n")
        failure_count += 1

    try:
        if not dry_run:
            uninstall_hook(resolved_workspace)
        else:
            print(f"[DRY-RUN] Would uninstall git pre-commit hook from {resolved_workspace}")
        success_count += 1
    except Exception as exc:
        sys.stderr.write(f"[ERROR] Failed to uninstall git hook: {exc}\n")
        failure_count += 1

    if not dry_run and manifest_path.is_file():
        try:
            manifest_path.unlink()
        except OSError as unlink_err:
            _ = unlink_err

    return success_count, failure_count


def parse_cli_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Apply YAML configuration for AI assistants, linter rules, skills, and hooks."
    )
    parser.add_argument(
        "--config",
        "-c",
        type=Path,
        default=REPO_ROOT / "config.yaml",
        help="Path to YAML configuration file (default: config.yaml)",
    )
    parser.add_argument(
        "--workspace",
        "-w",
        type=Path,
        default=Path.cwd(),
        help="Target workspace directory (default: current directory)",
    )
    parser.add_argument(
        "--dry-run",
        "-d",
        action="store_true",
        help="Preview changes and display data loss risks without writing files",
    )
    parser.add_argument(
        "--diff",
        action="store_true",
        help="Display detailed unified diffs for every affected file in plan preview",
    )
    parser.add_argument(
        "--detect",
        action="store_true",
        help="Detect existing workspace tool configurations and apply only relevant tools",
    )
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="Cleanly remove ai-dev-tools instructions, skills, hooks, and restore backups",
    )
    parser.add_argument(
        "--restore-backups",
        action="store_true",
        default=True,
        help="Restore original backups (.bak) during uninstall if available (default: True)",
    )
    parser.add_argument(
        "--write-mode",
        "-m",
        choices=["append", "overwrite", "skip"],
        default=None,
        help="Override file write mode ('append', 'overwrite', 'skip')",
    )
    parser.add_argument(
        "--tools",
        "-t",
        type=str,
        default=None,
        help="Comma-separated list of tools to configure (e.g. 'claude,cursor,antigravity')",
    )
    parser.add_argument(
        "--profile",
        "-p",
        choices=["full", "strict", "standard", "safe", "minimal"],
        default=None,
        help="Override rule profile",
    )
    parser.add_argument(
        "--no-hooks",
        action="store_true",
        help="Disable git pre-commit hook installation",
    )
    parser.add_argument(
        "--no-mcp",
        action="store_true",
        help="Disable Model Context Protocol server registration",
    )
    parser.add_argument(
        "--no-skills",
        action="store_true",
        help="Disable AI agent skill installation",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output the calculated execution plan as JSON",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Automatically approve and execute changes without interactive confirmation",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_cli_args()
    workspace_directory = args.workspace.resolve()

    if args.uninstall:
        successes, errors = uninstall_configuration(
            workspace_directory,
            restore_backups=args.restore_backups,
            dry_run=args.dry_run,
        )
        if errors > 0:
            print(f"\n[!] Uninstall completed with {errors} error(s).")
            return 1
        print("\n[OK] Uninstall completed successfully!")
        return 0

    cfg_file = args.config
    if not cfg_file.is_file():
        sys.stderr.write(f"Configuration file not found: {cfg_file}\n")
        return 1

    loaded_cfg = load_yaml_file(cfg_file)
    schema_warnings = validate_config_schema(loaded_cfg)
    for warn_text in schema_warnings:
        print(f"[WARNING] Schema notice: {warn_text}")

    target_tools = [tool_entry.strip() for tool_entry in args.tools.split(",")] if args.tools else None

    plan = build_plan_from_config(
        loaded_cfg,
        workspace_directory,
        mode_override=args.write_mode,
        tools_override=target_tools,
        profile_override=args.profile,
        disable_hooks=args.no_hooks,
        disable_mcp=args.no_mcp,
        disable_skills=args.no_skills,
        detect_tools=args.detect,
    )

    if args.json:
        data_dict = asdict(plan)
        print(json.dumps(data_dict, indent=2))
        return 0

    preview_output = format_plan_preview(plan, show_diff=args.diff)
    print(preview_output)

    if args.dry_run:
        print("\n[DRY-RUN] Execution completed. No files modified.")
        return 0

    if not args.yes and sys.stdin.isatty():
        try:
            choice = input("\nProceed with applying these changes? [y/N]: ").strip().lower()
            if choice not in ("y", "yes"):
                print("[-] Operation cancelled by user.")
                return 0
        except (KeyboardInterrupt, EOFError):
            print("\n[-] Operation cancelled.")
            return 0

    _, errs = execute_plan(plan, dry_run=False)
    if errs > 0:
        print(f"\n[!] Completed with {errs} warning(s)/error(s).")
        return 1
    print("\n[OK] Configuration successfully applied!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
