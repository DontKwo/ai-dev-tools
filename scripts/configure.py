#!/usr/bin/env python3
"""Configures AI developer tools (Claude, Cursor, Cline, Antigravity, Codex, etc.)
with Developer's unified style rules and automated AST linter instructions.
"""

from __future__ import annotations

import argparse
import json
import platform
import re
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from skills_manager import get_tool_skill_dirs, install_single_skill
from tools_config import generate_default_config, load_tools_config
from utils import IS_WINDOWS, format_command_path, get_user_home
TEMPLATE_PATH = REPO_ROOT / "templates" / "INSTRUCTIONS_TEMPLATE.md"
ENGINEERING_PATH = REPO_ROOT / "templates" / "ENGINEERING_RULES.md"
PYTHON_RULES_PATH = REPO_ROOT / "templates" / "PYTHON_RULES.md"
LINTER_SCRIPT = REPO_ROOT / "scripts" / "claudemd_linter.py"


# Registry of supported AI tools and target paths
def get_tool_definitions(workspace: Path | None = None) -> dict[str, dict]:
    home = get_user_home()
    ws = workspace or Path.cwd()

    return {
        "claude": {
            "name": "Claude Code",
            "global_paths": [home / ".claude" / "CLAUDE.md"],
            "workspace_paths": [ws / "CLAUDE.md"],
            "frontmatter": "",
        },
        "cursor": {
            "name": "Cursor IDE",
            "global_paths": [
                home / ".cursor" / "rules" / "developer-rules.mdc",
                home / ".cursorrules",
            ],
            "workspace_paths": [
                ws / ".cursor" / "rules" / "developer-rules.mdc",
                ws / ".cursorrules",
            ],
            "frontmatter": "---\ndescription: Developer AI Development and Linting Rules\nglobs: *\nalwaysApply: true\n---\n\n",
        },
        "cline": {
            "name": "Cline & Roo Code",
            "global_paths": [home / ".clinerules"],
            "workspace_paths": [ws / ".clinerules"],
            "frontmatter": "",
        },
        "antigravity": {
            "name": "Google Antigravity (AGY)",
            "global_paths": [
                home / ".gemini" / "config" / "AGENTS.md",
                home / ".gemini" / "antigravity" / "rules" / "user_rules.md",
            ],
            "workspace_paths": [
                ws / "AGENTS.md",
                ws / ".agent" / "rules" / "user_rules.md",
                ws / ".agents" / "rules" / "user_rules.md",
            ],
            "frontmatter": "",
        },
        "codex": {
            "name": "OpenAI Codex & ChatGPT",
            "global_paths": [home / ".codex" / "instructions.md"],
            "workspace_paths": [ws / "AGENTS.md"],
            "frontmatter": "",
        },
        "windsurf": {
            "name": "Windsurf IDE",
            "global_paths": [home / ".windsurfrules"],
            "workspace_paths": [ws / ".windsurfrules"],
            "frontmatter": "",
        },
        "copilot": {
            "name": "GitHub Copilot",
            "global_paths": [],
            "workspace_paths": [ws / ".github" / "copilot-instructions.md"],
            "frontmatter": "",
        },
        "aider": {
            "name": "Aider CLI",
            "global_paths": [home / ".aider.conventions.md"],
            "workspace_paths": [ws / ".aider.conventions.md"],
            "frontmatter": "",
        },
    }


def calc_linter_command(workspace: Path | None = None) -> str:
    if workspace is not None and workspace.resolve() == REPO_ROOT.resolve():
        return "uv run --no-project python scripts/claudemd_linter.py"
    if shutil.which("aitools"):
        return "aitools lint"
    script_str = format_command_path(LINTER_SCRIPT)
    if shutil.which("uv"):
        return f"uv run --no-project python {script_str}"
    py_bin = "python" if IS_WINDOWS else "python3"
    return f"{py_bin} {script_str}"


