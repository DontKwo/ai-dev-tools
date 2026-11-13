"""Pywebview adapter combining Python host and web frontend checks."""

import re
from pathlib import Path
from scripts.ui_models import BypassPattern, Site, UiFileFacts
from scripts.ui_adapters.web import WebAdapter

PYWEBVIEW_API_CALL_RE = re.compile(r"window\.pywebview\.api\.([a-zA-Z0-9_]+)\(")
PY_EXPOSE_RE = re.compile(r"(?:window\.expose|js_api\s*=)\s*([a-zA-Z0-9_]+)")


class PywebviewAdapter:
    name: str = "pywebview"
    extensions: tuple[str, ...] = (".py", ".html", ".js", ".ts")
    _web = WebAdapter()

    def detect(self, root: Path) -> bool:
        for py_path in root.rglob("*.py"):
            try:
                head = py_path.read_text(encoding="utf-8", errors="ignore")[:1000]
                if "import webview" in head or "from webview" in head:
                    return True
            except OSError:
                continue
        return False

    def extract(self, path: Path, source: str) -> UiFileFacts:
        if path.suffix == ".py":
            return UiFileFacts()
        facts = self._web.extract(path, source)
        for c in facts.controls:
            c.framework = "pywebview"
        return facts

    def test_bypass_patterns(self) -> list[BypassPattern]:
        base_patterns = self._web.test_bypass_patterns()
        return base_patterns + [
            BypassPattern(pattern=r"evaluate_js\(.*\.click\(", description="evaluate_js click bypasses native window")
        ]

    def tooltip_literal_sites(self, path: Path, source: str) -> list[Site]:
        if path.suffix == ".py":
            return []
        return self._web.tooltip_literal_sites(path, source)

    def layout_hazards(self, path: Path, source: str) -> list[Site]:
        if path.suffix == ".py":
            return []
        return self._web.layout_hazards(path, source)

    def bridge_mismatch_sites(self, root: Path) -> list[Site]:
        sites: list[Site] = []
        exposed_methods: set[str] = set()
        for py_file in root.rglob("*.py"):
            try:
                txt = py_file.read_text(encoding="utf-8", errors="ignore")
                for m in PY_EXPOSE_RE.finditer(txt):
                    exposed_methods.add(m.group(1))
            except OSError:
                continue

        for js_file in root.rglob("*.js"):
            try:
                txt = js_file.read_text(encoding="utf-8", errors="ignore")
                for idx, line in enumerate(txt.splitlines(), 1):
                    for match in PYWEBVIEW_API_CALL_RE.finditer(line):
                        method = match.group(1)
                        if exposed_methods and method not in exposed_methods:
                            sites.append(Site(file=js_file, line=idx, code=78, message=f"Bridge mismatch: {method} not exposed"))
            except OSError:
                continue
        return sites
