"""Tkinter UI adapter for standard Python desktop interfaces."""

import ast
from pathlib import Path
from scripts.ui_models import (
    BypassPattern,
    ControlRecord,
    ScreenRecord,
    Site,
    UiFileFacts,
)
from scripts.ui_adapters.base import compute_source_hash

TK_CONTROLS = {"Button", "Checkbutton", "Radiobutton", "Entry", "Combobox"}


class TkinterAdapter:
    name: str = "tkinter"
    extensions: tuple[str, ...] = (".py",)

    def detect(self, root: Path) -> bool:
        for py_path in root.rglob("*.py"):
            try:
                head = py_path.read_text(encoding="utf-8", errors="ignore")[:1000]
                if "tkinter" in head or "from tkinter" in head:
                    return True
            except OSError:
                continue
        return False

    def extract(self, path: Path, source: str) -> UiFileFacts:
        facts = UiFileFacts()
        if "tkinter" not in source and "Button" not in source:
            return facts
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return facts

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                func = node.value.func
                cls_name = getattr(func, "id", None) or getattr(func, "attr", None)
                if cls_name in TK_CONTROLS:
                    for target in node.targets:
                        var_name = getattr(target, "id", None) or getattr(target, "attr", None)
                        if var_name:
                            facts.controls.append(
                                ControlRecord(
                                    id=var_name,
                                    kind="button" if "Button" in str(cls_name) else "other_interactive",
                                    framework="tkinter",
                                    screen=path.stem,
                                    file=str(path),
                                    line=node.lineno,
                                    source_hash=compute_source_hash(f"{cls_name}:{var_name}"),
                                    can_disable=True,
                                )
                            )
            if isinstance(node, ast.ClassDef) and ("Frame" in node.name or "App" in node.name):
                facts.screens.append(ScreenRecord(id=node.name, kind="window", file=str(path), line=node.lineno))
        return facts

    def test_bypass_patterns(self) -> list[BypassPattern]:
        return [
            BypassPattern(pattern=r"\.invoke\(", description="invoke() bypasses Tkinter event generation"),
            BypassPattern(pattern=r"\.command\(", description="Direct command invocation bypasses mouse click"),
        ]

    def tooltip_literal_sites(self, path: Path, source: str) -> list[Site]:
        return []

    def layout_hazards(self, path: Path, source: str) -> list[Site]:
        sites: list[Site] = []
        if "tkinter" not in source:
            return sites
        for idx, line in enumerate(source.splitlines(), 1):
            if ".place(" in line:
                sites.append(Site(file=path, line=idx, code=54, message="Layout hazard: absolute .place() coordinate geometry"))
        return sites
