"""Configuration loader for .uilint.toml with autodetected defaults."""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import tomllib  # noqa: 22
except ModuleNotFoundError:
    tomllib = None  # type: ignore


@dataclass
class UiConfig:
    frameworks: list[str] = field(default_factory=list)
    id_pattern: str = r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$"
    tooltips_registry: str = ""
    strings_registry: str = ""
    theme_registry: str = ""
    ui_globs: list[str] = field(default_factory=lambda: ["tests/ui/**", "tests/**/test_ui*.py"])
    evidence_path: str = "ui_evidence.json"
    exhaustive_state_max: int = 8
    ordered_triples_max_actions: int = 6
    max_cases_per_context: int = 5000
    seed: int = 1234
    overlap_tolerance_px: float = 1.0
    matrix: str = "smoke"
    waivers: dict[str, str] = field(default_factory=dict)

    def matches_id_pattern(self, identifier: str) -> bool:
        return bool(re.match(self.id_pattern, identifier))

    def is_waived(self, control_id: str) -> bool:
        return control_id in self.waivers


def _parse_toml_simple(content: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current_section: dict[str, Any] = data
    section_name = ""

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
            key, raw_value = clean.split("=", 1)
            key = key.strip().strip('"').strip("'")
            raw_value = raw_value.strip()
            if raw_value.startswith('"') and raw_value.endswith('"'):
                current_section[key] = raw_value[1:-1]
            elif raw_value.startswith("'") and raw_value.endswith("'"):
                current_section[key] = raw_value[1:-1]
            elif raw_value.startswith("[") and raw_value.endswith("]"):
                items = [x.strip().strip('"').strip("'") for x in raw_value[1:-1].split(",") if x.strip()]
                current_section[key] = items
            elif raw_value.isdigit():
                current_section[key] = int(raw_value)
            else:
                current_section[key] = raw_value
    return data


def load_ui_config(root: Path) -> UiConfig:
    config_file = root / ".uilint.toml"
    cfg = UiConfig()

    if not config_file.is_file():
        return cfg

    try:
        content = config_file.read_text(encoding="utf-8")
        if tomllib is not None:
            raw = tomllib.loads(content)
        else:
            raw = _parse_toml_simple(content)
    except Exception:
        return cfg

    proj = raw.get("project", {})
    if "frameworks" in proj and isinstance(proj["frameworks"], list):
        cfg.frameworks = [str(x) for x in proj["frameworks"]]
    if "id_pattern" in proj:
        cfg.id_pattern = str(proj["id_pattern"])

    registries = raw.get("registries", {})
    cfg.tooltips_registry = str(registries.get("tooltips", ""))
    cfg.strings_registry = str(registries.get("strings", ""))
    cfg.theme_registry = str(registries.get("theme", ""))

    tests = raw.get("tests", {})
    if "ui_globs" in tests and isinstance(tests["ui_globs"], list):
        cfg.ui_globs = [str(x) for x in tests["ui_globs"]]
    if "evidence" in tests:
        cfg.evidence_path = str(tests["evidence"])

    combos = raw.get("combos", {})
    if "exhaustive_state_max" in combos:
        cfg.exhaustive_state_max = int(combos["exhaustive_state_max"])
    if "ordered_triples_max_actions" in combos:
        cfg.ordered_triples_max_actions = int(combos["ordered_triples_max_actions"])
    if "max_cases_per_context" in combos:
        cfg.max_cases_per_context = int(combos["max_cases_per_context"])
    if "seed" in combos:
        cfg.seed = int(combos["seed"])

    layout = raw.get("layout", {})
    if "overlap_tolerance_px" in layout:
        cfg.overlap_tolerance_px = float(layout["overlap_tolerance_px"])
    if "matrix" in layout:
        cfg.matrix = str(layout["matrix"])

    waivers = raw.get("waivers", {})
    if isinstance(waivers, dict):
        cfg.waivers = {str(k): str(v) for k, v in waivers.items()}

    return cfg
