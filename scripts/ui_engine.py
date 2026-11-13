"""UI verification engine coordinating static inspection and evidence auditing."""

import ast
import re
from fnmatch import fnmatch
from pathlib import Path
from typing import Any
from scripts.ui_adapters import detect_adapters, get_all_adapters
from scripts.ui_adapters.base import UiAdapter
from scripts.ui_combinations import verify_screen_combinations
from scripts.ui_config import UiConfig
from scripts.ui_evidence import load_ui_evidence
from scripts.ui_models import (
    ControlRecord,
    ScreenRecord,
    Site,
    TooltipRecord,
    UiEvidence,
    UiManifest,
)

TRIVIAL_ASSERT_RE = re.compile(
    r"\bassert\s+(?:True|1)\b|\bassertTrue\(\s*(?:True|true|1)\s*\)|\bexpect\(\s*true\s*\)",
    re.IGNORECASE,
)
RAW_EXCEPTION_RE = re.compile(
    r"(?:QMessageBox\.(?:critical|warning)|alert|Toast\.makeText)\([^)]*(?:str\([a-zA-Z0-9_]*e\)|err\.message|e\.toString\(\))"
)
BLOCKING_CALL_RE = re.compile(r"\b(time\.sleep|requests\.(?:get|post)|subprocess\.run|urllib\.request)\b")
DESTRUCTIVE_NAME_RE = re.compile(r"\b(delete|remove|clear|reset|overwrite|discard)\b", re.IGNORECASE)
EXCLUDED_PARTS = {"__pycache__", ".git", ".venv", "venv", ".pytest_cache", "node_modules", "dist", "build"}


def _is_valid_ui_file(fpath: Path) -> bool:
    if fpath.suffix in (".pyc", ".pyo", ".pyd", ".json", ".txt", ".md"):
        return False
    if "ui_adapters" in fpath.parts or "templates" in fpath.parts:
        return False
    return EXCLUDED_PARTS.isdisjoint(fpath.parts)


def _is_suppressed(line: str, code: int) -> bool:
    if "# noqa" in line or "// noqa" in line or "<!-- noqa" in line:
        if f"noqa: {code}" in line or "noqa" in line:
            return True
    return False


def _adapters_for_file(fpath: Path, source: str, adapters: list[UiAdapter]) -> list[UiAdapter]:
    if fpath.name.startswith("test_") or any(part in ("tests", "test") for part in fpath.parts):
        return []
    matched: list[UiAdapter] = []
    for ad in adapters:
        if fpath.suffix in ad.extensions:
            if fpath.suffix == ".py":
                if ad.name == "pyqt" and any(pkg in source for pkg in ("PyQt5", "PyQt6", "PySide2", "PySide6")):
                    matched.append(ad)
                elif ad.name == "tkinter" and ("import tkinter" in source or "from tkinter" in source):
                    matched.append(ad)
                elif ad.name == "wxpython" and ("import wx" in source or "from wx" in source):
                    matched.append(ad)
                elif ad.name == "textual" and ("import textual" in source or "from textual" in source):
                    matched.append(ad)
                elif ad.name == "kivy" and ("import kivy" in source or "from kivy" in source):
                    matched.append(ad)
            else:
                matched.append(ad)
    return matched


def build_manifest(root: Path, config: UiConfig, files: list[Path] | None = None) -> UiManifest:
    manifest = UiManifest()
    adapters = detect_adapters(root) or get_all_adapters()
    raw_files = files if files is not None else [p for p in root.rglob("*") if p.is_file()]
    target_files = [p for p in raw_files if _is_valid_ui_file(p)]

    for fpath in target_files:
        try:
            source = fpath.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        matching_adapters = _adapters_for_file(fpath, source, adapters)
        if not matching_adapters:
            continue

        for ad in matching_adapters:
            facts = ad.extract(fpath, source)
            manifest.controls.extend(facts.controls)
            manifest.screens.extend(facts.screens)
            manifest.tooltips.extend(facts.tooltips)

    return manifest