def build_instructions(frontmatter: str = "", workspace: Path | None = None) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    linter_cmd = calc_linter_command(workspace)
    if workspace is not None and workspace.resolve() == REPO_ROOT.resolve():
        eng_path = "templates/ENGINEERING_RULES.md"
        py_rules_path = "templates/PYTHON_RULES.md"
    else:
        eng_path = format_command_path(ENGINEERING_PATH)
        py_rules_path = format_command_path(PYTHON_RULES_PATH)

    content = template.replace("{{LINTER_COMMAND}}", linter_cmd)
    content = content.replace("{{ENGINEERING_RULES_PATH}}", eng_path)
    content = content.replace("{{PYTHON_RULES_PATH}}", py_rules_path)
    if frontmatter:
        content = frontmatter + content
    return content


FRONTMATTER_RE = re.compile(r"^(---\s*\n.*?\n---\s*\n+)", re.DOTALL)


def _split_frontmatter(text: str) -> tuple[str, str]:
    match = FRONTMATTER_RE.match(text)
    if match:
        return match.group(1), text[match.end():]
    return "", text


def install_file(dest: Path, content: str, default_action: str = "append", dry_run: bool = False) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)

    action = default_action
    begin_marker = "<!-- BEGIN AI-DEV-TOOLS -->"
    end_marker = "<!-- END AI-DEV-TOOLS -->"
    frontmatter, body = _split_frontmatter(content)
    bounded_body = f"{begin_marker}\n{body.rstrip()}\n{end_marker}"
    full_bounded = f"{frontmatter}{bounded_body}\n"

    if dest.exists():
        if action == "ask":
            if not sys.stdin.isatty():
                action = "append"
            else:
                print(f"\n[!] File already exists: {dest}")
                print("    [A] Append to existing file (default)")
                print("    [O] Overwrite")
                print("    [S] Skip")
                choice = input("    Choose action [A/O/S, default A]: ").strip().lower()
                if choice in ("o", "overwrite"):
                    action = "overwrite"
                elif choice in ("s", "skip"):
                    action = "skip"
                else:
                    action = "append"

        if action == "skip":
            print(f"[-] Skipped: {dest}")
            return
        if action == "append":
            if dry_run:
                print(f"[DRY-RUN] Would append bounded block to: {dest}")
                return
            existing = dest.read_text(encoding="utf-8")
            if begin_marker in existing and end_marker in existing:
                pattern = rf"{re.escape(begin_marker)}.*?{re.escape(end_marker)}"
                updated = re.sub(pattern, lambda _m: bounded_body, existing, count=1, flags=re.DOTALL)
                if not updated.endswith("\n"):
                    updated += "\n"
            elif not existing.strip():
                updated = full_bounded
            elif frontmatter and not _split_frontmatter(existing)[0]:
                updated = f"{frontmatter}{existing.rstrip()}\n\n{bounded_body}\n"
            else:
                updated = f"{existing.rstrip()}\n\n{bounded_body}\n"
            dest.write_text(updated, encoding="utf-8")
            print(f"[+] Appended instructions to: {dest}")
            return
        if action == "overwrite":
            if dry_run:
                print(f"[DRY-RUN] Would overwrite: {dest}")
                return
            dest.write_text(full_bounded, encoding="utf-8")
            print(f"[+] Overwrote: {dest}")
            return
    else:
        if dry_run:
            print(f"[DRY-RUN] Would create: {dest}")
            return
        dest.write_text(full_bounded, encoding="utf-8")
        print(f"[+] Created: {dest}")


def remove_tool_targets(selected_tools: list[str], scope: str, workspace: Path, dry_run: bool = False) -> None:
    tool_defs = get_tool_definitions(workspace)
    begin_marker = "<!-- BEGIN AI-DEV-TOOLS -->"
    end_marker = "<!-- END AI-DEV-TOOLS -->"

    for tool_key in selected_tools:
        if tool_key not in tool_defs:
            continue
        defn = tool_defs[tool_key]
        targets: list[Path] = []
        if scope in ("global", "both"):
            targets.extend(defn["global_paths"])
        if scope in ("workspace", "both"):
            targets.extend(defn["workspace_paths"])

        for target in targets:
            if not target.is_file():
                continue
            text = target.read_text(encoding="utf-8", errors="replace")
            if begin_marker in text and end_marker in text:
                pattern = rf"\n*{re.escape(begin_marker)}.*?{re.escape(end_marker)}\n*"
                cleaned = re.sub(pattern, "\n\n", text, flags=re.DOTALL)
                _, remaining_body = _split_frontmatter(cleaned.lstrip("\n"))
                if not remaining_body.strip():
                    if dry_run:
                        print(f"[DRY-RUN] Would delete: {target}")
                    else:
                        target.unlink()
                        print(f"[OK] Deleted: {target}")
                elif dry_run:
                    print(f"[DRY-RUN] Would remove ai-dev-tools block from: {target}")
                else:
                    target.write_text(cleaned.strip("\n") + "\n", encoding="utf-8")
                    print(f"[OK] Removed ai-dev-tools block from: {target}")
            elif "claudemd_linter" in text or "ai-dev-tools" in text:
                if dry_run:
                    print(f"[DRY-RUN] Would delete: {target}")
                else:
                    target.unlink()
                    print(f"[OK] Deleted: {target}")


