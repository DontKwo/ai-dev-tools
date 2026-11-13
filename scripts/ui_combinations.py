"""Combination sequence and state-vector coverage calculator for Rule 51."""

import itertools
import random
from typing import Any
from scripts.ui_models import CaseRecord, ControlRecord, ScreenRecord, UiEvidence


def generate_required_cases(
    screen: ScreenRecord,
    controls: list[ControlRecord],
    exhaustive_state_max: int = 8,
    ordered_triples_max_actions: int = 6,
    max_cases_per_context: int = 5000,
    seed: int = 1234,
) -> list[dict[str, Any]]:
    action_controls = [c.id for c in controls if c.kind in ("button", "icon_button", "menu_item", "link")]
    state_controls = [c.id for c in controls if c.kind in ("checkbox", "radio", "toggle", "combo", "slider")]

    required_cases: list[dict[str, Any]] = []

    # 1. State control vectors
    if state_controls:
        if len(state_controls) <= exhaustive_state_max:
            for vec in itertools.product([0, 1], repeat=len(state_controls)):
                required_cases.append({
                    "context_id": screen.id,
                    "case_kind": "state_vector",
                    "sequence": [f"{ctrl}={state_val}" for ctrl, state_val in zip(state_controls, vec)],
                })
        else:
            # Pairwise covering array
            for idx1 in range(len(state_controls)):
                for idx2 in range(idx1 + 1, len(state_controls)):
                    for val_a, val_b in ((0, 0), (0, 1), (1, 0), (1, 1)):
                        required_cases.append({
                            "context_id": screen.id,
                            "case_kind": "state_vector",
                            "sequence": [f"{state_controls[idx1]}={val_a}", f"{state_controls[idx2]}={val_b}"],
                        })

    # 2. Action control ordered pairs (with repetition)
    if action_controls:
        for a, b in itertools.product(action_controls, repeat=2):
            required_cases.append({
                "context_id": screen.id,
                "case_kind": "ordered_pair",
                "sequence": [a, b],
            })

        # Ordered triples if action count is at or below threshold
        if len(action_controls) <= ordered_triples_max_actions:
            for a, b, c in itertools.product(action_controls, repeat=3):
                required_cases.append({
                    "context_id": screen.id,
                    "case_kind": "ordered_triple",
                    "sequence": [a, b, c],
                })

    # 3. Mixed combinations
    if state_controls and action_controls:
        for action in action_controls:
            required_cases.append({
                "context_id": screen.id,
                "case_kind": "mixed",
                "sequence": [action],
            })

    # 4. Cap and sample if above maximum
    if len(required_cases) > max_cases_per_context:
        rng = random.Random(seed)
        sampled = rng.sample(required_cases, max_cases_per_context)
        for item in sampled:
            item["sampled"] = True
        return sampled

    return required_cases


def verify_screen_combinations(
    screen: ScreenRecord,
    controls: list[ControlRecord],
    evidence: UiEvidence,
    exhaustive_state_max: int = 8,
    ordered_triples_max_actions: int = 6,
    max_cases_per_context: int = 5000,
    seed: int = 1234,
) -> tuple[list[str], int, int]:
    expected = generate_required_cases(
        screen,
        controls,
        exhaustive_state_max,
        ordered_triples_max_actions,
        max_cases_per_context,
        seed,
    )
    if not expected:
        return [], 0, 0

    executed = {
        (c.case_kind, tuple(c.sequence))
        for c in evidence.cases
        if c.context_id == screen.id and c.passed
    }

    missing: list[str] = []
    for req in expected:
        key = (req["case_kind"], tuple(req["sequence"]))
        if key not in executed:
            missing.append(f"{req['case_kind']}: {' -> '.join(req['sequence'])}")

    return missing, len(executed), len(expected)
