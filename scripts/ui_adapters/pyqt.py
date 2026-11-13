"""PyQt and PySide UI adapter supporting Python, Qt Designer, and QML."""

import ast
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from scripts.ui_models import (
    BypassPattern,
    ControlRecord,
    ScreenRecord,
    Site,
    TooltipRecord,
    UiFileFacts,
)
from scripts.ui_adapters.base import compute_source_hash

PYQT_IMPORTS = ("PyQt5", "PyQt6", "PySide2", "PySide6")
QT_CONTROLS = {
    "QPushButton": "button",
    "QToolButton": "icon_button",
    "QCheckBox": "checkbox",
    "QRadioButton": "radio",
    "QComboBox": "combo",
    "QSlider": "slider",
    "QSpinBox": "spinbox",
    "QDoubleSpinBox": "spinbox",
    "NoScrollSpinBox": "spinbox",
    "NoScrollDoubleSpinBox": "spinbox",
    "QLineEdit": "text_input",
    "QTextEdit": "text_input",
    "QPlainTextEdit": "text_input",
    "QAction": "menu_item",
    "ClickableImagePreview": "icon_button",
}
SCREEN_CLASSES = {"QMainWindow", "QDialog", "QWizard", "QWizardPage", "QWidget"}
FIXED_GEOMETRY_RE = re.compile(r"\b(setFixedSize|setFixedWidth|setGeometry|move)\s*\(")
HEX_COLOR_RE = re.compile(r"#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b")
PX_STYLE_RE = re.compile(r"\b\d+px\b")