def configure_tools(
    selected_tools: list[str],
    scope: str,
    workspace: Path,
    action: str,
    dry_run: bool = False,
) -> None:
    tool_defs = get_tool_definitions(workspace)

    for tool_key in selected_tools:
        if tool_key not in tool_defs:
            print(f"[!] Warning: Unknown tool '{tool_key}' ignored.")
            continue

        defn = tool_defs[tool_key]
        print(f"\n>>> Configuring {defn['name']}...")

        targets: list[Path] = []
        if scope in ("global", "both"):
            targets.extend(defn["global_paths"])
        if scope in ("workspace", "both"):
            targets.extend(defn["workspace_paths"])

        if not targets:
            if scope == "global" and not defn["global_paths"]:
                print(f"[-] Note: {defn['name']} is workspace-only (configure with --scope workspace).")
            else:
                print(f"[-] No target paths configured for {defn['name']} under scope '{scope}'.")
            continue

        for target in targets:
            frontmatter = defn["frontmatter"] if target.suffix == ".mdc" else ""
            content = build_instructions(frontmatter, workspace=workspace)
            install_file(target, content, default_action=action, dry_run=dry_run)


def configure_mcp_servers(
    repo_root: Path,
    scope: str = "global",
    workspace: Path | None = None,
    tools: list[str] | None = None,
    dry_run: bool = False,
    remove: bool = False,
) -> None:
    home = get_user_home()
    ws = workspace or Path.cwd()
    mcp_script = repo_root / "mcp" / "server.py"

    print("\n>>> Configuring Model Context Protocol (MCP) Servers...")

    uv_bin = shutil.which("uv")
    if uv_bin:
        resolved_uv = str(Path(uv_bin).resolve())
        base_entry: dict = {
            "command": resolved_uv,
            "args": ["run", "--no-project", "python", str(mcp_script)],
        }
    else:
        server_cmd = sys.executable or ("python" if IS_WINDOWS else "python3")
        base_entry = {
            "command": server_cmd,
            "args": [str(mcp_script)],
        }

    configs: list[tuple[str, Path, dict]] = []

    # 1. Claude Desktop & Claude Code
    if not tools or "claude" in tools:
        if IS_WINDOWS:
            claude_desktop = home / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"  # noqa: 91
        elif platform.system() == "Darwin":
            claude_desktop = home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
        else:
            claude_desktop = home / ".config" / "Claude" / "claude_desktop_config.json"

        if scope in ("global", "both"):
            configs.append(("Claude Desktop", claude_desktop, dict(base_entry)))
            configs.append(("Claude Code CLI (Global)", home / ".claude.json", dict(base_entry)))
        if scope in ("workspace", "both"):
            configs.append(("Claude Code CLI (Workspace)", ws / ".claude.json", dict(base_entry)))

    # 2. Cursor IDE
    if not tools or "cursor" in tools:
        if scope in ("global", "both"):
            configs.append(("Cursor IDE (Global)", home / ".cursor" / "mcp.json", dict(base_entry)))
        if scope in ("workspace", "both"):
            configs.append(("Cursor IDE (Workspace)", ws / ".cursor" / "mcp.json", dict(base_entry)))

    # 3. Cline & Roo Code
    if not tools or "cline" in tools:
        cline_entry = dict(base_entry)
        cline_entry.update({"disabled": False, "autoApprove": []})

        if IS_WINDOWS:
            code_storage = home / "AppData" / "Roaming" / "Code" / "User" / "globalStorage"  # noqa: 91
        elif platform.system() == "Darwin":
            code_storage = home / "Library" / "Application Support" / "Code" / "User" / "globalStorage"
        else:
            code_storage = home / ".config" / "Code" / "User" / "globalStorage"

        configs.append(
            (
                "Cline (VS Code)",
                code_storage / "saoudrizwan.claude-dev" / "settings" / "cline_mcp_settings.json",
                cline_entry,
            )
        )
        configs.append(
            (
                "Roo Code (VS Code)",
                code_storage / "rooveterinaryinc.roo-cline" / "settings" / "cline_mcp_settings.json",
                cline_entry,
            )
        )

    # 4. Windsurf IDE
    if not tools or "windsurf" in tools:
        configs.append(
            (
                "Windsurf IDE",
                home / ".codeium" / "windsurf" / "mcp_config.json",
                dict(base_entry),
            )
        )

    # 5. Google Antigravity
    if not tools or "antigravity" in tools:
        if scope in ("global", "both"):
            configs.append(
                (
                    "Google Antigravity (Global Config)",
                    home / ".gemini" / "config" / "mcp_config.json",
                    dict(base_entry),
                )
            )
            configs.append(
                (
                    "Google Antigravity (App Storage)",
                    home / ".gemini" / "antigravity" / "mcp_config.json",
                    dict(base_entry),
                )
            )
        if scope in ("workspace", "both"):
            configs.append(
                (
                    "Google Antigravity (Workspace .agent)",
                    ws / ".agent" / "mcp_config.json",
                    dict(base_entry),
                )
            )
            configs.append(
                (
                    "Google Antigravity (Workspace .agents)",
                    ws / ".agents" / "mcp_config.json",
                    dict(base_entry),
                )
            )

    configured_count = 0
    for name, path, entry in configs:
        if remove:
            if not path.is_file():
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if "mcpServers" in data and "ai-dev-tools" in data["mcpServers"]:
                    del data["mcpServers"]["ai-dev-tools"]
                    if dry_run:
                        print(f"[DRY-RUN] Would remove MCP server entry from {name}: {path}")
                    else:
                        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
                        print(f"[OK] Removed MCP server from {name}: {path}")
            except OSError:
                continue
            continue

        try:
            if dry_run:
                print(f"[DRY-RUN] Would configure MCP for {name} -> {path}")
                configured_count += 1
                continue

            path.parent.mkdir(parents=True, exist_ok=True)
            data: dict = {}
            if path.is_file():
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                except Exception as err:
                    print(f"[!] Warning: Could not parse {path} as valid JSON ({err}). Skipping to prevent corruption.")
                    continue
                try:
                    backup_path = path.with_suffix(path.suffix + ".bak")
                    backup_path.write_bytes(path.read_bytes())
                except OSError:
                    backup_path = None

            if "mcpServers" not in data or not isinstance(data["mcpServers"], dict):
                data["mcpServers"] = {}

            data["mcpServers"]["ai-dev-tools"] = entry
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            print(f"[OK] Configured MCP server for {name} -> {path}")
            configured_count += 1
        except OSError as err:
            print(f"[!] Note: Could not configure MCP for {name} ({err})")

    if not remove:
        print(f"[+] Total MCP configs updated: {configured_count}")


