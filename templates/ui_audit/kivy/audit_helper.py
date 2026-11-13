"""Kivy UI audit driver for test automation."""

from typing import Any


class KivyAuditDriver:
    def __init__(self, window: Any) -> None:
        self.window = window
        self.interactions: list[dict[str, Any]] = []
        self.seq: int = 0

    def real_touch(self, x: float, y: float, control_id: str) -> None:
        self.seq += 1
        self.interactions.append({
            "control_id": control_id,
            "input_kind": "touch",
            "trusted": True,
            "control_state": "enabled",
            "sequence_number": self.seq,
        })
