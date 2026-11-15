---
name: diagnosing-bugs
description: >-
  Run a hypothesis-driven debugging loop with a minimal reproduction command,
  tagged instrumentation, and regression test verification. Use when debugging
  failing tests, runtime exceptions, regressions, flaky behavior, or unclear bugs.
---

# Diagnosing bugs

Isolate root causes through falsifiable hypotheses and fast reproduction loops instead of speculative edits.

## Phase 1: Establish a tight reproduction loop

Define a single fast command that proves the bug fails (red) and passes after a fix (green):

```bash
aitools test
# or target a single test / repro command:
uv run --no-project python -m unittest tests/test_target.py
```

If no automated repro exists, write a minimal scratch script or targeted test first and verify it reproduces the failure deterministically.

## Phase 2: Minimize the failing input

Shrink inputs, concurrency, and surrounding setup until only the essential trigger remains:

- Strip unrelated flags, fixtures, or configuration keys.
- Confirm the failure still matches the original error message and stack trace.

## Phase 3: Rank three to five falsifiable hypotheses

List candidate root causes ordered by likelihood and write down what observable evidence would confirm or rule out each hypothesis before touching production logic.

## Phase 4: Instrument with traceable probes

Add temporary diagnostic logging tagged with a unique session prefix (for example `[DEBUG-4f9a]`) at boundary points:

```python
# Temporary probe; remove in Phase 6
log.debug("[DEBUG-4f9a] parser state=%r offset=%d", state, offset)
```

Run the Phase 1 command, inspect captured values, and cross out disproven hypotheses until one concrete mechanism explains every symptom.

## Phase 5: Lock in a regression test and fix the root cause

1. Add a clean test at the public interface seam that reproduces the minimized case (see [tdd](../tdd/SKILL.md)).
2. Verify the new test fails before the code change.
3. Implement the minimal root-cause fix (skip symptom patches or silent fallbacks).
4. Re-run the full relevant test suite (`aitools test`).

## Phase 6: Strip instrumentation and verify cleanliness

1. Remove every `[DEBUG-...]` log line and temporary reproduction script.
2. Confirm no secrets, leaked tokens, or stray debug tags remain:

```bash
aitools lint . --level strict
aitools secrets --diff
```
