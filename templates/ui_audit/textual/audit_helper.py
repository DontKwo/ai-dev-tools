"""Textual UI audit driver for test automation."""

from typing import Any


class TextualAuditDriver:
    def __init__(self, pilot: Any) -> None:
        self.pilot = pilot
        self.interactions: list[dict[str, Any]] = []
        self.seq: int = 0

    async def real_click(self, selector: str, control_id: str) -> None:
        await self.pilot.click(selector)
        self.seq += 1
        self.interactions.append({
            "control_id": control_id,
            "input_kind": "mouse",
            "trusted": True,
            "control_state": "enabled",
            "sequence_number": self.seq,
        })
