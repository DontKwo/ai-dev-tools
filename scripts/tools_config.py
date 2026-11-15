"""Configuration loader and generator for .aitools.toml declarative settings."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import tomllib  # noqa: 22
except ModuleNotFoundError:
    try:
        import tomli as tomllib  # noqa: 22
    except ModuleNotFoundError:
        tomllib = None  # type: ignore

DEFAULT_TOOLS = [
    "claude",
    "cursor",
    "cline",
    "antigravity",
    "codex",
    "windsurf",
    "copilot",
    "aider",
]

DEFAULT_SKILL_TARGETS = [
    "antigravity",
    "agents",
    "claude",
    "cursor",
    "windsurf",
    "cline",
    "codex",
]


@dataclass
class AiToolsConfig:
    tools: list[str] = field(default_factory=lambda: list(DEFAULT_TOOLS))
    skill_targets: list[str] = field(default_factory=lambda: list(DEFAULT_SKILL_TARGETS))
    enabled_skills: list[str] = field(default_factory=list)
    disabled_skills: list[str] = field(default_factory=list)
    linter_level: str = "strict"
    linter_diff_only: bool = True
    linter_skip: list[int] = field(default_factory=list)
    linter_only: list[int] = field(default_factory=list)
    linter_ui_evidence: str = ""
    ui_frameworks: list[str] = field(default_factory=list)
    config_path: Path | None = None

    def is_skill_enabled(self, skill_name: str) -> bool:
        if self.disabled_skills and skill_name in self.disabled_skills:
            return False
        if self.enabled_skills:
            return skill_name in self.enabled_skills
        return True


def _parse_value(raw: str) -> Any:
    parsed = raw.strip()
    if parsed.lower() == "true":
        return True
    if parsed.lower() == "false":
        return False
    if parsed.isdigit():
        return int(parsed)
    if parsed.startswith('"') and parsed.endswith('"'):
        return parsed[1:-1]
    if parsed.startswith("'") and parsed.endswith("'"):
        return parsed[1:-1]
    if parsed.startswith("[") and parsed.endswith("]"):
        items = [elem.strip() for elem in parsed[1:-1].split(",") if elem.strip()]
        return [_parse_value(elem) for elem in items]
    return parsed


def parse_toml_content(content: str) -> dict[str, Any]:
    if tomllib is not None:
        try:
            return tomllib.loads(content)
        except Exception:
            return {}

    data: dict[str, Any] = {}
    current_section: dict[str, Any] = data
    for line in content.splitlines():
        clean = line.strip()
        if not clean or clean.startswith("#"):
            continue
        if clean.startswith("[") and clean.endswith("]"):
            section_name = clean[1:-1].strip()
            data[section_name] = {}
            current_section = data[section_name]
            continue
        if "=" in clean:
            key, raw_val = clean.split("=", 1)
            key = key.strip().strip('"').strip("'")
            current_section[key] = _parse_value(raw_val)
    return data


def generate_default_config() -> str:
    lines = [
        "# Developer AI Development Tools Configuration",
        "# Place this file at repository root as .aitools.toml or in your home directory.",
        "",
        "[tools]",
        "# Supported: claude, cursor, cline, antigravity, codex, windsurf, copilot, aider",
        'configured = ["claude", "cursor", "cline", "antigravity", "codex", "windsurf", "aider"]',
        "",
        "[skills]",
        "# Target editors for agent skills installation",
        'targets = ["antigravity", "agents", "claude", "cursor", "windsurf", "cline", "codex"]',
        "# Enabled skills whitelist (empty list means all available skills are enabled)",
        "enabled = []",
        "# Disabled skills blacklist (e.g. ['doc-to-markdown'])",
        "disabled = []",
        "",
        "[linter]",
        '# Verification level: standard, strict, full',
        'level = "strict"',
        "# Scope to git diff by default inside git repositories",
        "diff_only = true",
        "# Rule codes to skip globally for this repo (e.g. [38])",
        "skip = []",
        "# Run specific rule codes only",
        "only = []",
        '# Custom path to runtime UI interaction evidence',
        'ui_evidence = ""',
        "",
        "[ui]",
        "# Framework hints: pyqt, web, android, flutter, ios, tkinter, wxpython, kivy, textual, dotnet",
        "frameworks = []",
        "",
    ]
    return "\n".join(lines)


def load_tools_config(root_or_file: Path | None = None) -> AiToolsConfig:
    candidate_paths: list[Path] = []

    if root_or_file is not None:
        target = Path(root_or_file).resolve()
        if target.is_file():
            candidate_paths.append(target)
        else:
            candidate_paths.extend([
                target / ".aitools.toml",
                target / "ai-dev-tools.toml",
                target / "pyproject.toml",
            ])
    else:
        cwd = Path.cwd().resolve()
        candidate_paths.extend([
            cwd / ".aitools.toml",
            cwd / "ai-dev-tools.toml",
            cwd / "pyproject.toml",
        ])

    home = Path(os.environ.get("USERPROFILE") or os.environ.get("HOME") or "~").expanduser()
    candidate_paths.extend([
        home / ".config" / "ai-dev-tools" / "config.toml",
        home / ".aitools.toml",
    ])

    for path in candidate_paths:
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8")
            data = parse_toml_content(content)
            if path.name == "pyproject.toml":
                data = data.get("tool", {}).get("ai-dev-tools", {})
                if not data:
                    continue

            return _build_config_from_dict(data, path)
        except OSError:
            continue

    return AiToolsConfig()


def _build_config_from_dict(data: dict[str, Any], path: Path) -> AiToolsConfig:
    cfg = AiToolsConfig(config_path=path)

    tools_sec = data.get("tools", {})
    if isinstance(tools_sec, dict) and "configured" in tools_sec:
        cfg.tools = [str(item) for item in tools_sec.get("configured", [])]

    skills_sec = data.get("skills", {})
    if isinstance(skills_sec, dict):
        if "targets" in skills_sec:
            cfg.skill_targets = [str(item) for item in skills_sec.get("targets", [])]
        if "enabled" in skills_sec:
            cfg.enabled_skills = [str(item) for item in skills_sec.get("enabled", [])]
        if "disabled" in skills_sec:
            cfg.disabled_skills = [str(item) for item in skills_sec.get("disabled", [])]

    linter_sec = data.get("linter", {})
    if isinstance(linter_sec, dict):
        cfg.linter_level = str(linter_sec.get("level", "strict"))
        cfg.linter_diff_only = bool(linter_sec.get("diff_only", True))
        cfg.linter_skip = [int(code) for code in linter_sec.get("skip", []) if str(code).isdigit()]
        cfg.linter_only = [int(code) for code in linter_sec.get("only", []) if str(code).isdigit()]
        cfg.linter_ui_evidence = str(linter_sec.get("ui_evidence", ""))

    ui_sec = data.get("ui", {})
    if isinstance(ui_sec, dict) and "frameworks" in ui_sec:
        cfg.ui_frameworks = [str(item) for item in ui_sec.get("frameworks", [])]

    return cfg


def save_tools_config(path: Path, config: AiToolsConfig) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Developer AI Development Tools Configuration",
        "",
        "[tools]",
        f"configured = {config.tools!r}",
        "",
        "[skills]",
        f"targets = {config.skill_targets!r}",
        f"enabled = {config.enabled_skills!r}",
        f"disabled = {config.disabled_skills!r}",
        "",
        "[linter]",
        f'level = "{config.linter_level}"',
        f"diff_only = {str(config.linter_diff_only).lower()}",
        f"skip = {config.linter_skip!r}",
        f"only = {config.linter_only!r}",
        f'ui_evidence = "{config.linter_ui_evidence}"',
        "",
        "[ui]",
        f"frameworks = {config.ui_frameworks!r}",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
