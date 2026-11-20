"""Interactive Graphical Setup Wizard for AI-Dev-Tools."""
from __future__ import annotations

import importlib
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from apply_config import (
    ConfigExecutionPlan,
    build_plan_from_config,
    execute_plan,
    format_plan_preview,
)
from yaml_utils import dump_yaml_file, load_yaml_file


@dataclass
class SetupGuiModel:
    workspace: str = field(default_factory=lambda: str(Path.cwd()))
    scope: str = "workspace"
    write_mode: str = "append"
    profile_level: str = "strict"
    tools: dict[str, bool] = field(
        default_factory=lambda: {
            "claude": True,
            "cursor": True,
            "cline": True,
            "antigravity": True,
            "codex": True,
            "windsurf": True,
            "copilot": True,
            "aider": True,
        }
    )
    targets: dict[str, bool] = field(
        default_factory=lambda: {
            "claude_md": True,
            "agents_md": True,
            "cursorrules": True,
            "clinerules": True,
            "windsurfrules": True,
            "aider_conventions": True,
            "copilot_instructions": True,
        }
    )
    mcp_enabled: bool = True
    skills_enabled: bool = True
    skill_bundle: str = "all"
    git_hook_enabled: bool = True

    def to_config_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "scope": self.scope,
            "write_mode": self.write_mode,
            "profile": {
                "level": self.profile_level,
                "skip_rules": [],
                "description": f"Configured via GUI with {self.profile_level} profile.",
            },
            "tools": dict(self.tools),
            "targets": dict(self.targets),
            "mcp": {
                "enabled": self.mcp_enabled,
                "server_name": "ai-dev-tools",
            },
            "skills": {
                "enabled": self.skills_enabled,
                "bundle": self.skill_bundle,
            },
            "hooks": {
                "git_pre_commit": self.git_hook_enabled,
                "command": "uv run --no-project python scripts/claudemd_linter.py . --diff",
            },
        }

    def load_from_config_dict(self, cfg: dict[str, Any]) -> None:
        if "scope" in cfg:
            self.scope = str(cfg["scope"])
        if "write_mode" in cfg:
            self.write_mode = str(cfg["write_mode"])
        prof = cfg.get("profile", {})
        if isinstance(prof, dict):
            self.profile_level = str(prof.get("level", "strict"))
        elif isinstance(prof, str):
            self.profile_level = prof

        tools_sec = cfg.get("tools", {})
        if isinstance(tools_sec, dict):
            for tool_name, is_tool_enabled in tools_sec.items():
                self.tools[tool_name.lower()] = bool(is_tool_enabled)

        targets_sec = cfg.get("targets", {})
        if isinstance(targets_sec, dict):
            for target_name, is_target_enabled in targets_sec.items():
                self.targets[target_name.lower()] = bool(is_target_enabled)

        mcp_sec = cfg.get("mcp", {})
        if isinstance(mcp_sec, dict):
            self.mcp_enabled = bool(mcp_sec.get("enabled", True))

        skills_sec = cfg.get("skills", {})
        if isinstance(skills_sec, dict):
            self.skills_enabled = bool(skills_sec.get("enabled", True))
            self.skill_bundle = str(skills_sec.get("bundle", "all"))

        hooks_sec = cfg.get("hooks", {})
        if isinstance(hooks_sec, dict):
            self.git_hook_enabled = bool(hooks_sec.get("git_pre_commit", True))

    def load_preset(self, preset_name: str) -> None:
        preset_file = REPO_ROOT / "configs" / f"{preset_name}.yaml"
        if preset_file.is_file():
            loaded = load_yaml_file(preset_file)
            self.load_from_config_dict(loaded)

    def calculate_plan(self) -> ConfigExecutionPlan:
        cfg = self.to_config_dict()
        return build_plan_from_config(cfg, Path(self.workspace).resolve())


def _import_tk_modules() -> tuple[Any, Any, Any, Any]:
    tk_mod = importlib.import_module("tkinter")
    ttk_mod = importlib.import_module("tkinter.ttk")
    fd_mod = importlib.import_module("tkinter.filedialog")
    mb_mod = importlib.import_module("tkinter.messagebox")
    return tk_mod, ttk_mod, fd_mod, mb_mod


