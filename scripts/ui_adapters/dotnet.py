"""DotNet UI adapter for WPF, WinForms, Avalonia, and MAUI applications."""

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from scripts.ui_models import (
    BypassPattern,
    ControlRecord,
    ScreenRecord,
    Site,
    UiFileFacts,
)
from scripts.ui_adapters.base import compute_source_hash

DOTNET_CONTROLS = {"Button", "CheckBox", "RadioButton", "ComboBox", "Slider", "TextBox"}
LAYOUT_HAZARD_RE = re.compile(r"Canvas\.Left|Canvas\.Top|Width=\"\d+\"[^>]*TextTrimming")


class DotNetAdapter:
    name: str = "dotnet"
    extensions: tuple[str, ...] = (".xaml", ".axaml", ".cs")

    def detect(self, root: Path) -> bool:
        for proj in root.rglob("*.csproj"):
            try:
                txt = proj.read_text(encoding="utf-8", errors="ignore")
                if any(k in txt for k in ("UseWPF", "UseWindowsForms", "Avalonia", "UseMaui")):
                    return True
            except OSError:
                continue
        return False

    def extract(self, path: Path, source: str) -> UiFileFacts:
        facts = UiFileFacts()
        if path.suffix in (".xaml", ".axaml"):
            return self._extract_xaml(path, source)
        return facts

    def _extract_xaml(self, path: Path, source: str) -> UiFileFacts:
        facts = UiFileFacts()
        cleaned_xml = re.sub(r"\b[a-zA-Z0-9_]+:([a-zA-Z0-9_]+)=", r"\1=", source)
        try:
            root = ET.fromstring(cleaned_xml)
            for elem in root.iter():
                tag = elem.tag.split("}")[-1]
                if tag in DOTNET_CONTROLS:
                    name = elem.attrib.get("Name") or elem.attrib.get("AutomationId") or ""
                    ctrl_id = name or f"{path.stem}.{tag}_{len(facts.controls)+1}"
                    facts.controls.append(
                        ControlRecord(
                            id=ctrl_id,
                            kind="button" if "Button" in tag else "other_interactive",
                            framework="dotnet",
                            screen=path.stem,
                            file=str(path),
                            line=1,
                            source_hash=compute_source_hash(f"{tag}:{ctrl_id}"),
                            can_disable=True,
                        )
                    )
        except ET.ParseError:
            for match in re.finditer(r"<([A-Z][a-zA-Z0-9_]*)\b([^>]*)>", source):
                tag = match.group(1)
                if tag in DOTNET_CONTROLS:
                    attrs = match.group(2)
                    name_m = re.search(r'(?:x:Name|Name|AutomationProperties\.AutomationId)=["\']([^"\']+)["\']', attrs)
                    ctrl_id = name_m.group(1) if name_m else f"{path.stem}.{tag}_{len(facts.controls)+1}"
                    facts.controls.append(
                        ControlRecord(
                            id=ctrl_id,
                            kind="button" if "Button" in tag else "other_interactive",
                            framework="dotnet",
                            screen=path.stem,
                            file=str(path),
                            line=1,
                            source_hash=compute_source_hash(f"{tag}:{ctrl_id}"),
                            can_disable=True,
                        )
                    )

        facts.screens.append(ScreenRecord(id=path.stem, kind="window", file=str(path), line=1))
        return facts

    def test_bypass_patterns(self) -> list[BypassPattern]:
        return [
            BypassPattern(pattern=r"UIA\.Invoke\(", description="UIA Invoke() bypasses mouse click event"),
            BypassPattern(pattern=r"RaiseEvent\(.*ClickEvent", description="Direct RaiseEvent bypasses window routing"),
            BypassPattern(pattern=r"\.PerformClick\(", description="PerformClick bypasses physical input queue"),
        ]

    def tooltip_literal_sites(self, path: Path, source: str) -> list[Site]:
        sites: list[Site] = []
        for idx, line in enumerate(source.splitlines(), 1):
            if re.search(r"ToolTip=[\"'][^\"{][^\"']*[\"']", line):
                sites.append(Site(file=path, line=idx, code=23, message="Inline literal ToolTip in XAML"))
        return sites

    def layout_hazards(self, path: Path, source: str) -> list[Site]:
        sites: list[Site] = []
        for idx, line in enumerate(source.splitlines(), 1):
            if LAYOUT_HAZARD_RE.search(line):
                sites.append(Site(file=path, line=idx, code=54, message="Layout hazard: Canvas absolute coordinates or fixed width trimming"))
        return sites