def evaluate_static_rules(
    root: Path,
    manifest: UiManifest,
    config: UiConfig,
    files: list[Path] | None = None,
) -> list[tuple[Path, int, int]]:
    violations: list[tuple[Path, int, int]] = []
    adapters = detect_adapters(root) or get_all_adapters()
    raw_files = files if files is not None else [p for p in root.rglob("*") if p.is_file()]
    target_files = [p for p in raw_files if _is_valid_ui_file(p)]

    # 1. Rule 46: Stable ID check
    screen_ids: dict[str, set[str]] = {}
    for ctrl in manifest.controls:
        if config.is_waived(ctrl.id):
            continue
        ctrl_path = Path(ctrl.file)
        if not config.matches_id_pattern(ctrl.id):
            violations.append((ctrl_path, ctrl.line, 46))
        # Duplicate ID within same screen
        seen = screen_ids.setdefault(ctrl.screen, set())
        if ctrl.id in seen:
            violations.append((ctrl_path, ctrl.line, 46))
        seen.add(ctrl.id)

    # 2. Rule 52: Tooltip registry hygiene
    if config.tooltips_registry:
        reg_path = root / config.tooltips_registry
        if reg_path.is_file():
            _audit_tooltip_registry(reg_path, manifest, violations)

    # 3. File-level AST and pattern checks
    for fpath in target_files:
        try:
            rel_str = fpath.relative_to(root).as_posix()
        except ValueError:
            rel_str = fpath.as_posix()
        is_ui_test = any(
            fnmatch(rel_str, g) or fnmatch(fpath.as_posix(), g) or fnmatch(fpath.as_posix(), f"*/{g}")
            for g in config.ui_globs
        )
        try:
            source = fpath.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        matching_adapters = _adapters_for_file(fpath, source, adapters)
        if not is_ui_test and not matching_adapters:
            continue

        lines = source.splitlines()

        # Rule 48: Test bypasses in UI tests
        if is_ui_test:
            for ad in adapters:
                for bp in ad.test_bypass_patterns():
                    rx = re.compile(bp.pattern)
                    for idx, line in enumerate(lines, 1):
                        if rx.search(line):
                            violations.append((fpath, idx, 48))

            # Rule 49: Assertions after interaction
            _audit_test_assertions(fpath, source, violations)

        # Adapter static sites (Rules 23, 54, 58)
        for ad in matching_adapters:
            for site in ad.tooltip_literal_sites(fpath, source):
                violations.append((site.file, site.line, site.code))
            for site in ad.layout_hazards(fpath, source):
                violations.append((site.file, site.line, site.code))
            if hasattr(ad, "design_token_sites"):
                for site in getattr(ad, "design_token_sites")(fpath, source):
                    violations.append((site.file, site.line, site.code))

        # Rule 61: Raw exception display
        for idx, line in enumerate(lines, 1):
            if RAW_EXCEPTION_RE.search(line):
                violations.append((fpath, idx, 61))

        # Rule 62: Blocking calls in UI slots
        _audit_blocking_slots(fpath, source, violations)

        # Rule 67: Destructive actions without confirmation
        for idx, line in enumerate(lines, 1):
            if DESTRUCTIVE_NAME_RE.search(line) and ("button" in line.lower() or "action" in line.lower()):
                if not any(k in line.lower() for k in ("confirm", "dialog", "undo", "prompt")):
                    violations.append((fpath, idx, 67))

    # Rule 78: Bridge mismatch
    for ad in adapters:
        if hasattr(ad, "bridge_mismatch_sites"):
            for site in getattr(ad, "bridge_mismatch_sites")(root):
                violations.append((site.file, site.line, site.code))

    filtered_violations: list[tuple[Path, int, int]] = []
    file_lines_cache: dict[Path, list[str]] = {}
    for fpath, lineno, code in violations:
        if fpath not in file_lines_cache:
            try:
                file_lines_cache[fpath] = fpath.read_text(encoding="utf-8", errors="ignore").splitlines()
            except OSError:
                file_lines_cache[fpath] = []
        flines = file_lines_cache[fpath]
        line_txt = flines[lineno - 1] if lineno - 1 < len(flines) else ""
        if not _is_suppressed(line_txt, code):
            filtered_violations.append((fpath, lineno, code))

    return filtered_violations