class SetupApp:
    def __init__(self, root: Any, model: SetupGuiModel | None = None) -> None:
        self.root = root
        self.model = model or SetupGuiModel()
        self.tk, self.ttk, self.fd, self.mb = _import_tk_modules()
        self.root.title("AI-Dev-Tools Setup Assistant")
        self.root.geometry("820x760")
        self.root.minsize(700, 600)
        self._init_vars()
        self._build_ui()

    def _init_vars(self) -> None:
        self.ws_var = self.tk.StringVar(value=self.model.workspace)
        self.mode_var = self.tk.StringVar(value=self.model.write_mode)
        self.profile_var = self.tk.StringVar(value=self.model.profile_level)
        self.mcp_var = self.tk.BooleanVar(value=self.model.mcp_enabled)
        self.skills_var = self.tk.BooleanVar(value=self.model.skills_enabled)
        self.bundle_var = self.tk.StringVar(value=self.model.skill_bundle)
        self.hook_var = self.tk.BooleanVar(value=self.model.git_hook_enabled)
        self.tool_vars: dict[str, Any] = {
            tool_key: self.tk.BooleanVar(value=is_on) for tool_key, is_on in self.model.tools.items()
        }

    def _build_ui(self) -> None:
        main_frame = self.ttk.Frame(self.root, padding=12)
        main_frame.pack(fill=self.tk.BOTH, expand=True)

        header_lbl = self.ttk.Label(
            main_frame,
            text="AI-Dev-Tools Setup & Configuration",
            font=("Segoe UI", 15, "bold"),
        )
        header_lbl.pack(anchor=self.tk.W, pady=(0, 6))

        desc_lbl = self.ttk.Label(
            main_frame,
            text="Configure coding standards, skills, MCP servers, and linter rules across your AI coding assistants.",
            font=("Segoe UI", 9),
            foreground="#555555",
        )
        desc_lbl.pack(anchor=self.tk.W, pady=(0, 10))

        ws_group = self.ttk.LabelFrame(main_frame, text="Target Workspace", padding=8)
        ws_group.pack(fill=self.tk.X, pady=4)
        ws_box = self.ttk.Frame(ws_group)
        ws_box.pack(fill=self.tk.X)
        self.ws_entry = self.ttk.Entry(ws_box, textvariable=self.ws_var)  # noqa: 46
        self.ws_entry.pack(side=self.tk.LEFT, fill=self.tk.X, expand=True, padx=(0, 6))
        self.browse_button = self.ttk.Button(ws_box, text="Browse...", command=self._browse_workspace)  # noqa: 46
        self.browse_button.pack(side=self.tk.RIGHT)

        preset_group = self.ttk.LabelFrame(main_frame, text="Presets & YAML Configuration", padding=8)
        preset_group.pack(fill=self.tk.X, pady=4)
        preset_box = self.ttk.Frame(preset_group)
        preset_box.pack(fill=self.tk.X)
        for p_name, p_label in [
            ("full", "Full (Default)"),
            ("strict", "Strict"),
            ("standard", "Standard"),
            ("safe", "Safe Profile"),
            ("minimal", "Minimal"),
        ]:
            preset_btn = self.ttk.Button(  # noqa: 46
                preset_box, text=p_label, command=lambda pn=p_name: self._apply_preset(pn)
            )
            preset_btn.pack(side=self.tk.LEFT, padx=3)
        self.load_button = self.ttk.Button(preset_box, text="Load YAML...", command=self._load_yaml_file)  # noqa: 46
        self.load_button.pack(side=self.tk.RIGHT, padx=3)
        self.save_button = self.ttk.Button(preset_box, text="Export YAML...", command=self._save_yaml_file)  # noqa: 46
        self.save_button.pack(side=self.tk.RIGHT, padx=3)

        self.notebook_widget = self.ttk.Notebook(main_frame)
        self.notebook_widget.pack(fill=self.tk.BOTH, expand=True, pady=8)

        tab_tools = self.ttk.Frame(self.notebook_widget, padding=10)
        tab_profile = self.ttk.Frame(self.notebook_widget, padding=10)
        tab_features = self.ttk.Frame(self.notebook_widget, padding=10)
        self.notebook_widget.add(tab_tools, text="AI Assistants & Tools")
        self.notebook_widget.add(tab_profile, text="Linter & Write Mode")
        self.notebook_widget.add(tab_features, text="Skills, MCP & Hooks")

        self._populate_tools_tab(tab_tools)
        self._populate_profile_tab(tab_profile)
        self._populate_features_tab(tab_features)

        btn_bar = self.ttk.Frame(main_frame, padding=6)
        btn_bar.pack(fill=self.tk.X, side=self.tk.BOTTOM)
        self.preview_button = self.ttk.Button(  # noqa: 46
            btn_bar, text="Preview Changes & Safety Check", command=self._preview_plan
        )
        self.preview_button.pack(side=self.tk.LEFT, padx=6)
        self.apply_button = self.ttk.Button(  # noqa: 46
            btn_bar, text="Apply Changes", command=self._execute_plan
        )
        self.apply_button.pack(side=self.tk.RIGHT, padx=6)

    def _populate_tools_tab(self, parent: Any) -> None:
        lbl = self.ttk.Label(
            parent,
            text="Select which AI assistants will receive instruction files in this workspace:",
            font=("Segoe UI", 9, "italic"),
        )
        lbl.pack(anchor=self.tk.W, pady=(0, 6))

        tool_meta = [
            ("claude", "Claude Code (CLAUDE.md) - Official CLI & Claude Desktop rules"),
            ("cursor", "Cursor IDE (.cursorrules & .cursor/rules/) - Editor rules"),
            ("antigravity", "Google Antigravity (AGENTS.md & .agent/rules/) - Native agent rules"),
            ("cline", "Cline & Roo Code (.clinerules) - Autonomous agent rules"),
            ("windsurf", "Windsurf IDE (.windsurfrules) - Cascade rules"),
            ("copilot", "GitHub Copilot (.github/copilot-instructions.md) - Workspace rules"),
            ("aider", "Aider (.aider.conventions.md) - Git pairing assistant rules"),
            ("codex", "OpenAI Codex & ChatGPT (instructions.md) - Agent rules"),
        ]
        for key, text in tool_meta:
            if key in self.tool_vars:
                chk = self.ttk.Checkbutton(parent, text=text, variable=self.tool_vars[key])  # noqa: 46
                chk.pack(anchor=self.tk.W, pady=3)

    def _populate_profile_tab(self, parent: Any) -> None:
        mode_grp = self.ttk.LabelFrame(parent, text="File Write Mode", padding=8)
        mode_grp.pack(fill=self.tk.X, pady=4)

        modes = [
            ("append", "Append (Safe) - Preserves existing custom content; updates bounded block."),
            ("overwrite", "Overwrite (Clean Slate) - Replaces file; saves backup to filename.bak."),
            ("skip", "Skip - Keeps existing files untouched; only creates missing ones."),
        ]
        for m_val, m_text in modes:
            rb = self.ttk.Radiobutton(mode_grp, text=m_text, value=m_val, variable=self.mode_var)  # noqa: 46
            rb.pack(anchor=self.tk.W, pady=2)

        prof_grp = self.ttk.LabelFrame(parent, text="Linter & Rule Strictness Profile", padding=8)
        prof_grp.pack(fill=self.tk.X, pady=6)

        profiles = [
            ("strict", "Strict (Default) - Full enforcement of all 91 rules, AST safety, anti-AI prose."),
            ("standard", "Standard - Core AST safety and security with relaxed prose and comment rules."),
            ("safe", "Safe Profile - Essential bug and secret checks with zero stylistic churn."),
            ("minimal", "Minimal - Lightweight AST protections only."),
        ]
        for p_val, p_text in profiles:
            prof_rb = self.ttk.Radiobutton(prof_grp, text=p_text, value=p_val, variable=self.profile_var)  # noqa: 46
            prof_rb.pack(anchor=self.tk.W, pady=2)

    def _populate_features_tab(self, parent: Any) -> None:
        self.mcp_chk = self.ttk.Checkbutton(  # noqa: 46
            parent,
            text="Model Context Protocol (MCP) - Register repository tools with AI assistants",
            variable=self.mcp_var,
        )
        self.mcp_chk.pack(anchor=self.tk.W, pady=6)

        self.skills_chk = self.ttk.Checkbutton(  # noqa: 46
            parent,
            text="Install AI Agent Skills (.agent/skills/, .claude/skills/, .cursor/skills/)",
            variable=self.skills_var,
        )
        self.skills_chk.pack(anchor=self.tk.W, pady=4)

        b_frame = self.ttk.Frame(parent)
        b_frame.pack(anchor=self.tk.W, padx=24, pady=2)
        b_lbl = self.ttk.Label(b_frame, text="Skills Bundle:")
        b_lbl.pack(side=self.tk.LEFT, padx=(0, 6))
        self.bundle_combo = self.ttk.Combobox(  # noqa: 46
            b_frame,
            textvariable=self.bundle_var,
            values=["all", "core", "architecture", "context", "workflow", "none"],
            state="readonly",
            width=16,
        )
        self.bundle_combo.pack(side=self.tk.LEFT)

        self.hook_chk = self.ttk.Checkbutton(  # noqa: 46
            parent,
            text="Git Pre-Commit Hook - Automatically verify staged code before commits",
            variable=self.hook_var,
        )
        self.hook_chk.pack(anchor=self.tk.W, pady=8)

    def _sync_model_from_ui(self) -> None:
        self.model.workspace = self.ws_var.get().strip()
        self.model.write_mode = self.mode_var.get()
        self.model.profile_level = self.profile_var.get()
        self.model.mcp_enabled = self.mcp_var.get()
        self.model.skills_enabled = self.skills_var.get()
        self.model.skill_bundle = self.bundle_var.get()
        self.model.git_hook_enabled = self.hook_var.get()
        for tool_key, var in self.tool_vars.items():
            self.model.tools[tool_key] = var.get()

    def _sync_ui_from_model(self) -> None:
        self.ws_var.set(self.model.workspace)
        self.mode_var.set(self.model.write_mode)
        self.profile_var.set(self.model.profile_level)
        self.mcp_var.set(self.model.mcp_enabled)
        self.skills_var.set(self.model.skills_enabled)
        self.bundle_var.set(self.model.skill_bundle)
        self.hook_var.set(self.model.git_hook_enabled)
        for tool_key, is_active in self.model.tools.items():
            if tool_key in self.tool_vars:
                self.tool_vars[tool_key].set(is_active)

    def _browse_workspace(self) -> None:
        chosen = self.fd.askdirectory(initialdir=self.ws_var.get() or os.getcwd())
        if chosen:
            self.ws_var.set(chosen)

    def _apply_preset(self, preset_name: str) -> None:
        self.model.load_preset(preset_name)
        self._sync_ui_from_model()
        self.mb.showinfo("Preset Loaded", f"Applied '{preset_name}' configuration preset.")

    def _load_yaml_file(self) -> None:
        filepath = self.fd.askopenfilename(
            filetypes=[("YAML Configuration", "*.yaml;*.yml"), ("All Files", "*.*")]
        )
        if filepath:
            data = load_yaml_file(Path(filepath))
            self.model.load_from_config_dict(data)
            self._sync_ui_from_model()
            self.mb.showinfo("Config Loaded", f"Successfully loaded configuration from {Path(filepath).name}")

    def _save_yaml_file(self) -> None:
        self._sync_model_from_ui()
        filepath = self.fd.asksaveasfilename(
            defaultextension=".yaml",
            filetypes=[("YAML Configuration", "*.yaml;*.yml")],
            initialfile="config.yaml",
        )
        if filepath:
            dump_yaml_file(self.model.to_config_dict(), Path(filepath))
            self.mb.showinfo("Saved", f"Exported configuration to {Path(filepath).name}")

    def _preview_plan(self) -> None:
        self._sync_model_from_ui()
        plan = self.model.calculate_plan()
        preview_text = format_plan_preview(plan)

        top = self.tk.Toplevel(self.root)
        top.title("Configuration Preview & Safety Check")
        top.geometry("740x550")

        preview_text_area = self.tk.Text(top, wrap=self.tk.NONE, font=("Consolas", 9))
        preview_text_area.insert("1.0", preview_text)
        preview_text_area.config(state=self.tk.DISABLED)
        preview_text_area.pack(fill=self.tk.BOTH, expand=True, padx=8, pady=8)

        close_btn = self.ttk.Button(top, text="Close Preview", command=top.destroy)  # noqa: 46
        close_btn.pack(pady=(0, 8))

    def _execute_plan(self) -> None:
        self._sync_model_from_ui()
        plan = self.model.calculate_plan()

        loss_risks = [it.risk_description for it in plan.rule_actions if it.data_loss_risk]
        if loss_risks:
            formatted_risks = "\n".join(loss_risks)
            warn_msg = f"POTENTIAL DATA LOSS WARNING:\n\n{formatted_risks}\n\nBackups will be created (.bak). Proceed?"
            confirmed = self.mb.askyesno("Confirm Data Loss", warn_msg, icon=self.mb.WARNING)
            if not confirmed:
                return

        successes, errors = execute_plan(plan, dry_run=False)
        if errors > 0:
            self.mb.showwarning(
                "Execution Warning",
                f"Configuration completed with {errors} issue(s). Check output log for details.",
            )
        else:
            self.mb.showinfo(
                "Setup Successful",
                f"Successfully configured workspace!\nModified/Created {successes} component(s).",
            )


def main() -> None:
    tk_mod, _, _, _ = _import_tk_modules()
    root = tk_mod.Tk()
    SetupApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
