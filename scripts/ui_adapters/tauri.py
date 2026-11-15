"""Tauri UI adapter checking Rust command bridges and frontend invokes."""

import json
import re
from pathlib import Path
from scripts.ui_models import BypassPattern, Site, UiFileFacts
from scripts.ui_adapters.web import WebAdapter

TAURI_CMD_RE = re.compile(r"#\[tauri::command\]\s*(?:async\s+)?fn\s+([a-zA-Z0-9_]+)")
INVOKE_RE = re.compile(r"\binvoke\(\s*[\"']([^\"']+)[\"']")
INCLUDE_DIST_RE = re.compile(r"include_str!\(\s*[\"']([^\"']*dist/[^\"']+)[\"']\s*\)")


class TauriAdapter:
    name: str = "tauri"
    extensions: tuple[str, ...] = (".rs", ".js", ".ts", ".html", ".tsx", ".jsx", ".css", ".scss")
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
                pass  # noqa: 10
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

    def stale_bundle_sites(self, root: Path) -> list[Site]:
        sites: list[Site] = []
        src_dir = root / "src" / "src"
        tauri_src = root / "src-tauri" / "src"
        if not src_dir.is_dir() or not tauri_src.is_dir():
            return sites
        src_mtimes = [
            f.stat().st_mtime
            for f in src_dir.rglob("*")
            if f.is_file() and f.suffix in (".ts", ".tsx", ".js", ".jsx", ".css")
        ]
        if not src_mtimes:
            return sites
        newest_src = max(src_mtimes)
        for rs_file in tauri_src.rglob("*.rs"):
            try:
                text = rs_file.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for idx, line in enumerate(text.splitlines(), 1):
                match = INCLUDE_DIST_RE.search(line)
                if match:
                    target = (rs_file.parent / match.group(1)).resolve()
                    if target.is_file() and newest_src > target.stat().st_mtime + 2.0:
                        sites.append(Site(file=rs_file, line=idx, code=87, message="Embedded dist asset is older than src/src"))
        return sites

    def desktop_lifecycle_sites(self, root: Path) -> list[Site]:
        main_rs = root / "src-tauri" / "src" / "main.rs"
        if not main_rs.is_file():
            return []
        try:
            main_src = main_rs.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return []
        if "TcpListener::bind" not in main_src or "--app=" not in main_src:
            return []
        combined = ""
        for rs_file in (root / "src-tauri" / "src").rglob("*.rs"):
            try:
                combined += rs_file.read_text(encoding="utf-8", errors="ignore") + "\n"
            except OSError:
                continue
        has_selftest = "--self-test" in combined
        has_shutdown = ("/api/shutdown" in combined) or ("/api/heartbeat" in combined)
        has_console_close = ("GetConsoleWindow" in combined) or ("windows_subsystem" in combined)
        if not (has_selftest and has_shutdown and has_console_close):
            return [Site(file=main_rs, line=1, code=88, message="Desktop server entrypoint missing lifecycle handlers")]
        return []
