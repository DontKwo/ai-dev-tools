---
name: exhaustive-testing
description: >-
  Systematically discover interactive handlers, seed hostile test data, execute stateful model-based random sequences, and verify system invariants. Use when validating complex logic or user-facing applications.
---

# Exhaustive Testing

Validate software across edge cases, hostile data, and stateful sequences.

## Trigger

Execute before declaring any non-trivial feature or refactor complete.

## Testing Phases

### Action registry (Phase A)
1. Statically scan handlers, routers, and interactive controls across the codebase.
2. Dynamically crawl application views to verify reachable controls.
3. Assign stable test IDs (`data-testid`) to every interactive element.
4. Verify that no handler or interactive control remains unregistered.

### Seeded corpus (Phase B)
Build a reusable corpus containing standard and hostile test inputs:
- Empty, boundary, and massive payloads.
- Unicode edge cases: right-to-left, zero-width spaces, combining accents, emojis.
- Injection strings: SQL, shell, HTML, cross-site script tags.
- Filesystem anomalies: truncated files, invalid encodings, full disks.
- Numerical extremes: negative values, floating-point subnormals, infinity, NaN.
- Locale variations: alternative date, currency, and decimal separators.
- Collection scales: zero, single, thousands of items, and duplicate elements.

### Multi-layer execution (Phase C)
1. Core Logic: Table-driven unit tests and property-based test suites.
2. UI Matrix: Action-by-data-class test matrix with state seeded directly.
3. Stateful Model Sequences: Execute pseudo-random chains of 5 to 200 actions with logged seeds.
4. Shrinking & Replay: Shrink failing sequences to minimal repro steps and save regression seeds.
5. Environmental Variants: Viewports (360px to 1920px), light/dark themes, reduced motion, CPU throttle, offline status, mid-edit reloads.

### Invariant verification (Phase D)
Assert invariants after every single test action:
- Zero unhandled exceptions or console errors.
- No `NaN`, `undefined`, or `[object Object]` strings rendered in the DOM.
- No visual text clipping, scroll overlap, or layout blowouts.
- UI counts and metrics match underlying persistent storage.
- Application state survives page reload and navigation restarts.
- Action transitions complete within their allotted time budget.
- Injected markup renders as inert text.
- Zero high-severity accessibility violations.

### Verification tiers (Phase E)
- Tier 1 (PR Smoke): Fast sanity checks and core unit tests on every branch.
- Tier 2 (Nightly Soak): Full UI matrix and long stateful random walks across sharded workers.
- Coverage Report: Output concrete counts of executed test paths and state transitions.
- Bug Fixes: Every discovered defect receives a root-cause fix and a regression test.

## Stack Conventions

- Python: Standard `unittest` with `subTest()` iterations and seeded `random.Random(seed)` fixtures. Use `Hypothesis` only when already a declared dependency.
- Web: Playwright test runner combined with `fast-check` generators.
- Scaffolding: When `scripts/scaffold_test_matrix.py` exists, execute it to generate harness templates.
- Mutation Testing: Run mutation tools (such as `mutmut` or `stryker`) where available to verify test sensitivity.
