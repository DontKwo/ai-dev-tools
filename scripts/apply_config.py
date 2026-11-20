"""Applies declarative YAML configuration to setup AI tools, skills, and hooks."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from configure import (
    SKILL_BUNDLES,
    build_instructions,
    configure_mcp_servers,
    configure_skills,
    get_tool_definitions,
    install_file,
)
from install_hooks import install_hook
from tools_config import BUILTIN_PROFILES
from utils import get_user_home
from yaml_utils import load_yaml_file


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
                if targets_toggle.get(fname_key) is False:
                    continue

            exists_flag = target_dest.exists()
            size_val = target_dest.stat().st_size if exists_flag else 0
            instructions_body = build_instructions(
                frontmatter=definition.get("frontmatter", ""),
                workspace=workspace_dir,
            )

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


def format_plan_preview(plan: ConfigExecutionPlan) -> str:
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
    for idx, item in enumerate(plan.rule_actions, start=1):
        target_name = Path(item.target_path).name
        status_label = "NEW FILE" if not item.file_exists else f"EXISTS ({item.existing_bytes} bytes)"
        lines.append(f"  {idx:2d}. [{item.tool_key.upper()}] -> {target_name} ({status_label})")
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
        for warn in loss_warnings:
            lines.append(warn)

    lines.append("=" * 72)
    return "\n".join(lines)


def execute_plan(plan: ConfigExecutionPlan, dry_run: bool = False) -> tuple[int, int]:
    ws_dir = Path(plan.workspace_path)
    user_home = get_user_home()
    success_count = 0
    failure_count = 0

    print(f"\n>>> Applying AI-Dev-Tools Configuration ({'DRY-RUN' if dry_run else 'LIVE'})...")

    for item in plan.rule_actions:
        target_file = Path(item.target_path)
        try:
            if item.file_exists and item.action_type == "overwrite" and not dry_run:
                backup_dest = target_file.with_suffix(target_file.suffix + ".bak")
                shutil.copy2(target_file, backup_dest)
                print(f"[BACKUP] Created backup of existing file: {backup_dest}")

            install_file(target_file, item.content, default_action=item.action_type, dry_run=dry_run)
            success_count += 1
        except Exception as exc:
            sys.stderr.write(f"[ERROR] Failed to write {target_file}: {exc}\n")
            failure_count += 1

    if plan.mcp_enabled:
        try:
            configure_mcp_servers(ws_dir, user_home, dry_run=dry_run)
            success_count += 1
        except Exception as exc:
            sys.stderr.write(f"[ERROR] Failed to configure MCP servers: {exc}\n")
            failure_count += 1

    if plan.skills_enabled:
        try:
            configure_skills(ws_dir, user_home, dry_run=dry_run, selected_bundle=plan.skill_bundle)
            success_count += 1
        except Exception as exc:
            sys.stderr.write(f"[ERROR] Failed to configure skills: {exc}\n")
            failure_count += 1

    if plan.git_hook_enabled:
        try:
            install_hook(ws_dir, action="append")
            success_count += 1
        except Exception as exc:
            sys.stderr.write(f"[ERROR] Failed to configure git pre-commit hook: {exc}\n")
            failure_count += 1

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
    cfg_file = args.config
    if not cfg_file.is_file():
        sys.stderr.write(f"Configuration file not found: {cfg_file}\n")
        return 1

    loaded_cfg = load_yaml_file(cfg_file)
    target_tools = [x.strip() for x in args.tools.split(",")] if args.tools else None

    plan = build_plan_from_config(
        loaded_cfg,
        args.workspace.resolve(),
        mode_override=args.write_mode,
        tools_override=target_tools,
        profile_override=args.profile,
        disable_hooks=args.no_hooks,
        disable_mcp=args.no_mcp,
        disable_skills=args.no_skills,
    )

    if args.json:
        data_dict = asdict(plan)
        print(json.dumps(data_dict, indent=2))
        return 0

    preview_output = format_plan_preview(plan)
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
