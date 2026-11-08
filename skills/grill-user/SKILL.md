---
name: grill-user
description: >-
  Stress-test a plan, architectural decision, design proposal, or user idea through rigorous adversarial questioning. Use when the user requests grilling, before executing risky refactors, or when validating technical architecture.
---

# Grill User

Critique and stress-test plans, architecture, and intent through focused interrogation.

## Triggers

- Real doubt about intent, scope, priority, or technical trade-offs.
- Before formulating an execution plan for any large or under-specified task.
- When the user explicitly requests grilling (for example, "grill me").

## Boundaries (What Not to Grill About)

- Anything discoverable from the repository, code, or memory files.
- Anything covered by standing instructions or project standards.
- Trivial, low-impact, or easily reversible choices.

## Procedure

1. Explore the codebase and environment first to eliminate factual unknowns.
2. List open questions ordered strictly by dependency and architectural impact.
3. Ask one question at a time, highest impact first.
4. Format each question with a recommended answer, reason, and 2 or 3 options.
5. Stop when remaining unknowns are low impact (cap at about 7 questions maximum).
6. If the user states "just do it", proceed immediately with the recommended answers.
7. Output a shared-understanding block before implementation:
   - Goal
   - Decisions
   - Assumptions
   - Out of scope
   - Acceptance criteria (including standing defaults)

## Async Mode for Cloud Agents

Background and cloud agents without live interactive terminals cannot hold multi-turn dialogue. Instead:
1. Run with `--async` to generate questions and recommended defaults.
2. Include open questions and recommended defaults in the written plan.
3. Ask only blocking questions; proceed on non-blocking items with stated defaults.
4. Record every assumption in the pull request description.

## Command

Run interactive or async grilling:

```bash
uv run --no-project python scripts/grill_user.py "<topic_or_plan>"
uv run --no-project python scripts/grill_user.py "<topic_or_plan>" --async
```

