# Agent brief authoring guide

Write `ready-for-agent` issue briefs purely in behavioral terms so they stay accurate across months of internal file moves and refactors.

## Structural rules

- **Omit volatile file paths and line numbers**: Describe the public command, endpoint, UI surface, and observable behavior so internal code cleanup never rots the ticket.
- **Name one verification seam**: Specify what test suite or command demonstrates fixed behavior.
- **Include an explicit Done checklist**: State exact pass/fail observables.

## Template

```md
## Behavior expected
Describe what users or callers should experience once fixed or added.

## Observed behavior
State exact error message, wrong output, or reproduction input.

## Scope bounds
List explicit non-goals so the agent stops cleanly without adjacent refactoring.

## Acceptance criteria
- Observable scenario A succeeds with expected result
- Failure mode B returns explicit error message X
- Relevant tests pass and `aitools lint . --level strict` stays clean
```
