"""Evidence loader, staleness verification, and schema validation."""

import hashlib
import json
from pathlib import Path
from typing import Any
from scripts.ui_models import (
    A11yFindingRecord,
    CaseRecord,
    ExceptionRecord,
    InteractionRecord,
    LatencySampleRecord,
    LayoutFindingRecord,
    LeakProbeRecord,
    UiEvidence,
    UiManifest,
)


def compute_file_hash(path: Path) -> str:
    if not path.is_file():
        return ""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""


def load_ui_evidence(path: Path, manifest: UiManifest | None = None) -> UiEvidence | None:
    if not path.is_file():
        return None

    try:
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    evidence = UiEvidence(
        run_id=str(data.get("run_id", "")),
        framework=str(data.get("framework", "")),
        commit=str(data.get("commit", "")),
        evidence_file_hash=compute_file_hash(path),
    )

    manifest_hashes: dict[str, str] = {}
    if manifest:
        manifest_hashes = {c.id: c.source_hash for c in manifest.controls}

    for item in data.get("interactions", []):
        ctrl_id = str(item.get("control_id", ""))
        rec_hash = str(item.get("source_hash", ""))
        # Check staleness: if source hash is recorded and differs from manifest, ignore
        if manifest_hashes and ctrl_id in manifest_hashes:
            expected_hash = manifest_hashes[ctrl_id]
            if rec_hash and rec_hash != expected_hash:
                continue

        evidence.interactions.append(
            InteractionRecord(
                control_id=ctrl_id,
                input_kind=str(item.get("input_kind", "mouse")),
                trusted=bool(item.get("trusted", False)),
                control_state=str(item.get("control_state", "enabled")),
                test_node_id=str(item.get("test_node_id", "")),
                sequence_number=int(item.get("sequence_number", 0)),
                screen_state_id=str(item.get("screen_state_id", "default")),
                source_hash=rec_hash,
            )
        )

    for item in data.get("cases", []):
        evidence.cases.append(
            CaseRecord(
                context_id=str(item.get("context_id", "")),
                case_kind=str(item.get("case_kind", "ordered_pair")),
                sequence=[str(x) for x in item.get("sequence", [])],
                passed=bool(item.get("passed", True)),
                sampled=bool(item.get("sampled", False)),
            )
        )

    for item in data.get("layout_findings", []):
        evidence.layout_findings.append(
            LayoutFindingRecord(
                type=str(item.get("type", "overlap")),
                screen_id=str(item.get("screen_id", "")),
                matrix_cell=str(item.get("matrix_cell", "default")),
                element_ids=[str(x) for x in item.get("element_ids", [])],
                rectangles=[dict(r) for r in item.get("rectangles", [])],
                screenshot_path=item.get("screenshot_path"),
            )
        )

    for item in data.get("a11y_findings", []):
        evidence.a11y_findings.append(
            A11yFindingRecord(
                type=str(item.get("type", "contrast")),
                element_id=str(item.get("element_id", "")),
                message=str(item.get("message", "")),
            )
        )

    for item in data.get("exceptions", []):
        evidence.exceptions.append(
            ExceptionRecord(
                screen_id=str(item.get("screen_id", "")),
                traceback=str(item.get("traceback", "")),
            )
        )

    for item in data.get("latency_samples", []):
        evidence.latency_samples.append(
            LatencySampleRecord(
                control_id=str(item.get("control_id", "")),
                latency_ms=float(item.get("latency_ms", 0.0)),
            )
        )

    for item in data.get("leak_probes", []):
        evidence.leak_probes.append(
            LeakProbeRecord(
                screen_id=str(item.get("screen_id", "")),
                baseline_count=int(item.get("baseline_count", 0)),
                final_count=int(item.get("final_count", 0)),
            )
        )

    return evidence
