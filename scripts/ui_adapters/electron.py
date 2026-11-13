"""Electron UI adapter checking IPC channels and renderer interfaces."""

import json
import re
from pathlib import Path
from scripts.ui_models import BypassPattern, Site, UiFileFacts
from scripts.ui_adapters.web import WebAdapter

IPC_MAIN_RE = re.compile(r"ipcMain\.handle\(\s*[\"']([^\"']+)[\"']")
IPC_RENDERER_RE = re.compile(r"ipcRenderer\.invoke\(\s*[\"']([^\"']+)[\"']")


class ElectronAdapter:
    name: str = "electron"
    extensions: tuple[str, ...] = (".js", ".ts", ".html", ".tsx", ".jsx")
    _web = WebAdapter()

    def detect(self, root: Path) -> bool:
        pkg_json = root / "package.json"
        if not pkg_json.is_file():
            return False
        try:
            data = json.loads(pkg_json.read_text(encoding="utf-8"))
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            return "electron" in deps
        except (json.JSONDecodeError, OSError):
            return False

    def extract(self, path: Path, source: str) -> UiFileFacts:
        facts = self._web.extract(path, source)
        for c in facts.controls:
            c.framework = "electron"
        return facts

    def test_bypass_patterns(self) -> list[BypassPattern]:
        base = self._web.test_bypass_patterns()
        return base + [
            BypassPattern(pattern=r"ipcRenderer\.send\(", description="Direct IPC send without UI event injection")
        ]

    def tooltip_literal_sites(self, path: Path, source: str) -> list[Site]:
        return self._web.tooltip_literal_sites(path, source)

    def layout_hazards(self, path: Path, source: str) -> list[Site]:
        return self._web.layout_hazards(path, source)

    def bridge_mismatch_sites(self, root: Path) -> list[Site]:
        sites: list[Site] = []
        main_channels: set[str] = set()

        for f in root.rglob("*.js"):
            try:
                src = f.read_text(encoding="utf-8", errors="ignore")
                for m in IPC_MAIN_RE.finditer(src):
                    main_channels.add(m.group(1))
            except OSError:
                continue

        for f in root.rglob("*.js"):
            try:
                src = f.read_text(encoding="utf-8", errors="ignore")
                for idx, line in enumerate(src.splitlines(), 1):
                    for m in IPC_RENDERER_RE.finditer(line):
                        channel = m.group(1)
                        if main_channels and channel not in main_channels:
                            sites.append(Site(file=f, line=idx, code=78, message=f"IPC mismatch: {channel} not handled"))
            except OSError:
                continue
        return sites