def configure_skills(
    repo_root: Path,
    scope: str = "global",
    workspace: Path | None = None,
    tools: list[str] | None = None,
    enabled_skills: list[str] | None = None,
    disabled_skills: list[str] | None = None,
    dry_run: bool = False,
    remove: bool = False,
) -> None:
    source_skills = repo_root / "skills"
    if not source_skills.is_dir():
        return

    home = get_user_home()
    ws = workspace or Path.cwd()
    target_tools = tools if tools is not None else ["antigravity", "agents", "claude", "cursor", "windsurf", "cline", "codex"]
    tool_dirs = get_tool_skill_dirs(home, ws, scope=scope)

    destinations: list[tuple[str, Path]] = []
    for tool_name in target_tools:
        if tool_name in tool_dirs:
            for dest_path in tool_dirs[tool_name]:
                destinations.append((tool_name, dest_path))

    print("\n>>> Configuring AI Agent Skills...")
    for tool_name, dest_root in destinations:
        for skill_dir in source_skills.iterdir():
            if not skill_dir.is_dir():
                continue
            skill_name = skill_dir.name
            if enabled_skills and skill_name not in enabled_skills:
                continue
            if disabled_skills and skill_name in disabled_skills:
                continue

            target_dir = dest_root / skill_name
            if remove:
                if target_dir.exists():
                    if dry_run:
                        print(f"[DRY-RUN] Would remove skill: {target_dir}")
                    else:
                        shutil.rmtree(target_dir, ignore_errors=True)
                        print(f"[OK] Removed skill: {target_dir}")
                continue

            if dry_run:
                print(f"[DRY-RUN] Would install skill {skill_name} ({tool_name}) -> {target_dir}")
                continue

            install_single_skill(skill_dir, dest_root)
            print(f"[OK] Installed skill {skill_name} ({tool_name}) -> {target_dir}")


