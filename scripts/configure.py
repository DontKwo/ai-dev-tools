#!/usr/bin/env python3
"""Configures AI developer tools (Claude, Cursor, Cline, Antigravity, Codex, etc.)
with Developer's unified style rules and automated AST linter instructions.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import json
import platform
import re
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from skills_manager import get_tool_skill_dirs, install_single_skill
from tools_config import generate_default_config, load_tools_config, save_tools_config
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


SKILL_BUNDLES: dict[str, list[str]] = {
    "all": [],
    "core": [
        "smart-test",
        "tdd",
        "exhaustive-testing",
        "lint-and-fix",
        "diagnosing-bugs",
        "dependency-guard",
        "secret-sanitizer",
    ],
    "architecture": [
        "codebase-design",
        "improve-codebase-architecture",
        "domain-modeling",
        "to-spec",
        "to-tickets",
        "ponytail",
    ],
    "context": [
        "codebase-context",
        "doc-to-markdown",
        "clean-encoding",
        "pack-context",
    ],
    "workflow": [
        "grill-user",
        "workspace-checkpoint",
        "handoff",
        "session-wrap-up",
        "triage",
        "writing-for-agents",
        "implicit-requirements",
        "definition-of-done",
    ],
}


def detect_installed_tools(workspace: Path | None = None) -> list[str]:
    home = get_user_home()
    ws = workspace or Path.cwd()
    detected: list[str] = []

    if (home / ".claude").is_dir() or (ws / "CLAUDE.md").is_file() or shutil.which("claude"):
        detected.append("claude")

    if (
        (home / ".cursor").is_dir()
        or (ws / ".cursor").is_dir()
        or (ws / ".cursorrules").is_file()
        or shutil.which("cursor")
    ):
        detected.append("cursor")

    if (
        (home / ".gemini").is_dir()
        or (ws / ".agent").is_dir()
        or (ws / ".agents").is_dir()
        or (ws / "AGENTS.md").is_file()
        or shutil.which("agy")
    ):
        detected.append("antigravity")

    if (
        (home / ".codeium" / "windsurf").is_dir()
        or (ws / ".windsurfrules").is_file()
        or shutil.which("windsurf")
    ):
        detected.append("windsurf")

    code_storage = (
        home / "AppData" / "Roaming" / "Code" / "User" / "globalStorage"  # noqa: 91
        if IS_WINDOWS
        else home / ".config" / "Code" / "User" / "globalStorage"
    )
    if (
        (code_storage / "saoudrizwan.claude-dev").is_dir()
        or (code_storage / "rooveterinaryinc.roo-cline").is_dir()
        or (ws / ".clinerules").is_file()
    ):
        detected.append("cline")

    if (home / ".codex").is_dir() or shutil.which("codex"):
        detected.append("codex")

    if (ws / ".github" / "copilot-instructions.md").is_file() or (ws / ".github").is_dir():
        detected.append("copilot")

    if (
        (home / ".aider.conventions.md").is_file()
        or (ws / ".aider.conventions.md").is_file()
        or shutil.which("aider")
    ):
        detected.append("aider")

    return detected


def calc_linter_command(workspace: Path | None = None) -> str:
    if workspace is not None and workspace.resolve() == REPO_ROOT.resolve():
        return "uv run --no-project python scripts/claudemd_linter.py"
    if shutil.which("adt"):
        return "adt lint"
    if shutil.which("ailint"):
        return "ailint"
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


def get_mcp_server_configs(
    repo_root: Path,
    scope: str = "global",
    workspace: Path | None = None,
    tools: list[str] | None = None,
) -> list[tuple[str, Path, dict]]:
    home_dir = get_user_home()
    workspace_dir = workspace or Path.cwd()
    mcp_script = repo_root / "mcp" / "server.py"

    uv_binary = shutil.which("uv")
    if uv_binary:
        resolved_uv = str(Path(uv_binary).resolve())
        base_entry: dict = {
            "command": resolved_uv,
            "args": ["run", "--no-project", "python", str(mcp_script)],
        }
    else:
        server_command = sys.executable or ("python" if IS_WINDOWS else "python3")
        base_entry = {
            "command": server_command,
            "args": [str(mcp_script)],
        }

    configs: list[tuple[str, Path, dict]] = []

    # 1. Claude Desktop and Claude Code CLI
    if not tools or "claude" in tools:
        if IS_WINDOWS:
            claude_desktop = home_dir / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"  # noqa: 91
        elif platform.system() == "Darwin":
            claude_desktop = home_dir / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
        else:
            claude_desktop = home_dir / ".config" / "Claude" / "claude_desktop_config.json"

        if scope in ("global", "both"):
            configs.append(("Claude Desktop", claude_desktop, dict(base_entry)))
            configs.append(("Claude Code CLI (Global)", home_dir / ".claude.json", dict(base_entry)))
        if scope in ("workspace", "both"):
            configs.append(("Claude Code CLI (Workspace)", workspace_dir / ".claude.json", dict(base_entry)))

    # 2. Cursor IDE
    if not tools or "cursor" in tools:
        if scope in ("global", "both"):
            configs.append(("Cursor IDE (Global)", home_dir / ".cursor" / "mcp.json", dict(base_entry)))
        if scope in ("workspace", "both"):
            configs.append(("Cursor IDE (Workspace)", workspace_dir / ".cursor" / "mcp.json", dict(base_entry)))

    # 3. Cline and Roo Code
    if not tools or "cline" in tools:
        cline_entry = dict(base_entry)
        cline_entry.update({"disabled": False, "autoApprove": []})

        if IS_WINDOWS:
            code_storage = home_dir / "AppData" / "Roaming" / "Code" / "User" / "globalStorage"  # noqa: 91
        elif platform.system() == "Darwin":
            code_storage = home_dir / "Library" / "Application Support" / "Code" / "User" / "globalStorage"
        else:
            code_storage = home_dir / ".config" / "Code" / "User" / "globalStorage"

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
                home_dir / ".codeium" / "windsurf" / "mcp_config.json",
                dict(base_entry),
            )
        )

    # 5. Google Antigravity
    if not tools or "antigravity" in tools:
        if scope in ("global", "both"):
            configs.append(
                (
                    "Google Antigravity (Global Config)",
                    home_dir / ".gemini" / "config" / "mcp_config.json",
                    dict(base_entry),
                )
            )
            configs.append(
                (
                    "Google Antigravity (App Storage)",
                    home_dir / ".gemini" / "antigravity" / "mcp_config.json",
                    dict(base_entry),
                )
            )
        if scope in ("workspace", "both"):
            configs.append(
                (
                    "Google Antigravity (Workspace .agent)",
                    workspace_dir / ".agent" / "mcp_config.json",
                    dict(base_entry),
                )
            )
            configs.append(
                (
                    "Google Antigravity (Workspace .agents)",
                    workspace_dir / ".agents" / "mcp_config.json",
                    dict(base_entry),
                )
            )

    return configs


def configure_mcp_servers(
    repo_root: Path,
    scope: str = "global",
    workspace: Path | None = None,
    tools: list[str] | None = None,
    dry_run: bool = False,
    remove: bool = False,
) -> None:
    print("\n>>> Configuring Model Context Protocol (MCP) Servers...")
    configs = get_mcp_server_configs(repo_root, scope=scope, workspace=workspace, tools=tools)

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


@dataclass
class PlannedAction:
    category: str
    title: str
    description: str
    target_path: Path
    action_type: str
    tool_key: str = ""
    metadata: dict = field(default_factory=dict)


def create_setup_plan(
    repo_root: Path,
    selected_tools: list[str],
    scope: str,
    workspace: Path,
    action: str = "append",
    setup_rules: bool = True,
    setup_mcp: bool = True,
    setup_skills: bool = True,
    skill_targets: list[str] | None = None,
    enabled_skills: list[str] | None = None,
    disabled_skills: list[str] | None = None,
    init_custom_config: bool = True,
    linter_profile: str | None = None,
    linter_disable: list[int] | None = None,
    linter_enable: list[int] | None = None,
    setup_git_hook: bool = False,
) -> list[PlannedAction]:
    plan: list[PlannedAction] = []
    tool_defs = get_tool_definitions(workspace)

    # 1. Rule instructions
    if setup_rules:
        for tool_key in selected_tools:
            if tool_key not in tool_defs:
                continue
            tool_def = tool_defs[tool_key]
            targets: list[Path] = []
            if scope in ("global", "both"):
                targets.extend(tool_def["global_paths"])
            if scope in ("workspace", "both"):
                targets.extend(tool_def["workspace_paths"])

            for target in targets:
                frontmatter = tool_def["frontmatter"] if target.suffix == ".mdc" else ""
                if target.exists():
                    text = target.read_text(encoding="utf-8", errors="replace")
                    if "<!-- BEGIN AI-DEV-TOOLS -->" in text:
                        action_type = "update"
                        desc = f"Update existing ai-dev-tools rules block in {target}"
                    else:
                        action_type = "append"
                        desc = f"Append ai-dev-tools rules block to existing file at {target}"
                else:
                    action_type = "create"
                    desc = f"Create new rules file at {target}"

                plan.append(
                    PlannedAction(
                        category="rule",
                        title=f"{tool_def['name']} Rules",
                        description=desc,
                        target_path=target,
                        action_type=action_type,
                        tool_key=tool_key,
                        metadata={"frontmatter": frontmatter, "default_action": action},
                    )
                )

    # 2. Model Context Protocol servers
    if setup_mcp:
        mcp_configs = get_mcp_server_configs(repo_root, scope=scope, workspace=workspace, tools=selected_tools)
        for client_name, target_path, entry_dict in mcp_configs:
            action_type = "update" if target_path.exists() else "create"
            desc = f"Register 'ai-dev-tools' MCP server in {client_name} ({target_path})"
            plan.append(
                PlannedAction(
                    category="mcp",
                    title=f"MCP Server: {client_name}",
                    description=desc,
                    target_path=target_path,
                    action_type=action_type,
                    metadata={"name": client_name, "entry": entry_dict},
                )
            )

    # 3. Agent Skills
    if setup_skills:
        source_skills = repo_root / "skills"
        if source_skills.is_dir():
            home_dir = get_user_home()
            active_skill_tools = (
                skill_targets
                if skill_targets is not None
                else [tk for tk in selected_tools if tk in ("antigravity", "claude", "cursor", "windsurf", "cline", "codex")]
            )
            tool_dirs = get_tool_skill_dirs(home_dir, workspace, scope=scope)

            available_skill_names = [
                entry.name
                for entry in source_skills.iterdir()
                if entry.is_dir()
                and (not enabled_skills or entry.name in enabled_skills)
                and (not disabled_skills or entry.name not in disabled_skills)
            ]
            skills_count = len(available_skill_names)

            for tool_name in active_skill_tools:
                if tool_name in tool_dirs:
                    for dest_path in tool_dirs[tool_name]:
                        desc = f"Install {skills_count} agent skill runbooks into {dest_path}"
                        plan.append(
                            PlannedAction(
                                category="skill",
                                title=f"Agent Skills ({tool_name})",
                                description=desc,
                                target_path=dest_path,
                                action_type="copy",
                                tool_key=tool_name,
                                metadata={
                                    "enabled_skills": enabled_skills,
                                    "disabled_skills": disabled_skills,
                                    "skill_count": skills_count,
                                },
                            )
                        )

    # 4. Custom Linter Configuration
    if init_custom_config:
        custom_cfg_path = repo_root / "linter_custom.yaml"
        example_cfg_path = repo_root / "linter_custom.example.yaml"
        if not custom_cfg_path.exists() and example_cfg_path.is_file():
            desc = f"Initialize custom linter config at {custom_cfg_path} from template"
            plan.append(
                PlannedAction(
                    category="config",
                    title="Custom Linter Config",
                    description=desc,
                    target_path=custom_cfg_path,
                    action_type="create",
                    metadata={"example_path": example_cfg_path},
                )
            )

    # 5. Linter Profile Configuration
    if linter_profile:
        config_target = workspace / ".aitools.toml"
        desc = f"Configure linter profile '{linter_profile}' in {config_target}"
        action_type = "update" if config_target.exists() else "create"
        plan.append(
            PlannedAction(
                category="config",
                title=f"Linter Profile ({linter_profile.title()})",
                description=desc,
                target_path=config_target,
                action_type=action_type,
                metadata={
                    "profile": linter_profile,
                    "disable": linter_disable or [],
                    "enable": linter_enable or [],
                },
            )
        )

    # 6. Git Pre-Commit Hook
    if setup_git_hook:
        git_dir = workspace / ".git"
        if git_dir.is_dir():
            hook_target = git_dir / "hooks" / "pre-commit"
            action_type = "update" if hook_target.exists() else "create"
            desc = f"Install git pre-commit hook to verify staged changes with linter in {hook_target}"
            plan.append(
                PlannedAction(
                    category="git-hook",
                    title="Git Pre-Commit Hook",
                    description=desc,
                    target_path=hook_target,
                    action_type=action_type,
                )
            )

    return plan


def render_plan_summary(plan: list[PlannedAction]) -> str:
    if not plan:
        return "No configuration actions planned."

    lines: list[str] = [
        "=" * 70,
        "                         AI-DEV-TOOLS SETUP PLAN",
        "=" * 70,
        "ai-dev-tools will configure the following components for your AI assistants:",
        "",
    ]

    by_category: dict[str, list[PlannedAction]] = {}
    for item in plan:
        by_category.setdefault(item.category, []).append(item)

    category_labels = {
        "rule": "1. Instruction Rules (Coding Guidelines and Linter Commands)",
        "mcp": "2. Model Context Protocol (MCP) Server Registrations",
        "skill": "3. Agent Skills (Workflow Runbooks)",
        "config": "4. Custom Project Configuration",
        "git-hook": "5. Git Pre-Commit Hooks",
    }

    action_index = 1
    for category_key in ("rule", "mcp", "skill", "config", "git-hook"):
        category_items = by_category.get(category_key, [])
        if not category_items:
            continue
        lines.append(f"[{category_labels.get(category_key, category_key)}]")
        for item in category_items:
            lines.append(f"  {action_index}. {item.title}")
            lines.append(f"     Action: {item.description}")
            action_index += 1
        lines.append("")

    lines.append("=" * 70)
    return "\n".join(lines)


def ask_user_plan_confirmation(
    plan: list[PlannedAction],
    workspace: Path,
) -> list[PlannedAction]:
    if not plan:
        print("\n[OK] Everything is already configured. No actions needed.")
        return []

    print("\n" + render_plan_summary(plan))
    print("\nHow would you like to proceed?")
    print("  [A] Approve all actions and proceed")
    print("  [I] Review and approve or reject each item individually")
    print("  [C] Cancel setup and make no changes")

    try:
        user_choice = input("\nSelect an option [A/I/C, default A]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n[-] Setup cancelled.")
        return []

    if user_choice in ("c", "cancel", "q", "quit"):
        print("\n[-] Setup cancelled. No files or settings were modified.")
        return []

    if user_choice in ("i", "individual", "review"):
        print("\n--- Reviewing Individual Actions ---")
        approved_items: list[PlannedAction] = []
        for index, item in enumerate(plan, 1):
            print(f"\n[{index}/{len(plan)}] {item.title}")
            print(f"      Action: {item.description}")
            print(f"      Target: {item.target_path}")

            while True:
                try:
                    response_text = (
                        input("      Approve this action? [Y/n/v(iew preview), default Y]: ")
                        .strip()
                        .lower()
                    )
                except (EOFError, KeyboardInterrupt):
                    print("\n[-] Individual review aborted. No changes applied.")
                    return []

                if response_text in ("v", "view", "preview"):
                    if item.category == "rule":
                        frontmatter = item.metadata.get("frontmatter", "")
                        preview_content = build_instructions(frontmatter, workspace=workspace)
                        preview_lines = preview_content.splitlines()[:12]
                        print("\n      --- Content Preview (first 12 lines) ---")
                        for line_text in preview_lines:
                            print(f"      | {line_text}")
                        print("      ----------------------------------------\n")
                    elif item.category == "mcp":
                        entry_json = json.dumps(item.metadata.get("entry", {}), indent=2)
                        print(f"\n      --- MCP Entry Preview ---\n{entry_json}\n      -------------------------\n")
                    else:
                        print(f"\n      --- Preview ---\n      {item.description}\n      ---------------\n")
                    continue
                elif response_text in ("n", "no", "reject", "skip"):
                    print(f"      [-] Rejected: {item.title}")
                    break
                else:
                    print(f"      [+] Approved: {item.title}")
                    approved_items.append(item)
                    break

        print(f"\nReview complete: {len(approved_items)} approved, {len(plan) - len(approved_items)} rejected.")
        if not approved_items:
            print("[-] No actions approved. Exiting without making changes.")
            return []

        try:
            proceed_resp = (
                input(f"\nProceed with applying the {len(approved_items)} approved action(s)? [Y/n, default Y]: ")
                .strip()
                .lower()
            )
        except (EOFError, KeyboardInterrupt):
            print("\n[-] Setup cancelled.")
            return []

        if proceed_resp in ("n", "no"):
            print("[-] Cancelled by user. No changes applied.")
            return []

        return approved_items

    return plan


def execute_setup_plan(
    plan: list[PlannedAction],
    workspace: Path,
    action: str = "append",
    dry_run: bool = False,
) -> None:
    if not plan:
        return

    source_skills = REPO_ROOT / "skills"
    for item in plan:
        if item.category == "rule":
            frontmatter = item.metadata.get("frontmatter", "")
            content = build_instructions(frontmatter, workspace=workspace)
            install_file(item.target_path, content, default_action=action, dry_run=dry_run)

        elif item.category == "mcp":
            target_path = item.target_path
            client_name = item.metadata.get("name", "MCP Client")
            entry_dict = item.metadata.get("entry", {})
            if dry_run:
                print(f"[DRY-RUN] Would configure MCP for {client_name} -> {target_path}")
                continue
            try:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                existing_data: dict = {}
                if target_path.is_file():
                    try:
                        existing_data = json.loads(target_path.read_text(encoding="utf-8"))
                    except Exception as err:
                        print(f"[!] Warning: Could not parse {target_path} as valid JSON ({err}). Skipping.")
                        continue
                    try:
                        backup_path = target_path.with_suffix(target_path.suffix + ".bak")
                        backup_path.write_bytes(target_path.read_bytes())
                    except OSError:
                        backup_path = None
                if "mcpServers" not in existing_data or not isinstance(existing_data["mcpServers"], dict):
                    existing_data["mcpServers"] = {}
                existing_data["mcpServers"]["ai-dev-tools"] = entry_dict
                target_path.write_text(json.dumps(existing_data, indent=2), encoding="utf-8")
                print(f"[OK] Configured MCP server for {client_name} -> {target_path}")
            except OSError as exc:
                print(f"[!] Note: Could not configure MCP for {client_name} ({exc})")

        elif item.category == "skill":
            dest_root = item.target_path
            tool_name = item.tool_key
            enabled_skills = item.metadata.get("enabled_skills")
            disabled_skills = item.metadata.get("disabled_skills")
            if source_skills.is_dir():
                for skill_dir in source_skills.iterdir():
                    if not skill_dir.is_dir():
                        continue
                    skill_name = skill_dir.name
                    if enabled_skills and skill_name not in enabled_skills:
                        continue
                    if disabled_skills and skill_name in disabled_skills:
                        continue
                    target_dir = dest_root / skill_name
                    if dry_run:
                        print(f"[DRY-RUN] Would install skill {skill_name} ({tool_name}) -> {target_dir}")
                        continue
                    install_single_skill(skill_dir, dest_root)
                if not dry_run:
                    print(f"[OK] Installed skills for {tool_name} -> {dest_root}")

        elif item.category == "config":
            example_path = item.metadata.get("example_path")
            target_path = item.target_path
            profile_name = item.metadata.get("profile")
            if dry_run:
                print(f"[DRY-RUN] Would configure {item.title}: {target_path}")
                continue
            if profile_name:
                cfg = load_tools_config(target_path)
                cfg.linter_profile = profile_name
                if "disable" in item.metadata:
                    cfg.linter_disable = item.metadata["disable"]
                if "enable" in item.metadata:
                    cfg.linter_enable = item.metadata["enable"]
                save_tools_config(target_path, cfg)
                print(f"[OK] Configured linter profile '{profile_name}': {target_path}")
            elif example_path and Path(example_path).is_file() and not target_path.exists():
                shutil.copy2(example_path, target_path)
                print(f"[OK] Initialized custom linter config: {target_path}")

        elif item.category == "git-hook":
            if dry_run:
                print(f"[DRY-RUN] Would install git pre-commit hook in: {workspace}")
                continue
            from install_hooks import install_hook
            install_hook(workspace, action=action)


def run_interactive_wizard(workspace_override: Path | None = None, dry_run: bool = False) -> None:
    print("=" * 70)
    print("             Developer AI Tools Setup & Configuration Wizard")
    print("=" * 70)
    print("This wizard configures AI assistants (Claude Code, Cursor, Cline,")
    print("Google Antigravity, OpenAI Codex, Windsurf, Copilot, and Aider)")
    print("with unified coding standards, AST linting, MCP tools, and skills.")
    print(f"Repository directory: {REPO_ROOT}")
    print(f"Linter script:        {LINTER_SCRIPT}")

    target_workspace = (workspace_override or Path.cwd()).resolve()
    print(f"Workspace directory:  {target_workspace}\n")

    tool_defs = get_tool_definitions(target_workspace)
    tool_keys = list(tool_defs.keys())

    detected = detect_installed_tools(target_workspace)
    if detected:
        detected_names = [tool_defs[k]["name"] for k in detected if k in tool_defs]
        print(f"[+] Detected AI tools on your system: {', '.join(detected_names)}")
    else:
        print("[i] No existing AI assistant configurations detected.")

    print("\nChoose setup mode:")
    print("  [1] Express Setup (Recommended: auto-detects tools, sets up workspace with Standard profile)")
    print("  [2] Custom Guided Setup (Configure tools, scope, profile, skills, and hooks step-by-step)")
    print("  [3] Diagnostic Health Doctor (Audit installed tools, paths, and skills)")
    print("  [4] Revert / Clean Uninstall (Remove ai-dev-tools rules and settings)")
    print("")

    try:
        mode_input = input("Select mode [1-4, default 1]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n[-] Setup cancelled.")
        return

    if mode_input in ("3", "doctor", "health"):
        print("\n>>> Running Environment Health Doctor...")
        subprocess.run([sys.executable, str(REPO_ROOT / "scripts" / "doctor.py")])
        return

    if mode_input in ("4", "revert", "uninstall", "remove"):
        print("\n>>> Reverting ai-dev-tools configurations...")
        selected = detected if detected else tool_keys
        remove_tool_targets(selected, "workspace", target_workspace, dry_run=dry_run)
        configure_mcp_servers(REPO_ROOT, "workspace", target_workspace, selected, dry_run=dry_run, remove=True)
        configure_skills(REPO_ROOT, "workspace", target_workspace, tools=selected, dry_run=dry_run, remove=True)
        print("\n[OK] Cleanup complete.")
        return

    if mode_input in ("2", "custom", "guided"):
        print("\nStep 1: Choose AI Tools to Configure")
        print("  0) [ALL] Configure all supported AI tools")
        for index, key in enumerate(tool_keys, 1):
            tag = " [detected]" if key in detected else ""
            print(f"  {index}) {tool_defs[key]['name']} ({key}){tag}")
        print("")

        default_tool_sel = "0" if not detected else ",".join(str(tool_keys.index(k) + 1) for k in detected)
        selection = input(f"Select tools [0-{len(tool_keys)} or comma-separated, default {default_tool_sel}]: ").strip()
        if not selection:
            selected_tools = detected if detected else tool_keys
        elif selection == "0":
            selected_tools = tool_keys
        else:
            selected_tools = []
            for part in selection.split(","):
                part_str = part.strip()
                if part_str.isdigit():
                    num_idx = int(part_str) - 1
                    if 0 <= num_idx < len(tool_keys):
                        selected_tools.append(tool_keys[num_idx])
                elif part_str in tool_defs:
                    selected_tools.append(part_str)
            if not selected_tools:
                selected_tools = detected if detected else tool_keys

        print(f"\n[+] Selected tools: {', '.join(selected_tools)}")

        print("\nStep 2: Choose Configuration Scope")
        print("  1) Workspace (Recommended: applies only to this project directory)")
        print("  2) Global (User profile: applies to all projects on this machine)")
        print("  3) Both (Configures global user profile and this project directory)")
        scope_choice = input("Select scope [1-3, default 1]: ").strip()
        scope_map = {"1": "workspace", "2": "global", "3": "both"}
        chosen_scope = scope_map.get(scope_choice, "workspace")

        if chosen_scope in ("workspace", "both"):
            ws_in = input(f"Target workspace folder [default: {target_workspace}]: ").strip()
            if ws_in:
                target_workspace = Path(ws_in).resolve()

        print("\nStep 3: Choose Linter Rule Profile")
        print("  1) Standard (Recommended: AST safety, dependencies, and secrets with relaxed prose/comment rules)")
        print("  2) Safe (Core safety only: bugs, runtime crashes, hallucinated imports, secrets)")
        print("  3) Strict (All 91 rules active: full AST safety, style, and anti-slop)")
        print("  4) Custom (Specify custom profile name or rule exclusions)")
        prof_choice = input("Select profile [1-4, default 1]: ").strip()

        prof_map = {"1": "standard", "2": "safe", "3": "strict", "4": "custom"}
        chosen_profile = prof_map.get(prof_choice, "standard")
        chosen_disable: list[int] = []

        if chosen_profile == "custom":
            custom_name = input("Custom profile name [default: team]: ").strip() or "team"
            chosen_profile = custom_name
            skips_in = input("Enter rule codes to disable/skip (comma-separated, e.g. 1, 5, 38) [optional]: ").strip()
            if skips_in:
                for part in skips_in.split(","):
                    part_clean = part.strip()
                    if part_clean.isdigit():
                        chosen_disable.append(int(part_clean))

        print("\nStep 4: Choose Agent Skills Bundle")
        print("  1) All Skills (Recommended: 37 agent runbooks for planning, testing, and debugging)")
        print("  2) Core Safety & Testing (smart-test, tdd, exhaustive-testing, lint-and-fix, diagnosing-bugs, deps, sec)")
        print("  3) Architecture & Design (codebase-design, domain-modeling, improve-codebase-architecture, to-spec)")
        print("  4) Context & Optimization (codebase-context, doc-to-markdown, clean-encoding, pack-context)")
        print("  5) None (Skip skills installation)")
        skill_choice = input("Select skill bundle [1-5, default 1]: ").strip()
        skill_map = {"1": "all", "2": "core", "3": "architecture", "4": "context", "5": "none"}
        chosen_bundle = skill_map.get(skill_choice, "all")
        if chosen_bundle == "none":
            setup_skills = False
            enabled_skills = None
        elif chosen_bundle == "all":
            setup_skills = True
            enabled_skills = None
        else:
            setup_skills = True
            enabled_skills = SKILL_BUNDLES.get(chosen_bundle, None)

        print("\nStep 5: Choose Components to Configure")
        rules_in = input("  Install instruction rules (coding guidelines and linter commands)? [Y/n, default Y]: ").strip().lower()
        setup_rules = rules_in not in ("n", "no")

        mcp_in = input("  Configure Model Context Protocol (MCP) server for selected tools? [Y/n, default Y]: ").strip().lower()
        setup_mcp = mcp_in not in ("n", "no")

        has_git = (target_workspace / ".git").is_dir()
        if has_git:
            hook_in = input("  Install Git pre-commit hook to verify staged changes with linter? [Y/n, default Y]: ").strip().lower()
            setup_hook = hook_in not in ("n", "no")
        else:
            setup_hook = False

        plan = create_setup_plan(
            repo_root=REPO_ROOT,
            selected_tools=selected_tools,
            scope=chosen_scope,
            workspace=target_workspace,
            setup_rules=setup_rules,
            setup_mcp=setup_mcp,
            setup_skills=setup_skills,
            enabled_skills=enabled_skills,
            linter_profile=chosen_profile,
            linter_disable=chosen_disable,
            setup_git_hook=setup_hook,
        )

    else:
        # Express setup (Option 1)
        selected_tools = detected if detected else tool_keys
        has_git = (target_workspace / ".git").is_dir()
        plan = create_setup_plan(
            repo_root=REPO_ROOT,
            selected_tools=selected_tools,
            scope="workspace",
            workspace=target_workspace,
            setup_rules=True,
            setup_mcp=True,
            setup_skills=True,
            linter_profile="standard",
            setup_git_hook=has_git,
        )

    approved = ask_user_plan_confirmation(plan, target_workspace)
    if approved:
        print("\n>>> Applying approved configuration actions...")
        execute_setup_plan(approved, target_workspace, action="append", dry_run=dry_run)
        print("\nSetup finished. Selected AI tools configured successfully.")


def interactive_menu() -> tuple[list[str], str, Path, bool]:
    tool_defs = get_tool_definitions()
    tool_keys = list(tool_defs.keys())
    return tool_keys, "global", Path.cwd(), True


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
        "-y",
        "--yes",
        action="store_true",
        help="Automatically approve all planned actions without interactive prompts.",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick express configuration using auto-detected tools and standard profile.",
    )
    parser.add_argument(
        "--hooks",
        action="store_true",
        help="Install git pre-commit hook to lint staged files before commit.",
    )
    parser.add_argument(
        "--skill-bundle",
        choices=["all", "core", "architecture", "context", "workflow"],
        help="Install a predefined bundle of agent skills.",
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
        "--profile",
        choices=["strict", "standard", "safe"],
        help="Linter rule profile to configure in .aitools.toml (default: strict).",
    )
    parser.add_argument(
        "--disable-rules",
        help="Comma-separated rule codes to disable in .aitools.toml (e.g. 1,5,38).",
    )
    parser.add_argument(
        "--enable-rules",
        help="Comma-separated rule codes to enable in .aitools.toml (e.g. 11,25).",
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

    if not args.tools and not args.quick and len(sys.argv) == 1:
        run_interactive_wizard(workspace_override=args.workspace, dry_run=args.dry_run)
        return

    if args.quick:
        detected_tools = detect_installed_tools(args.workspace)
        selected = detected_tools if detected_tools else list(tool_defs.keys())
        scope = "workspace"
        profile = args.profile or "standard"
        setup_hook = (args.workspace / ".git").is_dir() or args.hooks
        plan = create_setup_plan(
            repo_root=REPO_ROOT,
            selected_tools=selected,
            scope=scope,
            workspace=args.workspace,
            action=args.action,
            setup_rules=True,
            setup_mcp=not args.no_mcp,
            setup_skills=not args.no_skills,
            init_custom_config=True,
            linter_profile=profile,
            setup_git_hook=setup_hook,
        )
        approved = plan
        print("\n>>> Applying express configuration actions...")
        execute_setup_plan(approved, args.workspace, action=args.action, dry_run=args.dry_run)
        print("\n[OK] Express setup complete. AI tools configured successfully.")
        return

    tools_arg = args.tools or "all"
    if tools_arg.strip().lower() == "all":
        selected = list(tool_defs.keys())
    else:
        selected = [tool.strip().lower() for tool in tools_arg.split(",") if tool.strip()]

    skill_targets = [item.strip().lower() for item in args.skills_tools.split(",")] if args.skills_tools else loaded_cfg.skill_targets
    if "all" in skill_targets:
        skill_targets = ["antigravity", "claude", "cursor", "windsurf", "cline", "codex"]

    if args.skill_bundle and args.skill_bundle in SKILL_BUNDLES:
        bundle_skills = SKILL_BUNDLES[args.skill_bundle]
        enabled_skills = bundle_skills if bundle_skills else None
    else:
        enabled_skills = [name.strip() for name in args.skills.split(",")] if args.skills else loaded_cfg.enabled_skills

    disabled_skills = [name.strip() for name in args.exclude_skills.split(",")] if args.exclude_skills else loaded_cfg.disabled_skills

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

    disable_rules = (
        [int(c.strip()) for c in args.disable_rules.split(",") if c.strip().isdigit()]
        if args.disable_rules
        else None
    )
    enable_rules = (
        [int(c.strip()) for c in args.enable_rules.split(",") if c.strip().isdigit()]
        if args.enable_rules
        else None
    )

    plan = create_setup_plan(
        repo_root=REPO_ROOT,
        selected_tools=selected,
        scope=args.scope,
        workspace=args.workspace,
        action=args.action,
        setup_rules=True,
        setup_mcp=not args.no_mcp,
        setup_skills=not args.no_skills,
        skill_targets=skill_targets,
        enabled_skills=enabled_skills,
        disabled_skills=disabled_skills,
        init_custom_config=True,
        linter_profile=args.profile,
        linter_disable=disable_rules,
        linter_enable=enable_rules,
        setup_git_hook=args.hooks,
    )

    if not args.yes and sys.stdin.isatty():
        approved = ask_user_plan_confirmation(plan, args.workspace)
    else:
        approved = plan

    if approved:
        print("\n>>> Applying approved configuration actions...")
        execute_setup_plan(approved, args.workspace, action=args.action, dry_run=args.dry_run)
        print("\nConfiguration finished! All AI tools reference:")
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
