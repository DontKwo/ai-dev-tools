"""wxPython UI audit driver for test automation."""

from typing import Any


class WxAuditDriver:
    def __init__(self, sim: Any) -> None:
        self.sim = sim
        self.interactions: list[dict[str, Any]] = []
        self.seq: int = 0

    def real_click(self, x: int, y: int, control_id: str) -> None:
        self.sim.MouseMove(x, y)
        self.sim.MouseClick()
        self.seq += 1
        self.interactions.append({
            "control_id": control_id,
            "input_kind": "mouse",
            "trusted": True,
            "control_state": "enabled",
            "sequence_number": self.seq,
        })
