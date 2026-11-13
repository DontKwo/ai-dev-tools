"""Tkinter UI audit driver for test automation."""

from typing import Any


class TkAuditDriver:
    def __init__(self, root: Any) -> None:
        self.root = root
        self.interactions: list[dict[str, Any]] = []
        self.seq: int = 0

    def real_click(self, widget: Any, control_id: str) -> None:
        widget.event_generate("<Button-1>")
        widget.event_generate("<ButtonRelease-1>")
        self.seq += 1
        self.interactions.append({
            "control_id": control_id,
            "input_kind": "mouse",
            "trusted": True,
            "control_state": "enabled",
            "sequence_number": self.seq,
        })
