---
name: grill-user
description: >-
  Stress-test a plan, design proposal, architecture change, or user idea through
  frontier-round questioning until shared understanding is reached. Use when the
  user requests grilling, before large or under-specified tasks, or when design
  decisions conflict or stay ambiguous.
---

# Grill user

Resolve design ambiguity by walking the decision tree from root branches to leaves.

## Fact-check before asking

Never ask the user something you can verify from the codebase, git history, or `memory/` files:

- Inspect relevant files or dispatch a fresh-context `research` subagent for non-trivial factual questions.
- Skip trivial or easily reversible choices and act directly with stated defaults.
- Ask only when the decision depends on human intent, domain tradeoffs, or one-way consequences.

## Frontier-round protocol

Walk dependencies in breadth-first frontier rounds instead of guessing ahead or interrogating randomly:

1. Identify open design branches from the user prompt and repository inspection.
2. Ask one to four independent questions on the current frontier (highest architectural leverage first). Wait for replies before opening downstream branches.
3. Frame each question in plain domain terms and pair it with a recommended default and concise options:

```text
[Q] Q1 -- Where should validation errors surface before saving?
[A] Recommended: Inline field validation plus a top summary banner, so users fix mistakes without losing form state.
    Options: (a) Inline + banner (recommended), (b) Modal dialog, (c) Submit-time toast.
```

4. If the user replies "yes" (or "just do it"), accept the stated recommendation for every open question in the round.
5. Stop when remaining unknowns are low-impact details. Output a compact Shared Understanding block (`Goal`, `Decisions`, `Assumptions`, `Out of scope`, `Acceptance criteria`).

## Synchronize domain docs

When working inside a codebase, keep project domain documentation current as decisions lock in (see [domain-modeling](../domain-modeling/SKILL.md)):

- Record settled canonical domain terms and `_Avoid:_` synonyms in `GLOSSARY.md` when the project maintains one.
- Propose an Architecture Decision Record in `docs/adr/NNNN-<slug>.md` when a decision is hard to reverse, surprising without context, or settled among real tradeoffs.

## Async mode for cloud agents

Headless and background runs cannot hold multi-turn dialogue. Use `aitools grill`:

```bash
aitools grill "<topic_or_plan>"
aitools grill "<topic_or_plan>" --async
```

1. Write open questions and recommended defaults into the plan.
2. Halt and ask only blocking questions; proceed on non-blocking choices using the recommended defaults.
3. Record all assumed defaults in the pull request description.
