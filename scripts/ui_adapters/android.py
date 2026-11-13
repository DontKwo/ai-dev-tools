"""Android UI adapter for Android Views XML layouts and Jetpack Compose."""

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

ANDROID_CONTROLS = {
    "Button": "button",
    "ImageButton": "icon_button",
    "CheckBox": "checkbox",
    "RadioButton": "radio",
    "Spinner": "combo",
    "SeekBar": "slider",
    "EditText": "text_input",
}
COMPOSE_CONTROL_RE = re.compile(r"\b(Button|IconButton|TextButton|OutlinedButton)\b")
TEST_TAG_RE = re.compile(r"testTag\s*\(\s*[\"']([^\"']+)[\"']")
LAYOUT_HAZARD_RE = re.compile(r"<AbsoluteLayout\b|android:layout_width=\"\d+dp\"[^>]*android:maxLines=\"1\"")
COLOR_LITERAL_RE = re.compile(r"#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b")


class AndroidAdapter:
    name: str = "android"
    extensions: tuple[str, ...] = (".xml", ".kt", ".java")

    def detect(self, root: Path) -> bool:
        if (root / "AndroidManifest.xml").is_file():
            return True
        return any(root.rglob("AndroidManifest.xml")) or any(root.rglob("build.gradle*"))

    def extract(self, path: Path, source: str) -> UiFileFacts:
        if path.suffix == ".xml":
            return self._extract_xml(path, source)
        return self._extract_kotlin(path, source)

    def _extract_xml(self, path: Path, source: str) -> UiFileFacts:
        facts = UiFileFacts()
        try:
            root = ET.fromstring(source)
        except ET.ParseError:
            return facts

        for elem in root.iter():
            tag = elem.tag.split("}")[-1]
            if tag in ANDROID_CONTROLS:
                res_id = ""
                for k, v in elem.attrib.items():
                    if k.endswith("id"):
                        res_id = v.split("/")[-1]
                ctrl_id = res_id or f"{path.stem}.{tag}_{len(facts.controls)+1}"
                c_hash = compute_source_hash(f"{tag}:{res_id}")
                facts.controls.append(
                    ControlRecord(
                        id=ctrl_id,
                        kind=ANDROID_CONTROLS[tag],
                        framework="android",
                        screen=path.stem,
                        file=str(path),
                        line=1,
                        source_hash=c_hash,
                        can_disable=True,
                    )
                )

        facts.screens.append(ScreenRecord(id=path.stem, kind="activity", file=str(path), line=1))
        return facts

    def _extract_kotlin(self, path: Path, source: str) -> UiFileFacts:
        facts = UiFileFacts()
        lines = source.splitlines()

        for idx, line in enumerate(lines, 1):
            if COMPOSE_CONTROL_RE.search(line):
                tag_match = TEST_TAG_RE.search(line)
                ctrl_id = tag_match.group(1) if tag_match else f"{path.stem}.compose_{idx}"
                c_hash = compute_source_hash(line)
                facts.controls.append(
                    ControlRecord(
                        id=ctrl_id,
                        kind="button",
                        framework="android",
                        screen=path.stem,
                        file=str(path),
                        line=idx,
                        source_hash=c_hash,
                        can_disable=True,
                    )
                )
        return facts

    def test_bypass_patterns(self) -> list[BypassPattern]:
        return [
            BypassPattern(pattern=r"\.performClick\(", description="performClick bypasses Android touch queue"),
            BypassPattern(pattern=r"\.callOnClick\(", description="callOnClick bypasses touch preflight"),
            BypassPattern(pattern=r"performSemanticsAction\(", description="Semantics action bypasses gesture engine"),
        ]

    def tooltip_literal_sites(self, path: Path, source: str) -> list[Site]:
        sites: list[Site] = []
        for idx, line in enumerate(source.splitlines(), 1):
            if re.search(r"android:tooltipText=[\"'][^@][^\"']*[\"']", line):
                sites.append(Site(file=path, line=idx, code=23, message="Inline literal tooltip string in Android layout"))
        return sites

    def layout_hazards(self, path: Path, source: str) -> list[Site]:
        sites: list[Site] = []
        for idx, line in enumerate(source.splitlines(), 1):
            if LAYOUT_HAZARD_RE.search(line):
                sites.append(Site(file=path, line=idx, code=54, message="Layout hazard: AbsoluteLayout or fixed single-line width"))
        return sites

    def color_literal_sites(self, path: Path, source: str) -> list[Site]:
        sites: list[Site] = []
        if "color" in path.name.lower():
            return sites
        for idx, line in enumerate(source.splitlines(), 1):
            if COLOR_LITERAL_RE.search(line):
                sites.append(Site(file=path, line=idx, code=28, message="Hardcoded hex color outside colors.xml"))
        return sites
