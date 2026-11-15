---
name: code-review
description: >-
  Run a dual-axis parallel review on a branch diff checking coding standards,
  linter compliance, code smells, and specification fidelity. Use when
  reviewing pull requests, inspecting a feature branch before merge, or running
  code review on git changes.
---

# Code review

Audit branch changes (`git diff <base>...HEAD`) using two fresh-context review lenses so standards noise and specification bugs receive independent scrutiny.

## Preparation

Determine the base branch (`main` or `master` unless specified) and collect the branch diff plus active spec or ticket acceptance criteria.

## Two parallel fresh-context reviewers

Dispatch two subagents simultaneously with distinct briefs:

### Lens 1: Standards and smell reviewer

Run static checks and scan the diff against Martin Fowler's 12 classic code smells:

```bash
aitools lint . --diff --level strict
aitools secrets --diff
```

Check for `Duplicate Code`, `Long Function`, `Long Parameter List`, `Global Data`, `Mutable Data`, `Divergent Change`, `Shotgun Surgery`, `Feature Envy`, `Data Clumps`, `Primitive Obsession`, `Repeated Switches`, and `Speculative Generalization / Unused Loops`. Verify type annotations, error chaining, and failure-mode test coverage.

### Lens 2: Spec and logic reviewer

Read the branch diff alongside the original request, spec, or ticket:

- Check every requirement and edge case for omissions or subtle off-by-one/boundary errors.
- Flag unrequested scope creep outside the approved plan.
- Verify public interfaces and `GLOSSARY.md` terms match what callers expect.

## Synthesis format

Merge both subagent reports into three concise severity buckets with `file:line` pointers:

- **Blockers**: Correctness bugs, missing tests on critical paths, security issues, or linter failures that stop merge.
- **Warnings**: Structural smells, shallow wrappers, or weak edge-case handling worth fixing now or logging as follow-up tickets.
- **Nits**: Optional naming or formatting polish.
