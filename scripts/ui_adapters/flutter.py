"""Flutter UI adapter for Dart widget trees."""

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

FLUTTER_CONTROLS = {
    "ElevatedButton": "button",
    "IconButton": "icon_button",
    "TextButton": "button",
    "OutlinedButton": "button",
    "InkWell": "button",
    "Checkbox": "checkbox",
    "Radio": "radio",
    "DropdownButton": "combo",
    "Slider": "slider",
    "TextField": "text_input",
}
FLUTTER_CONTROL_RE = re.compile(r"\b(" + "|".join(FLUTTER_CONTROLS.keys()) + r")\b")
KEY_RE = re.compile(r"(?:Key|ValueKey)\s*\(\s*[\"']([^\"']+)[\"']")
LAYOUT_HAZARD_RE = re.compile(r"SizedBox\s*\(\s*width:\s*\d+.*Text\(")
COLOR_LITERAL_RE = re.compile(r"Color\s*\(\s*0x[0-9a-fA-F]+\s*\)")


class FlutterAdapter:
    name: str = "flutter"
    extensions: tuple[str, ...] = (".dart",)

    def detect(self, root: Path) -> bool:
        pubspec = root / "pubspec.yaml"
        if not pubspec.is_file():
            return False
        try:
            return "flutter:" in pubspec.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return False

    def extract(self, path: Path, source: str) -> UiFileFacts:
        facts = UiFileFacts()
        lines = source.splitlines()

        for idx, line in enumerate(lines, 1):
            m = FLUTTER_CONTROL_RE.search(line)
            if m:
                widget_name = m.group(1)
                key_match = KEY_RE.search(line)
                ctrl_id = key_match.group(1) if key_match else f"{path.stem}.{widget_name}_{idx}"
                c_hash = compute_source_hash(line)
                facts.controls.append(
                    ControlRecord(
                        id=ctrl_id,
                        kind=FLUTTER_CONTROLS[widget_name],
                        framework="flutter",
                        screen=path.stem,
                        file=str(path),
                        line=idx,
                        source_hash=c_hash,
                        can_disable=True,
                    )
                )

        if "screen" in path.name.lower() or "page" in path.name.lower() or "view" in path.name.lower():
            facts.screens.append(ScreenRecord(id=path.stem, kind="page", file=str(path), line=1))

        return facts

    def test_bypass_patterns(self) -> list[BypassPattern]:
        return [
            BypassPattern(pattern=r"onPressed!\s*\(", description="Direct invocation of onPressed bypasses widget hit testing"),
            BypassPattern(pattern=r"warnIfMissed:\s*false", description="warnIfMissed: false silences hit test failures"),
        ]

    def tooltip_literal_sites(self, path: Path, source: str) -> list[Site]:
        sites: list[Site] = []
        for idx, line in enumerate(source.splitlines(), 1):
            if re.search(r"Tooltip\s*\(\s*message:\s*[\"'][^\"']+[\"']", line):
                sites.append(Site(file=path, line=idx, code=23, message="Inline literal tooltip message in Flutter"))
        return sites

    def layout_hazards(self, path: Path, source: str) -> list[Site]:
        sites: list[Site] = []
        for idx, line in enumerate(source.splitlines(), 1):
            if LAYOUT_HAZARD_RE.search(line):
                sites.append(Site(file=path, line=idx, code=54, message="Layout hazard: fixed SizedBox enclosing Text"))
        return sites

    def color_literal_sites(self, path: Path, source: str) -> list[Site]:
        sites: list[Site] = []
        if "theme" in path.name.lower():
            return sites
        for idx, line in enumerate(source.splitlines(), 1):
            if COLOR_LITERAL_RE.search(line):
                sites.append(Site(file=path, line=idx, code=28, message="Color literal outside theme class"))
        return sites
