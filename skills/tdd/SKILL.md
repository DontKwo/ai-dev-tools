---
name: tdd
description: >-
  Execute vertical red-green-refactor TDD cycles against observable public seams
  with disciplined mocking. Use when writing features, fixing bugs, writing
  regression tests, or refactoring code behind an interface seam.
---

# Test-driven development

Build features and bug fixes in thin vertical slices using red-green-refactor cycles anchored on public behavior.

Load [tests.md](tests.md) when designing test cases and assertions. Load [mocking.md](mocking.md) before introducing any stub, fake, or mock.

## Core principles

- **Vertical slices first**: Deliver one end-to-end behavior per cycle (schema -> logic -> caller/output). Skip horizontal batching (all tests up front, then all code).
- **Test public seams**: Exercise exported functions, CLI commands, API handlers, or UI interactions instead of private helper internals.
- **No implementation coupling**: Tests describe observable inputs, outputs, and state transitions so internal refactors keep existing tests green.
- **Cover failure modes**: Include boundary inputs, empty states, invalid arguments, and error paths via table-driven or generated cases alongside the happy path (see `exhaustive-testing`).

## Cycle

1. **Agree on the seam**: Identify the public entrypoint and expected observable outcome for this slice.
2. **Red**: Write one minimal failing test for that slice and run `aitools test` (or the targeted test runner) to verify it fails for the right reason.
3. **Green**: Write the smallest clean production implementation that makes the test pass.
4. **Refactor**: Consolidate duplicate logic, clarify types and names, and re-run tests to confirm green.
5. **Lint and repeat**: Run `aitools lint --diff --level strict` cleanly, then start the next vertical slice.
