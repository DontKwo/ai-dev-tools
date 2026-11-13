"""iOS UI adapter for SwiftUI and UIKit applications."""

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

IOS_CONTROL_RE = re.compile(r"\b(Button|UIButton|UISwitch|UISlider|UITextField)\b")
ACCESSIBILITY_ID_RE = re.compile(r"accessibilityIdentifier\s*(?:=|\()\s*[\"']([^\"']+)[\"']")


class IosAdapter:
    name: str = "ios"
    extensions: tuple[str, ...] = (".swift", ".m", ".h")

    def detect(self, root: Path) -> bool:
        if (root / "Package.swift").is_file():
            return True
        return any(root.rglob("*.xcodeproj")) or any(root.rglob("*.xcworkspace"))

    def extract(self, path: Path, source: str) -> UiFileFacts:
        facts = UiFileFacts()
        lines = source.splitlines()
        controls_by_var: dict[str, ControlRecord] = {}

        for idx, line in enumerate(lines, 1):
            if IOS_CONTROL_RE.search(line):
                var_match = re.search(r"\b(?:let|var)\s+([a-zA-Z0-9_]+)\s*=", line)
                var_name = var_match.group(1) if var_match else ""
                id_match = ACCESSIBILITY_ID_RE.search(line)
                ctrl_id = id_match.group(1) if id_match else f"{path.stem}.ios_{idx}"
                c_hash = compute_source_hash(line)
                ctrl = ControlRecord(
                    id=ctrl_id,
                    kind="button",
                    framework="ios",
                    screen=path.stem,
                    file=str(path),
                    line=idx,
                    source_hash=c_hash,
                    can_disable=True,
                )
                facts.controls.append(ctrl)
                if var_name:
                    controls_by_var[var_name] = ctrl

            id_assign_match = re.search(r"([a-zA-Z0-9_]+)\.accessibilityIdentifier\s*=\s*[\"']([^\"']+)[\"']", line)
            if id_assign_match:
                vname, actual_id = id_assign_match.group(1), id_assign_match.group(2)
                if vname in controls_by_var:
                    controls_by_var[vname].id = actual_id

        if "viewcontroller" in path.name.lower() or "view" in path.name.lower():
            facts.screens.append(ScreenRecord(id=path.stem, kind="view_controller", file=str(path), line=1))

        return facts

    def test_bypass_patterns(self) -> list[BypassPattern]:
        return [
            BypassPattern(pattern=r"sendActions\(for:", description="sendActions bypasses window touch routing"),
            BypassPattern(pattern=r"ViewInspector.*\.tap\(", description="ViewInspector tap bypasses accessibility hit testing"),
        ]

    def tooltip_literal_sites(self, path: Path, source: str) -> list[Site]:
        sites: list[Site] = []
        for idx, line in enumerate(source.splitlines(), 1):
            if re.search(r"\.help\(\s*[\"'][^\"']+[\"']\s*\)", line):
                sites.append(Site(file=path, line=idx, code=23, message="Inline literal .help() string outside registry"))
        return sites

    def layout_hazards(self, path: Path, source: str) -> list[Site]:
        sites: list[Site] = []
        for idx, line in enumerate(source.splitlines(), 1):
            if "widthAnchor.constraint(equalToConstant:" in line and "minimumScaleFactor" not in line:
                sites.append(Site(file=path, line=idx, code=54, message="Layout hazard: pinned width constraint without scale factor"))
        return sites
