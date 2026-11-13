"""Data structures for UI manifest and runtime evidence records."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ControlRecord:
    id: str
    kind: str
    framework: str
    screen: str
    file: str
    line: int
    source_hash: str
    label_ref: str | None = None
    tooltip_ref: str | None = None
    icon_only: bool = False
    checkable: bool = False
    can_disable: bool = False
    handlers: list[str] = field(default_factory=list)
    overlay_ok: bool = False
    scrollable_ok: bool = False
    discovered: str = "static"


@dataclass
class ScreenRecord:
    id: str
    kind: str
    file: str
    line: int
    controls: list[str] = field(default_factory=list)
    has_layout_audit: bool = False


@dataclass
class TooltipRecord:
    id: str
    text: str
    accessible_name: str | None = None
    accessible_hint: str | None = None
    shortcut: str | None = None
    disabled_reason: str | None = None
    file: str = ""
    line: int = 0


@dataclass
class Site:
    file: Path
    line: int
    code: int
    message: str


@dataclass
class BypassPattern:
    pattern: str
    description: str


@dataclass
class UiFileFacts:
    controls: list[ControlRecord] = field(default_factory=list)
    screens: list[ScreenRecord] = field(default_factory=list)
    tooltips: list[TooltipRecord] = field(default_factory=list)
    sites: list[Site] = field(default_factory=list)


@dataclass
class InteractionRecord:
    control_id: str
    input_kind: str
    trusted: bool
    control_state: str
    test_node_id: str
    sequence_number: int
    screen_state_id: str = "default"
    source_hash: str = ""


@dataclass
class CaseRecord:
    context_id: str
    case_kind: str
    sequence: list[str] = field(default_factory=list)
    passed: bool = True
    sampled: bool = False


@dataclass
class LayoutFindingRecord:
    type: str
    screen_id: str
    matrix_cell: str
    element_ids: list[str]
    rectangles: list[dict[str, float]]
    screenshot_path: str | None = None


@dataclass
class A11yFindingRecord:
    type: str
    element_id: str
    message: str


@dataclass
class ExceptionRecord:
    screen_id: str
    traceback: str


@dataclass
class LatencySampleRecord:
    control_id: str
    latency_ms: float


@dataclass
class LeakProbeRecord:
    screen_id: str
    baseline_count: int
    final_count: int


@dataclass
class UiManifest:
    controls: list[ControlRecord] = field(default_factory=list)
    screens: list[ScreenRecord] = field(default_factory=list)
    tooltips: list[TooltipRecord] = field(default_factory=list)
    strings: list[dict[str, Any]] = field(default_factory=list)
    theme_tokens: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "controls": [vars(c) for c in self.controls],
            "screens": [vars(s) for s in self.screens],
            "tooltips": [vars(t) for t in self.tooltips],
            "strings": self.strings,
            "theme_tokens": self.theme_tokens,
        }


@dataclass
class UiEvidence:
    run_id: str
    framework: str
    commit: str
    evidence_file_hash: str = ""
    interactions: list[InteractionRecord] = field(default_factory=list)
    cases: list[CaseRecord] = field(default_factory=list)
    layout_findings: list[LayoutFindingRecord] = field(default_factory=list)
    a11y_findings: list[A11yFindingRecord] = field(default_factory=list)
    exceptions: list[ExceptionRecord] = field(default_factory=list)
    latency_samples: list[LatencySampleRecord] = field(default_factory=list)
    leak_probes: list[LeakProbeRecord] = field(default_factory=list)
