"""Web UI adapter for HTML, JSX, TSX, Vue, and Svelte frontend files."""

import json
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

INTERACTIVE_TAG_RE = re.compile(
    r"<(button|input|select|textarea|a\b|div\b[^>]*\brole=[\"']button[\"']|div\b[^>]*\bonClick)([^>]*)>",
    re.IGNORECASE,
)
TEST_ID_RE = re.compile(r"(?:data-testid|testID|id)=[\"']([^\"']+)[\"']")
TOOLTIP_LITERAL_RE = re.compile(r"(?:title|data-tooltip)=[\"']([^\"']+)[\"']|<Tooltip\b[^>]*title=[\"']([^\"']+)[\"']")
LAYOUT_HAZARD_RE = re.compile(r"position:\s*absolute|white-space:\s*nowrap;\s*overflow:\s*hidden")
COLOR_LITERAL_RE = re.compile(r"#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b|rgb\([^)]+\)|hsl\([^)]+\)")
PX_TOKEN_RE = re.compile(r"\b\d+px\b")
POSITIVE_TABINDEX_RE = re.compile(r"tabindex=[\"']([1-9][0-9]*)[\"']", re.IGNORECASE)


class WebAdapter:
    name: str = "web"
    extensions: tuple[str, ...] = (
        ".html", ".htm", ".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte"
    )

    def detect(self, root: Path) -> bool:
        pkg_json = root / "package.json"
        if pkg_json.is_file():
            try:
                data = json.loads(pkg_json.read_text(encoding="utf-8"))
                deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                if any(k in deps for k in ("react", "vue", "svelte", "electron", "@tauri-apps/api")):
                    return True
            except (json.JSONDecodeError, OSError):
                return True
        return any(root.rglob("*.html"))

    def extract(self, path: Path, source: str) -> UiFileFacts:
        facts = UiFileFacts()
        lines = source.splitlines()

        for idx, line in enumerate(lines, 1):
            for match in INTERACTIVE_TAG_RE.finditer(line):
                tag_kind = match.group(1).split()[0].lower()
                attrs = match.group(2)
                id_match = TEST_ID_RE.search(attrs)
                ctrl_id = id_match.group(1) if id_match else f"{path.stem}.elem_{idx}"
                c_hash = compute_source_hash(match.group(0))

                kind = "button" if "button" in tag_kind else ("link" if tag_kind == "a" else "other_interactive")
                has_tooltip = bool(TOOLTIP_LITERAL_RE.search(attrs))
                can_disable = "button" in tag_kind or "input" in tag_kind

                facts.controls.append(
                    ControlRecord(
                        id=ctrl_id,
                        kind=kind,
                        framework="web",
                        screen=path.stem,
                        file=str(path),
                        line=idx,
                        source_hash=c_hash,
                        tooltip_ref=ctrl_id if has_tooltip else None,
                        can_disable=can_disable,
                    )
                )

        if any(keyword in path.name.lower() for keyword in ("page", "view", "screen", "dialog", "modal")):
            facts.screens.append(
                ScreenRecord(
                    id=path.stem,
                    kind="page" if "page" in path.name.lower() else "dialog",
                    file=str(path),
                    line=1,
                )
            )

        return facts

    def test_bypass_patterns(self) -> list[BypassPattern]:
        return [
            BypassPattern(pattern=r"\.click\({\s*force:\s*true\s*}\)", description="force: true bypasses hit testing"),
            BypassPattern(pattern=r"\.dispatchEvent\(", description="dispatchEvent bypasses browser input engine"),
            BypassPattern(pattern=r"fireEvent\.", description="fireEvent used instead of real browser input"),
            BypassPattern(pattern=r"evaluate\(\s*.*\.click\(", description="Script-evaluated click bypasses UI"),
        ]

    def tooltip_literal_sites(self, path: Path, source: str) -> list[Site]:
        sites: list[Site] = []
        if "registry" in path.name.lower() or "tooltip" in path.name.lower():
            return sites
        for idx, line in enumerate(source.splitlines(), 1):
            if TOOLTIP_LITERAL_RE.search(line):
                sites.append(Site(file=path, line=idx, code=23, message="Inline web tooltip outside registry"))
        return sites

    def layout_hazards(self, path: Path, source: str) -> list[Site]:
        sites: list[Site] = []
        for idx, line in enumerate(source.splitlines(), 1):
            if LAYOUT_HAZARD_RE.search(line):
                sites.append(Site(file=path, line=idx, code=54, message="Layout hazard: absolute positioning or overflow clip"))
        return sites

    def wheel_hazards(self, path: Path, source: str) -> list[Site]:
        sites: list[Site] = []
        for idx, line in enumerate(source.splitlines(), 1):
            if re.search(r"<input\b[^>]*type=[\"']number[\"']", line, re.IGNORECASE):
                if "onWheel" not in line and "wheel" not in line:
                    sites.append(Site(file=path, line=idx, code=31, message="Number input vulnerable to wheel scroll"))
        return sites

    def selectable_text_hazards(self, path: Path, source: str) -> list[Site]:
        sites: list[Site] = []
        for idx, line in enumerate(source.splitlines(), 1):
            if re.search(r"user-select:\s*none", line, re.IGNORECASE):
                sites.append(Site(file=path, line=idx, code=33, message="user-select: none prevents error/status selection"))
        return sites

    def color_literal_sites(self, path: Path, source: str) -> list[Site]:
        sites: list[Site] = []
        if "theme" in path.name.lower() or "palette" in path.name.lower() or "color" in path.name.lower():
            return sites
        for idx, line in enumerate(source.splitlines(), 1):
            if COLOR_LITERAL_RE.search(line):
                sites.append(Site(file=path, line=idx, code=28, message="Hardcoded color literal outside theme"))
        return sites

    def design_token_sites(self, path: Path, source: str) -> list[Site]:
        sites: list[Site] = []
        if "theme" in path.name.lower() or "token" in path.name.lower():
            return sites
        for idx, line in enumerate(source.splitlines(), 1):
            if PX_TOKEN_RE.search(line):
                sites.append(Site(file=path, line=idx, code=58, message="Hardcoded pixel token outside theme"))
        return sites

    def keyboard_operability_sites(self, path: Path, source: str) -> list[Site]:
        sites: list[Site] = []
        for idx, line in enumerate(source.splitlines(), 1):
            if POSITIVE_TABINDEX_RE.search(line):
                sites.append(Site(file=path, line=idx, code=64, message="Positive tabindex disrupts logical focus order"))
        return sites
