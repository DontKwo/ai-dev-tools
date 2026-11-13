"""Textual TUI adapter for terminal user interfaces."""

import ast
import re
from pathlib import Path
from scripts.ui_models import (
    BypassPattern,
    ControlRecord,
    ScreenRecord,
    Site,
    UiFileFacts,
)
from scripts.ui_adapters.base import compute_source_hash

TEXTUAL_CONTROLS = {"Button", "Input", "Select", "Checkbox", "RadioButton", "Switch"}


class TextualAdapter:
    name: str = "textual"
    extensions: tuple[str, ...] = (".py", ".tcss")

    def detect(self, root: Path) -> bool:
        for py_path in root.rglob("*.py"):
            try:
                head = py_path.read_text(encoding="utf-8", errors="ignore")[:1000]
                if "textual" in head or "from textual" in head:
                    return True
            except OSError:
                continue
        return False

    def extract(self, path: Path, source: str) -> UiFileFacts:
        facts = UiFileFacts()
        if path.suffix != ".py" or ("textual" not in source and "from textual" not in source):
            return facts

        try:
            tree = ast.parse(source)
        except SyntaxError:
            return facts

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                name = getattr(func, "id", None) or getattr(func, "attr", None)
                if name in TEXTUAL_CONTROLS:
                    ctrl_id = ""
                    for kw in node.keywords:
                        if kw.arg == "id" and isinstance(kw.value, ast.Constant):
                            ctrl_id = str(kw.value.value)
                    ctrl_id = ctrl_id or f"{path.stem}.{name}_{node.lineno}"
                    facts.controls.append(
                        ControlRecord(
                            id=ctrl_id,
                            kind="button" if name == "Button" else "other_interactive",
                            framework="textual",
                            screen=path.stem,
                            file=str(path),
                            line=node.lineno,
                            source_hash=compute_source_hash(f"{name}:{ctrl_id}"),
                            can_disable=True,
                        )
                    )
            if isinstance(node, ast.ClassDef) and ("Screen" in node.name or "App" in node.name):
                facts.screens.append(ScreenRecord(id=node.name, kind="screen", file=str(path), line=node.lineno))
        return facts

    def test_bypass_patterns(self) -> list[BypassPattern]:
        return [
            BypassPattern(pattern=r"\.press\(", description="button.press() bypasses Pilot event queue"),
            BypassPattern(pattern=r"post_message\(Button\.Pressed", description="Direct Pressed message bypasses terminal click"),
        ]

    def tooltip_literal_sites(self, path: Path, source: str) -> list[Site]:
        sites: list[Site] = []
        for idx, line in enumerate(source.splitlines(), 1):
            if re.search(r"tooltip\s*=\s*[\"'][^\"']+[\"']", line):
                sites.append(Site(file=path, line=idx, code=23, message="Inline literal tooltip string in Textual widget"))
        return sites

    def layout_hazards(self, path: Path, source: str) -> list[Site]:
        sites: list[Site] = []
        if path.suffix != ".tcss":
            return sites
        for idx, line in enumerate(source.splitlines(), 1):
            if "width: " in line and "w" in line and "min-width" not in line:
                sites.append(Site(file=path, line=idx, code=54, message="Layout hazard: fixed cell width without min-width constraint"))
        return sites
