"""wxPython desktop UI adapter."""

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

WX_CONTROLS = {"Button", "CheckBox", "ToggleButton", "ComboBox", "TextCtrl"}


class WxPythonAdapter:
    name: str = "wxpython"
    extensions: tuple[str, ...] = (".py",)

    def detect(self, root: Path) -> bool:
        for py_path in root.rglob("*.py"):
            try:
                head = py_path.read_text(encoding="utf-8", errors="ignore")[:1000]
                if "import wx" in head or "from wx" in head:
                    return True
            except OSError:
                continue
        return False

    def extract(self, path: Path, source: str) -> UiFileFacts:
        facts = UiFileFacts()
        if "wx" not in source and "Button" not in source:
            return facts
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return facts

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                func = node.value.func
                attr_name = getattr(func, "attr", None) or getattr(func, "id", None)
                if attr_name in WX_CONTROLS:
                    for target in node.targets:
                        name = getattr(target, "id", None) or getattr(target, "attr", None)
                        if name:
                            facts.controls.append(
                                ControlRecord(
                                    id=name,
                                    kind="button" if "Button" in str(attr_name) else "other_interactive",
                                    framework="wxpython",
                                    screen=path.stem,
                                    file=str(path),
                                    line=node.lineno,
                                    source_hash=compute_source_hash(f"{attr_name}:{name}"),
                                    can_disable=True,
                                )
                            )
            if isinstance(node, ast.ClassDef) and any(b in ("Frame", "Dialog") for b in [getattr(x, "id", None) for x in node.bases]):
                facts.screens.append(ScreenRecord(id=node.name, kind="dialog" if "Dialog" in node.name else "window", file=str(path), line=node.lineno))
        return facts

    def test_bypass_patterns(self) -> list[BypassPattern]:
        return [
            BypassPattern(pattern=r"wx\.PostEvent\(", description="wx.PostEvent bypasses UIActionSimulator"),
            BypassPattern(pattern=r"ProcessEvent\(", description="ProcessEvent bypasses window system hit test"),
        ]

    def tooltip_literal_sites(self, path: Path, source: str) -> list[Site]:
        sites: list[Site] = []
        for idx, line in enumerate(source.splitlines(), 1):
            if "SetToolTip(" in line:
                sites.append(Site(file=path, line=idx, code=23, message="Inline literal tooltip string in wxPython"))
        return sites

    def layout_hazards(self, path: Path, source: str) -> list[Site]:
        sites: list[Site] = []
        if "wx" not in source:
            return sites
        for idx, line in enumerate(source.splitlines(), 1):
            if "SetSize(" in line and "Sizer" not in line:
                sites.append(Site(file=path, line=idx, code=54, message="Layout hazard: fixed SetSize coordinate bypasses sizer"))
        return sites
