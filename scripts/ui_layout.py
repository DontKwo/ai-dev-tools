"""Layout audit algorithms checking geometric overlap, clipping, and bounds."""

from dataclasses import dataclass
from typing import Any
from scripts.ui_models import LayoutFindingRecord


@dataclass
class Rect:
    x: float
    y: float
    width: float
    height: float

    @property
    def area(self) -> float:
        return max(0.0, self.width) * max(0.0, self.height)

    def intersection(self, other: "Rect") -> "Rect | None":
        x1 = max(self.x, other.x)
        y1 = max(self.y, other.y)
        x2 = min(self.x + self.width, other.x + other.width)
        y2 = min(self.y + self.height, other.y + other.height)
        if x2 > x1 and y2 > y1:
            return Rect(x1, y1, x2 - x1, y2 - y1)
        return None

    def contains(self, other: "Rect") -> bool:
        return (
            other.x >= self.x
            and other.y >= self.y
            and other.x + other.width <= self.x + self.width
            and other.y + other.height <= self.y + self.height
        )


def check_element_overlaps(
    elements: list[dict[str, Any]],
    tolerance_px: float = 1.0,
    screen_id: str = "main",
    matrix_cell: str = "default",
) -> list[LayoutFindingRecord]:
    findings: list[LayoutFindingRecord] = []
    tol_area = tolerance_px * tolerance_px

    for i in range(len(elements)):
        e1 = elements[i]
        if e1.get("overlay_ok", False):
            continue
        r1 = Rect(e1.get("x", 0.0), e1.get("y", 0.0), e1.get("width", 0.0), e1.get("height", 0.0))

        for j in range(i + 1, len(elements)):
            e2 = elements[j]
            if e2.get("overlay_ok", False):
                continue
            r2 = Rect(e2.get("x", 0.0), e2.get("y", 0.0), e2.get("width", 0.0), e2.get("height", 0.0))

            inter = r1.intersection(r2)
            if inter and inter.area > tol_area:
                min_area = min(r1.area, r2.area)
                if min_area > 0 and (inter.area / min_area) > 0.02:
                    findings.append(
                        LayoutFindingRecord(
                            type="overlap",
                            screen_id=screen_id,
                            matrix_cell=matrix_cell,
                            element_ids=[str(e1.get("id")), str(e2.get("id"))],
                            rectangles=[
                                {"x": r1.x, "y": r1.y, "w": r1.width, "h": r1.height},
                                {"x": r2.x, "y": r2.y, "w": r2.width, "h": r2.height},
                            ],
                        )
                    )
    return findings


def check_target_size(
    elements: list[dict[str, Any]],
    min_width: float = 24.0,
    min_height: float = 24.0,
) -> list[str]:
    violations: list[str] = []
    for elem in elements:
        w = float(elem.get("width", 0.0))
        h = float(elem.get("height", 0.0))
        if w < min_width or h < min_height:
            violations.append(f"{elem.get('id')}: {w}x{h} < {min_width}x{min_height}")
    return violations


def check_parent_clipping(
    elements: list[dict[str, Any]],
    tolerance_px: float = 1.0,
    screen_id: str = "main",
    matrix_cell: str = "default",
) -> list[LayoutFindingRecord]:
    findings: list[LayoutFindingRecord] = []
    for elem in elements:
        parent = elem.get("parent_rect")
        if not isinstance(parent, dict):
            continue
        child_r = Rect(elem.get("x", 0.0), elem.get("y", 0.0), elem.get("width", 0.0), elem.get("height", 0.0))
        parent_r = Rect(parent.get("x", 0.0), parent.get("y", 0.0), parent.get("width", 0.0), parent.get("height", 0.0))
        clipped = (
            child_r.x < parent_r.x - tolerance_px
            or child_r.y < parent_r.y - tolerance_px
            or child_r.x + child_r.width > parent_r.x + parent_r.width + tolerance_px
            or child_r.y + child_r.height > parent_r.y + parent_r.height + tolerance_px
        )
        if clipped:
            findings.append(
                LayoutFindingRecord(
                    type="clipping",
                    screen_id=screen_id,
                    matrix_cell=matrix_cell,
                    element_ids=[str(elem.get("id"))],
                    rectangles=[
                        {"x": child_r.x, "y": child_r.y, "w": child_r.width, "h": child_r.height},
                        {"x": parent_r.x, "y": parent_r.y, "w": parent_r.width, "h": parent_r.height},
                    ],
                )
            )
    return findings


def check_viewport_overflow(
    elements: list[dict[str, Any]],
    viewport_width: float,
    viewport_height: float,
    tolerance_px: float = 1.0,
    screen_id: str = "main",
    matrix_cell: str = "default",
) -> list[LayoutFindingRecord]:
    findings: list[LayoutFindingRecord] = []
    for elem in elements:
        if not elem.get("visible", True):
            continue
        width = float(elem.get("width", 0.0))
        height = float(elem.get("height", 0.0))
        if width <= 0.0 or height <= 0.0:
            continue
        x_pos = float(elem.get("x", 0.0))
        y_pos = float(elem.get("y", 0.0))
        overflow_x = (x_pos + width) > (viewport_width + tolerance_px) or x_pos < -tolerance_px
        overflow_y = (y_pos + height) > (viewport_height + tolerance_px) or y_pos < -tolerance_px
        if overflow_x or overflow_y:
            findings.append(
                LayoutFindingRecord(
                    type="viewport_overflow",
                    screen_id=screen_id,
                    matrix_cell=matrix_cell,
                    element_ids=[str(elem.get("id"))],
                    rectangles=[
                        {"x": x_pos, "y": y_pos, "w": width, "h": height},
                        {"x": 0.0, "y": 0.0, "w": viewport_width, "h": viewport_height},
                    ],
                )
            )
    return findings
