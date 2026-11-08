---
name: implicit-requirements
description: >-
  Infer and apply unstated quality, testing, error-handling, and performance requirements at the start of non-trivial tasks. Use when expanding short prompts into comprehensive task checklists.
---

# Implicit Requirements

Expand short requests into complete engineering checklists without waiting for explicit prompts.

## Trigger

Run silently at the start of every non-trivial task before formulating execution steps.

## Checklist Categories

1. **Explicit Ask**: The direct user request and core objective.
2. **Implicit Requirements**: Standards drawn from project instructions, UX rules, and memory files.
3. **Failure Modes**:
   - Bad, malformed, empty, or oversized input.
   - Process interruptions, timeouts, and abrupt cancellation.
   - Concurrency conflicts and race conditions.
   - Storage exhaustion or filesystem permission barriers.
   - Locale differences, encoding shifts, and time zone offsets.
   - Hostile input strings, script injection, and payload attacks.
   - Low-tier hardware, CPU throttling, or high-latency networks.
4. **User Annoyances**: Flaws, layout glitches, or missing conveniences that would annoy the user later.
5. **Definition of Done**: Clear criteria including automated tests, linter cleanliness, and documentation.

## Procedure

1. Parse the user prompt and identify core targets.
2. Cross-reference project rules and memory files for unstated expectations.
3. Enumerate specific failure modes applicable to the task domain.
4. Format into an "Implicit requirements applied" checklist in the execution plan.
5. Skip irrelevant items; keep exactly one concise line per applicable requirement.
6. Implement all identified requirements alongside the explicit request.

## Example Plan Block

```markdown
### Implicit requirements applied
- Validated empty, single-element, and oversized payload arrays.
- Ensured WCAG AA contrast on newly added status badges.
- Added localized error message on network timeout.
- Handled rapid repeated button clicks without duplicate submits.
- Maintained clean AST linter status across all modified files.
```