class PyQtAdapter:
    name: str = "pyqt"
    extensions: tuple[str, ...] = (".py", ".ui", ".qml")

    def detect(self, root: Path) -> bool:
        for py_path in root.rglob("*.py"):
            try:
                head = py_path.read_text(encoding="utf-8", errors="ignore")[:2000]
                if any(pkg in head for pkg in PYQT_IMPORTS):
                    return True
            except OSError:
                continue
        return any(root.rglob("*.ui"))

    def extract(self, path: Path, source: str) -> UiFileFacts:
        if path.suffix == ".ui":
            return self._extract_ui_file(path, source)
        if path.suffix == ".qml":
            return self._extract_qml_file(path, source)
        return self._extract_python(path, source)

    def _extract_ui_file(self, path: Path, source: str) -> UiFileFacts:
        facts = UiFileFacts()
        try:
            root = ET.fromstring(source)
        except ET.ParseError:
            return facts

        for widget in root.iter("widget"):
            cls_name = widget.get("class", "")
            name = widget.get("name", "")
            kind = QT_CONTROLS.get(cls_name, "other_interactive")
            if cls_name in QT_CONTROLS:
                tool_tip = ""
                for prop in widget.findall("property"):
                    if prop.get("name") == "toolTip":
                        string_elem = prop.find("string")
                        if string_elem is not None and string_elem.text:
                            tool_tip = string_elem.text
                c_hash = compute_source_hash(f"{cls_name}:{name}")
                facts.controls.append(
                    ControlRecord(
                        id=name,
                        kind=kind,
                        framework="pyqt",
                        screen=path.stem,
                        file=str(path),
                        line=1,
                        source_hash=c_hash,
                        tooltip_ref=tool_tip or None,
                    )
                )
        return facts

    def _extract_qml_file(self, path: Path, source: str) -> UiFileFacts:
        facts = UiFileFacts()
        lines = source.splitlines()
        for idx, line in enumerate(lines, 1):
            id_match = re.search(r"\bid:\s*([a-zA-Z0-9_]+)", line)
            if id_match:
                control_id = id_match.group(1)
                facts.controls.append(
                    ControlRecord(
                        id=control_id,
                        kind="button",
                        framework="pyqt",
                        screen=path.stem,
                        file=str(path),
                        line=idx,
                        source_hash=compute_source_hash(line),
                    )
                )
        return facts

    def _extract_python(self, path: Path, source: str) -> UiFileFacts:
        facts = UiFileFacts()
        if not any(pkg in source for pkg in PYQT_IMPORTS):
            return facts
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return facts

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                is_screen = any(self._is_name_match(b, SCREEN_CLASSES) for b in node.bases)
                if is_screen:
                    facts.screens.append(
                        ScreenRecord(
                            id=node.name,
                            kind="dialog" if "Dialog" in node.name else "window",
                            file=str(path),
                            line=node.lineno,
                        )
                    )

            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                func = node.value.func
                class_name = getattr(func, "id", None) or getattr(func, "attr", None)
                if class_name in QT_CONTROLS:
                    for target in node.targets:
                        var_name = getattr(target, "id", None) or getattr(target, "attr", None)
                        if var_name:
                            c_hash = compute_source_hash(f"{class_name}:{var_name}")
                            can_disable = class_name in ("QPushButton", "QAction", "QComboBox")
                            facts.controls.append(
                                ControlRecord(
                                    id=var_name,
                                    kind=QT_CONTROLS[class_name],
                                    framework="pyqt",
                                    screen=path.stem,
                                    file=str(path),
                                    line=node.lineno,
                                    source_hash=c_hash,
                                    can_disable=can_disable,
                                )
                            )
        return facts

    def _is_name_match(self, node: ast.AST, targets: set[str]) -> bool:
        if isinstance(node, ast.Name):
            return node.id in targets
        if isinstance(node, ast.Attribute):
            return node.attr in targets
        return False

    def test_bypass_patterns(self) -> list[BypassPattern]:
        return [
            BypassPattern(pattern=r"\.click\(\)", description="Direct click call bypasses Qt event queue"),
            BypassPattern(pattern=r"\.clicked\.emit\(", description="Signal emit bypasses hit-testing"),
            BypassPattern(pattern=r"\.toggle\(\)", description="Direct toggle bypasses input pipeline"),
            BypassPattern(pattern=r"\.setChecked\(", description="Direct setChecked bypasses interaction"),
            BypassPattern(pattern=r"\.trigger\(\)", description="Action trigger bypasses UI click event"),
            BypassPattern(pattern=r"\.animateClick\(", description="animateClick bypasses physical input queue"),
        ]

    def tooltip_literal_sites(self, path: Path, source: str) -> list[Site]:
        sites: list[Site] = []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return sites

        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "setToolTip" and node.args:
                    arg = node.args[0]
                    if isinstance(arg, (ast.Constant, ast.JoinedStr)):
                        sites.append(Site(file=path, line=node.lineno, code=23, message="Inline literal tooltip"))
        return sites

    def layout_hazards(self, path: Path, source: str) -> list[Site]:
        sites: list[Site] = []
        if path.suffix == ".py" and not any(pkg in source for pkg in PYQT_IMPORTS):
            return sites
        for idx, line in enumerate(source.splitlines(), 1):
            if FIXED_GEOMETRY_RE.search(line):
                sites.append(Site(file=path, line=idx, code=54, message="Fixed geometry call causes layout hazard"))
        return sites

    def wheel_hazards(self, path: Path, source: str) -> list[Site]:
        sites: list[Site] = []
        if path.name == "spinbox.py":
            return sites
        for idx, line in enumerate(source.splitlines(), 1):
            if re.search(r"\b(QSpinBox|QDoubleSpinBox)\b", line) and "NoScroll" not in line:
                sites.append(Site(file=path, line=idx, code=31, message="Raw QSpinBox usage without wheel protection"))
        return sites

    def selectable_text_hazards(self, path: Path, source: str) -> list[Site]:
        sites: list[Site] = []
        lines = source.splitlines()
        for idx, line in enumerate(lines, 1):
            if "setWordWrap(True)" in line and not any("setTextInteractionFlags" in ln for ln in lines):
                sites.append(Site(file=path, line=idx, code=33, message="Word-wrapped label missing selectable flags"))
        return sites

    def color_literal_sites(self, path: Path, source: str) -> list[Site]:
        sites: list[Site] = []
        if "theme" in path.name.lower():
            return sites
        for idx, line in enumerate(source.splitlines(), 1):
            if HEX_COLOR_RE.search(line):
                sites.append(Site(file=path, line=idx, code=28, message="Hardcoded hex color outside theme module"))
        return sites

    def design_token_sites(self, path: Path, source: str) -> list[Site]:
        sites: list[Site] = []
        if "theme" in path.name.lower():
            return sites
        for idx, line in enumerate(source.splitlines(), 1):
            if PX_STYLE_RE.search(line):
                sites.append(Site(file=path, line=idx, code=58, message="Hardcoded pixel literal outside theme"))
        return sites
