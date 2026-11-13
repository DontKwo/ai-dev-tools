"""Tauri UI adapter checking Rust command bridges and frontend invokes."""

import json
import re
from pathlib import Path
from scripts.ui_models import BypassPattern, Site, UiFileFacts
from scripts.ui_adapters.web import WebAdapter

TAURI_CMD_RE = re.compile(r"#\[tauri::command\]\s*(?:async\s+)?fn\s+([a-zA-Z0-9_]+)")
INVOKE_RE = re.compile(r"\binvoke\(\s*[\"']([^\"']+)[\"']")


class TauriAdapter:
    name: str = "tauri"
    extensions: tuple[str, ...] = (".rs", ".js", ".ts", ".html", ".tsx", ".jsx")
    _web = WebAdapter()

    def detect(self, root: Path) -> bool:
        pkg_json = root / "package.json"
        if pkg_json.is_file():
            try:
                data = json.loads(pkg_json.read_text(encoding="utf-8"))
                deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                if "@tauri-apps/api" in deps:
                    return True
            except (json.JSONDecodeError, OSError):
                pass
        return (root / "src-tauri" / "Cargo.toml").is_file()

    def extract(self, path: Path, source: str) -> UiFileFacts:
        facts = self._web.extract(path, source)
        for c in facts.controls:
            c.framework = "tauri"
        return facts

    def test_bypass_patterns(self) -> list[BypassPattern]:
        base = self._web.test_bypass_patterns()
        return base + [
            BypassPattern(pattern=r"invoke\(.*plugin:", description="Direct plugin invoke without UI event")
        ]

    def tooltip_literal_sites(self, path: Path, source: str) -> list[Site]:
        return self._web.tooltip_literal_sites(path, source)

    def layout_hazards(self, path: Path, source: str) -> list[Site]:
        return self._web.layout_hazards(path, source)

    def bridge_mismatch_sites(self, root: Path) -> list[Site]:
        sites: list[Site] = []
        commands: set[str] = set()

        for rs_file in root.rglob("*.rs"):
            try:
                src = rs_file.read_text(encoding="utf-8", errors="ignore")
                for m in TAURI_CMD_RE.finditer(src):
                    commands.add(m.group(1))
            except OSError:
                continue

        for js_file in root.rglob("*.js"):
            try:
                src = js_file.read_text(encoding="utf-8", errors="ignore")
                for idx, line in enumerate(src.splitlines(), 1):
                    for m in INVOKE_RE.finditer(line):
                        cmd = m.group(1)
                        if commands and cmd not in commands:
                            sites.append(Site(file=js_file, line=idx, code=78, message=f"Tauri invoke mismatch: {cmd}"))
            except OSError:
                continue
        return sites
