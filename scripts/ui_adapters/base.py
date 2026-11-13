"""Base protocol and common types for UI toolkit adapters."""

import hashlib
from pathlib import Path
from typing import Protocol
from scripts.ui_models import BypassPattern, Site, UiFileFacts


def compute_source_hash(source_fragment: str) -> str:
    cleaned = "".join(source_fragment.split())
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()[:16]


class UiAdapter(Protocol):
    name: str
    extensions: tuple[str, ...]

    def detect(self, root: Path) -> bool: ...

    def extract(self, path: Path, source: str) -> UiFileFacts: ...

    def test_bypass_patterns(self) -> list[BypassPattern]: ...

    def tooltip_literal_sites(self, path: Path, source: str) -> list[Site]: ...

    def layout_hazards(self, path: Path, source: str) -> list[Site]: ...
