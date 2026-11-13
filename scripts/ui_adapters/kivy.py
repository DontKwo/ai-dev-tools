"""Kivy UI adapter parsing .kv layout files and Python modules."""

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

KV_ID_RE = re.compile(r"^\s*id:\s*([a-zA-Z0-9_]+)")
KV_WIDGET_RE = re.compile(r"^\s*<([a-zA-Z0-9_]+)>|^\s*([A-Z][a-zA-Z0-9_]*):")


class KivyAdapter:
    name: str = "kivy"
    extensions: tuple[str, ...] = (".kv", ".py")

    def detect(self, root: Path) -> bool:
        if any(root.rglob("*.kv")):
            return True
        for py_path in root.rglob("*.py"):
            try:
                head = py_path.read_text(encoding="utf-8", errors="ignore")[:1000]
                if "kivy" in head or "from kivy" in head:
                    return True
            except OSError:
                continue
        return False

    def extract(self, path: Path, source: str) -> UiFileFacts:
        facts = UiFileFacts()
        if path.suffix != ".kv":
            return facts

        lines = source.splitlines()
        for idx, line in enumerate(lines, 1):
            id_m = KV_ID_RE.search(line)
            if id_m:
                ctrl_id = id_m.group(1)
                facts.controls.append(
                    ControlRecord(
                        id=ctrl_id,
                        kind="button",
                        framework="kivy",
                        screen=path.stem,
                        file=str(path),
                        line=idx,
                        source_hash=compute_source_hash(line),
                        can_disable=True,
                    )
                )

        facts.screens.append(ScreenRecord(id=path.stem, kind="screen", file=str(path), line=1))
        return facts

    def test_bypass_patterns(self) -> list[BypassPattern]:
        return [
            BypassPattern(pattern=r"dispatch\(\s*['\"]on_press['\"]\)", description="dispatch bypasses touch event loop"),
            BypassPattern(pattern=r"trigger_action\(", description="trigger_action bypasses touch collide_point"),
        ]

    def tooltip_literal_sites(self, path: Path, source: str) -> list[Site]:
        return []

    def layout_hazards(self, path: Path, source: str) -> list[Site]:
        sites: list[Site] = []
        for idx, line in enumerate(source.splitlines(), 1):
            if "pos_hint:" not in line and re.search(r"size:\s*\d+,\s*\d+", line):
                sites.append(Site(file=path, line=idx, code=54, message="Layout hazard: fixed pixel size without pos_hint"))
        return sites