def evaluate_evidence_rules(
    root: Path,
    manifest: UiManifest,
    evidence: UiEvidence | None,
    config: UiConfig,
) -> list[tuple[Path, int, int]]:
    violations: list[tuple[Path, int, int]] = []

    if not manifest.controls and not manifest.screens:
        return violations

    if evidence is None:
        # Rule 47: project-level violation if UI present but no evidence
        default_file = Path(manifest.controls[0].file) if manifest.controls else root / "ui_evidence.json"
        violations.append((default_file, 1, 47))
        return violations

    recorded_controls = {i.control_id for i in evidence.interactions if i.trusted}
    disabled_recorded = {i.control_id for i in evidence.interactions if i.trusted and i.control_state == "disabled"}
    enabled_recorded = {i.control_id for i in evidence.interactions if i.trusted and i.control_state == "enabled"}

    # Rule 47: Control never pressed with real input
    for ctrl in manifest.controls:
        if config.is_waived(ctrl.id):
            continue
        if ctrl.id not in recorded_controls:
            violations.append((Path(ctrl.file), ctrl.line, 47))

    # Rule 50: can_disable controls must exercise both states
    for ctrl in manifest.controls:
        if ctrl.can_disable and not config.is_waived(ctrl.id):
            if ctrl.id not in disabled_recorded or ctrl.id not in enabled_recorded:
                violations.append((Path(ctrl.file), ctrl.line, 50))

    # Rule 51: Combination coverage
    for screen in manifest.screens:
        screen_controls = [c for c in manifest.controls if c.screen == screen.id]
        missing, _, _ = verify_screen_combinations(
            screen,
            screen_controls,
            evidence,
            config.exhaustive_state_max,
            config.ordered_triples_max_actions,
            config.max_cases_per_context,
            config.seed,
        )
        if missing:
            violations.append((Path(screen.file), screen.line, 51))

    # Rule 53: Layout findings
    for finding in evidence.layout_findings:
        target_ctrl = next((c for c in manifest.controls if c.id in finding.element_ids), None)
        f_path = Path(target_ctrl.file) if target_ctrl else Path(evidence.commit or "ui_evidence.json")
        f_line = target_ctrl.line if target_ctrl else 1
        violations.append((f_path, f_line, 53))

    # Rule 56: Target below minimum size
    for a11y in evidence.a11y_findings:
        if a11y.type == "target_size":
            target_ctrl = next((c for c in manifest.controls if c.id == a11y.element_id), None)
            f_path = Path(target_ctrl.file) if target_ctrl else root / "ui_evidence.json"
            f_line = target_ctrl.line if target_ctrl else 1
            violations.append((f_path, f_line, 56))

    # Rule 71: Latency budget violations (> 100ms)
    for sample in evidence.latency_samples:
        if sample.latency_ms > 100.0:
            target_ctrl = next((c for c in manifest.controls if c.id == sample.control_id), None)
            f_path = Path(target_ctrl.file) if target_ctrl else root / "ui_evidence.json"
            f_line = target_ctrl.line if target_ctrl else 1
            violations.append((f_path, f_line, 71))

    # Rule 72: Memory leak probes
    for probe in evidence.leak_probes:
        if probe.final_count > probe.baseline_count:
            screen = next((s for s in manifest.screens if s.id == probe.screen_id), None)
            f_path = Path(screen.file) if screen else root / "ui_evidence.json"
            f_line = screen.line if screen else 1
            violations.append((f_path, f_line, 72))

    return violations


def _audit_tooltip_registry(reg_path: Path, manifest: UiManifest, violations: list[tuple[Path, int, int]]) -> None:
    try:
        content = reg_path.read_text(encoding="utf-8")
    except OSError:
        return

    control_ids = {c.id for c in manifest.controls}
    for idx, line in enumerate(content.splitlines(), 1):
        m = re.search(r"[\"']([a-zA-Z0-9_.]+)[\"']\s*:\s*[\"']([^\"']+)[\"']", line)
        if m:
            entry_id, text = m.group(1), m.group(2)
            # Orphan entry
            if control_ids and entry_id not in control_ids and not entry_id.startswith("test."):
                violations.append((reg_path, idx, 52))
            # Trailing period or style violation
            if text.endswith("."):
                violations.append((reg_path, idx, 52))


def _audit_test_assertions(path: Path, source: str, violations: list[tuple[Path, int, int]]) -> None:
    if path.suffix != ".py":
        return
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            has_interaction = False
            has_non_trivial_assert = False

            for sub in ast.walk(node):
                if isinstance(sub, ast.Call):
                    func_name = getattr(sub.func, "id", None) or getattr(sub.func, "attr", None)
                    if func_name in ("real_click", "real_key", "real_type", "mouseClick", "keyClick"):
                        has_interaction = True
                elif isinstance(sub, ast.Assert):
                    if not (isinstance(sub.test, ast.Constant) and sub.test.value in (True, 1)):
                        has_non_trivial_assert = True

            if has_interaction and not has_non_trivial_assert:
                violations.append((path, node.lineno, 49))


def _audit_blocking_slots(path: Path, source: str, violations: list[tuple[Path, int, int]]) -> None:
    if path.suffix != ".py":
        return
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and any(node.name.startswith(p) for p in ("on_", "handle_", "slot_")):
            for sub in ast.walk(node):
                if isinstance(sub, ast.Call):
                    txt = ast.unparse(sub) if hasattr(ast, "unparse") else ""
                    if txt and BLOCKING_CALL_RE.search(txt):
                        violations.append((path, sub.lineno, 62))