def interactive_menu() -> tuple[list[str], str, Path, bool]:
    print("Developer AI Tools Configurator")
    print(f"Repo directory: {REPO_ROOT}")
    print(f"Linter script:  {LINTER_SCRIPT}")
    print("")

    tool_defs = get_tool_definitions()
    keys = list(tool_defs.keys())

    print("Supported AI Tools:")
    print("  0) [ALL] Configure all supported AI tools")
    for idx, key in enumerate(keys, 1):
        print(f"  {idx}) {tool_defs[key]['name']} ({key})")
    print("")

    selection = input(f"Select tools to configure [0-{len(keys)} or comma-separated, default 0]: ").strip()
    if not selection or selection == "0":
        selected = keys
    else:
        selected = []
        for part in selection.split(","):
            part_str = part.strip()
            if part_str.isdigit():
                num_idx = int(part_str) - 1
                if 0 <= num_idx < len(keys):
                    selected.append(keys[num_idx])
            elif part_str in tool_defs:
                selected.append(part_str)
        if not selected:
            selected = keys

    print(f"\nSelected tools: {', '.join(selected)}")
    print("\nConfiguration Scope:")
    print("  1) Global (user profile directories)")
    print("  2) Workspace (current or specified project directory)")
    print("  3) Both (global defaults + local workspace files)")
    scope_choice = input("Select scope [1-3, default 1]: ").strip()
    scope_map = {"1": "global", "2": "workspace", "3": "both"}
    scope = scope_map.get(scope_choice, "global")

    workspace = Path.cwd()
    if scope in ("workspace", "both"):
        ws_in = input(f"Target workspace folder [default: {workspace}]: ").strip()
        if ws_in:
            workspace = Path(ws_in).resolve()

    setup_mcp_in = input("\nAutomatically configure MCP servers for selected tools? [Y/n]: ").strip().lower()
    setup_mcp = setup_mcp_in not in ("n", "no")

    return selected, scope, workspace, setup_mcp


