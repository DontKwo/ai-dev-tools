---
name: to-spec
disable-model-invocation: true
description: Synthesize settled conversation decisions into a crisp specification with agreed public test seams.
---

# Turn conversation into a spec

Convert decisions settled during conversation or `grill-user` rounds into one structured engineering specification. Avoid re-interviewing the user on choices that are already locked.

## Spec structure

1. **Problem and goal**: Two to three crisp sentences defining the problem and desired outcome.
2. **Scope boundaries**: Explicit **In scope** and **Out of scope** lists.
3. **Domain terms**: Any project nouns/verbs locked during design (synced with `GLOSSARY.md` if present).
4. **Architecture and seams**: Affected modules, public interfaces, data shapes, and dependency categories (see [codebase-design](../codebase-design/SKILL.md)).
5. **Pre-agreed test seams**: Exact entrypoints (`CLI command`, `function`, `HTTP endpoint`, or `UI flow`) where `tdd` behavioral tests attach, plus key failure modes to cover.
6. **Rollout and risks**: Compatibility assumptions, migration steps if one-way, and verification commands.

## Rules

- Cite concrete repo file paths only where inspected directly.
- Mark unresolved low-impact choices as explicit **Assumptions** instead of blocking on trivial questions.
- Save to the scratch path or issue tracker specified by the user; do not create unsolicited tracked Markdown files in the repository root.
- Recommend `/to-tickets` or `/implement` as the next step once the spec is confirmed.
