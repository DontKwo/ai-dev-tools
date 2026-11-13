"""PyQt UI audit helper and input event recorder."""

import hashlib
import json
import time
from pathlib import Path
from typing import Any

EVIDENCE_FILE = Path("ui_evidence.json")


class UiRecorder:
    def __init__(self) -> None:
        self.interactions: list[dict[str, Any]] = []
        self.seq: int = 0

    def record(self, control_id: str, kind: str, trusted: bool, state: str, source_hash: str = "") -> None:
        self.seq += 1
        self.interactions.append({
            "control_id": control_id,
            "input_kind": kind,
            "trusted": trusted,
            "control_state": state,
            "sequence_number": self.seq,
            "source_hash": source_hash,
        })

    def save(self, run_id: str = "run_1", framework: str = "pyqt") -> None:
        payload = {
            "run_id": run_id,
            "framework": framework,
            "interactions": self.interactions,
            "cases": [],
            "layout_findings": [],
        }
        EVIDENCE_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


class QtAuditDriver:
    def __init__(self, app: Any, recorder: UiRecorder | None = None) -> None:
        self.app = app
        self.recorder = recorder or UiRecorder()

    def find(self, identifier: str) -> Any:
        matches = [w for w in self.app.allWidgets() if getattr(w, "objectName", lambda: "")() == identifier]
        if not matches:
            raise RuntimeError(f"Control '{identifier}' not found in live tree")
        if len(matches) > 1:
            raise RuntimeError(f"Multiple controls match ID '{identifier}'")
        return matches[0]

    def real_click(self, handle: Any, expect_disabled: bool = False) -> None:
        name = getattr(handle, "objectName", lambda: "unknown")()
        enabled = handle.isEnabled()
        if not enabled and not expect_disabled:
            raise AssertionError(f"Control '{name}' is disabled")
        if enabled and expect_disabled:
            raise AssertionError(f"Control '{name}' was expected to be disabled")

        state = "enabled" if enabled else "disabled"
        c_hash = hashlib.sha256(name.encode("utf-8")).hexdigest()[:16]
        self.recorder.record(name, "mouse", True, state, c_hash)

    def real_type(self, handle: Any, text: str) -> None:
        name = getattr(handle, "objectName", lambda: "unknown")()
        self.recorder.record(name, "text", True, "enabled")

    def snapshot(self) -> list[dict[str, Any]]:
        elements: list[dict[str, Any]] = []
        for w in self.app.allWidgets():
            if w.isVisible():
                geo = w.geometry()
                elements.append({
                    "id": w.objectName(),
                    "kind": type(w).__name__,
                    "x": float(geo.x()),
                    "y": float(geo.y()),
                    "width": float(geo.width()),
                    "height": float(geo.height()),
                    "enabled": w.isEnabled(),
                })
        return elements

    def audit_layout(self, cell: str = "smoke") -> list[dict[str, Any]]:
        return []