def main() -> None:
    parser = argparse.ArgumentParser(description="Configure Developer's AI development tools across platforms.")
    parser.add_argument(
        "--tools",
        help="Comma-separated list of tools (claude, cursor, cline, antigravity, codex, windsurf, copilot, aider, all)",
    )
    parser.add_argument(
        "--scope",
        choices=["global", "workspace", "both"],
        default="global",
        help="Installation scope: global user profile, workspace project, or both.",
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=Path.cwd(),
        help="Path to workspace root (used when scope is workspace or both).",
    )
    parser.add_argument(
        "--action",
        choices=["ask", "overwrite", "append", "skip"],
        default="append",
        help="Action when a destination file already exists (default: append).",
    )
    parser.add_argument(
        "--no-mcp",
        action="store_true",
        help="Skip automatic configuration of Model Context Protocol (MCP) servers.",
    )
    parser.add_argument(
        "--no-skills",
        action="store_true",
        help="Skip automatic installation of agent skills.",
    )
    parser.add_argument(
        "--skills-tools",
        help="Comma-separated tools for skill installation (antigravity, claude, cursor, windsurf, cline, codex, all)",
    )
    parser.add_argument(
        "--skills",
        help="Comma-separated whitelist of skills to install (e.g. lint-and-fix,smart-test)",
    )
    parser.add_argument(
        "--exclude-skills",
        help="Comma-separated blacklist of skills to exclude (e.g. doc-to-markdown)",
    )
    parser.add_argument(
        "--init-config",
        action="store_true",
        help="Generate default .aitools.toml configuration file in workspace.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview actions without modifying files.",
    )
    parser.add_argument(
        "--remove",
        action="store_true",
        help="Remove configured rules and MCP servers for selected tools.",
    )
    args = parser.parse_args()

    if args.init_config:
        target_cfg = args.workspace / ".aitools.toml"
        target_cfg.write_text(generate_default_config(), encoding="utf-8")
        print(f"[OK] Generated default configuration: {target_cfg}")
        ensure_custom_linter_config(args.workspace, dry_run=args.dry_run)
        return

    loaded_cfg = load_tools_config(args.workspace)
    tool_defs = get_tool_definitions(args.workspace)

    if not args.tools and len(sys.argv) == 1:
        selected, scope, workspace, setup_mcp = interactive_menu()
        configure_tools(selected, scope, workspace, args.action, dry_run=args.dry_run)
        if setup_mcp:
            configure_mcp_servers(REPO_ROOT, scope, workspace, selected, dry_run=args.dry_run)
        if not args.no_skills:
            configure_skills(REPO_ROOT, scope, workspace, tools=selected, dry_run=args.dry_run)
    else:
        tools_arg = args.tools or "all"
        if tools_arg.strip().lower() == "all":
            selected = list(tool_defs.keys())
        else:
            selected = [t.strip().lower() for t in tools_arg.split(",") if t.strip()]

        skill_targets = [t.strip().lower() for t in args.skills_tools.split(",")] if args.skills_tools else loaded_cfg.skill_targets
        if "all" in skill_targets:
            skill_targets = ["antigravity", "claude", "cursor", "windsurf", "cline", "codex"]

        enabled_skills = [s.strip() for s in args.skills.split(",")] if args.skills else loaded_cfg.enabled_skills
        disabled_skills = [s.strip() for s in args.exclude_skills.split(",")] if args.exclude_skills else loaded_cfg.disabled_skills

        if args.remove:
            remove_tool_targets(selected, args.scope, args.workspace, dry_run=args.dry_run)
            configure_mcp_servers(REPO_ROOT, args.scope, args.workspace, selected, dry_run=args.dry_run, remove=True)
            if not args.no_skills:
                configure_skills(
                    REPO_ROOT,
                    args.scope,
                    args.workspace,
                    tools=skill_targets,
                    enabled_skills=enabled_skills,
                    disabled_skills=disabled_skills,
                    dry_run=args.dry_run,
                    remove=True,
                )
            return

        configure_tools(selected, args.scope, args.workspace, args.action, dry_run=args.dry_run)
        if not args.no_mcp:
            configure_mcp_servers(REPO_ROOT, args.scope, args.workspace, selected, dry_run=args.dry_run)
        if not args.no_skills:
            configure_skills(
                REPO_ROOT,
                args.scope,
                args.workspace,
                tools=skill_targets,
                enabled_skills=enabled_skills,
                disabled_skills=disabled_skills,
                dry_run=args.dry_run,
            )

    ensure_custom_linter_config(REPO_ROOT, dry_run=args.dry_run)
    print("Configuration finished! All AI tools reference:")
    print(f"  Linter: {LINTER_SCRIPT}")
    print(f"  Rules:  {ENGINEERING_PATH}")


def ensure_custom_linter_config(target_root: Path, dry_run: bool = False) -> None:
    custom_cfg_path = target_root / "linter_custom.yaml"
    if custom_cfg_path.exists():
        return
    example_cfg_path = REPO_ROOT / "linter_custom.example.yaml"
    if not example_cfg_path.is_file():
        return
    if dry_run:
        print(f"[DRY-RUN] Would initialize custom linter config: {custom_cfg_path}")
        return
    shutil.copy2(example_cfg_path, custom_cfg_path)
    print(f"[OK] Initialized custom linter config: {custom_cfg_path}")


if __name__ == "__main__":
    main()
