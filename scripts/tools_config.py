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

BUILTIN_PROFILES: dict[str, dict[str, Any]] = {
    "strict": {
        "level": "strict",
        "skip": [],
        "description": "All 91 rules active. Strict AST safety, writing hygiene, and code structure.",
    },
    "standard": {
        "level": "standard",
        "skip": [1, 5, 17, 38],
        "description": "AST safety, dependencies, and secrets with relaxed prose and comment rules.",
    },
    "safe": {
        "level": "standard",
        "skip": [1, 2, 3, 4, 5, 6, 7, 8, 11, 17, 18, 19, 23, 24, 25, 28, 31, 33, 34, 38],
        "description": "Essential bug, hallucination, and security checks without opinionated styling.",
    },
}


@dataclass
class AiToolsConfig:
    tools: list[str] = field(default_factory=lambda: list(DEFAULT_TOOLS))
    skill_targets: list[str] = field(default_factory=lambda: list(DEFAULT_SKILL_TARGETS))
    enabled_skills: list[str] = field(default_factory=list)
    disabled_skills: list[str] = field(default_factory=list)
    linter_profile: str = "strict"
    linter_level: str = "strict"
    linter_diff_only: bool = True
    linter_skip: list[int] = field(default_factory=list)
    linter_only: list[int] = field(default_factory=list)
    linter_enable: list[int] = field(default_factory=list)
    linter_disable: list[int] = field(default_factory=list)
    linter_profiles: dict[str, dict[str, Any]] = field(default_factory=dict)
    linter_ui_evidence: str = ""
    ui_frameworks: list[str] = field(default_factory=list)
    single_os: str = ""
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


def resolve_linter_profile(
    profile_name: str,
    custom_profiles: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    prof_key = profile_name.strip().lower()
    if custom_profiles and prof_key in custom_profiles:
        return custom_profiles[prof_key]
    if prof_key in BUILTIN_PROFILES:
        return BUILTIN_PROFILES[prof_key]
    return BUILTIN_PROFILES["strict"]


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
        "# Profile presets: 'strict' (default, 91 rules), 'standard' (relaxed style), 'safe' (bugs/safety only)",
        'profile = "strict"',
        "# Verification level override: standard, strict, full",
        'level = "strict"',
        "# Scope to git diff by default inside git repositories",
        "diff_only = true",
        "# Manually disable specific rule codes (e.g. [1, 5, 38])",
        "disable = []",
        "# Manually enable specific rule codes (overrides profile skips)",
        "enable = []",
        "# Rule codes to skip globally (alias for disable)",
        "skip = []",
        "# Run specific rule codes only",
        "only = []",
        '# Custom path to runtime UI interaction evidence',
        'ui_evidence = ""',
        "",
        "# Custom named profile example:",
        "# [linter.profiles.team]",
        '# level = "standard"',
        "# skip = [1, 5, 38]",
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
    custom_profiles: dict[str, dict[str, Any]] = {}
    if isinstance(linter_sec, dict):
        raw_profiles = linter_sec.get("profiles", {})
        if isinstance(raw_profiles, dict):
            for pname, pdata in raw_profiles.items():
                if isinstance(pdata, dict):
                    custom_profiles[pname.strip().lower()] = pdata

    for k, v in data.items():
        if k.startswith("linter.profiles.") and isinstance(v, dict):
            pname = k.split("linter.profiles.", 1)[1].strip().lower()
            custom_profiles[pname] = v

    cfg.linter_profiles = custom_profiles

    if isinstance(linter_sec, dict):
        cfg.linter_profile = str(linter_sec.get("profile", "strict")).strip().lower()
        cfg.linter_diff_only = bool(linter_sec.get("diff_only", True))
        cfg.linter_ui_evidence = str(linter_sec.get("ui_evidence", ""))

        explicit_skip = [int(code) for code in linter_sec.get("skip", []) if str(code).isdigit()]
        cfg.linter_disable = [int(code) for code in linter_sec.get("disable", []) if str(code).isdigit()]
        cfg.linter_enable = [int(code) for code in linter_sec.get("enable", []) if str(code).isdigit()]
        explicit_only = [int(code) for code in linter_sec.get("only", []) if str(code).isdigit()]

        profile_info = resolve_linter_profile(cfg.linter_profile, cfg.linter_profiles)
        if "level" in linter_sec:
            cfg.linter_level = str(linter_sec["level"])
        else:
            cfg.linter_level = str(profile_info.get("level", "strict"))

        base_skip = set(int(c) for c in profile_info.get("skip", []) if str(c).isdigit())
        base_only = set(int(c) for c in profile_info.get("only", []) if str(c).isdigit())

        combined_skip = (base_skip | set(explicit_skip) | set(cfg.linter_disable)) - set(cfg.linter_enable)
        cfg.linter_skip = sorted(list(combined_skip))

        combined_only = base_only | set(explicit_only)
        cfg.linter_only = sorted(list(combined_only))

    ui_sec = data.get("ui", {})
    if isinstance(ui_sec, dict) and "frameworks" in ui_sec:
        cfg.ui_frameworks = [str(item) for item in ui_sec.get("frameworks", [])]

    proj_sec = data.get("project", {})
    if isinstance(proj_sec, dict) and "single_os" in proj_sec:
        cfg.single_os = str(proj_sec.get("single_os", "")).strip().lower()

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
        f'profile = "{config.linter_profile}"',
        f'level = "{config.linter_level}"',
        f"diff_only = {str(config.linter_diff_only).lower()}",
        f"disable = {config.linter_disable!r}",
        f"enable = {config.linter_enable!r}",
        f"skip = {config.linter_skip!r}",
        f"only = {config.linter_only!r}",
        f'ui_evidence = "{config.linter_ui_evidence}"',
        "",
    ]
    if config.linter_profiles:
        for pname, pdata in config.linter_profiles.items():
            lines.append(f"[linter.profiles.{pname}]")
            for k, v in pdata.items():
                if isinstance(v, str):
                    lines.append(f'{k} = "{v}"')
                else:
                    lines.append(f"{k} = {v!r}")
            lines.append("")
    lines.extend([
        "[ui]",
        f"frameworks = {config.ui_frameworks!r}",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")
