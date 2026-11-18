---
name: triage
description: Triage incoming issues or PRs against out-of-scope rules and repository state into actionable labels and behavioral Agent Briefs.
---

# Triage issues and PRs

Classify incoming backlog items, prune duplicates or out-of-scope requests, and convert autonomous-ready issues into durable Agent Briefs.

Load [AGENT-BRIEF.md](AGENT-BRIEF.md) when rewriting issues for autonomous execution (`ready-for-agent`). Load [OUT-OF-SCOPE.md](OUT-OF-SCOPE.md) when checking or recording permanent scope exclusions in `.out-of-scope/`.

## Triage state machine

Assign exactly one primary state label (see `docs/agents/triage-labels.md` if present):

| State label | Meaning | Next owner |
| :--- | :--- | :--- |
| `needs-triage` | Unreviewed incoming item | Maintainer |
| `needs-info` | Missing reproduction steps, logs, or concrete scope | Reporter |
| `ready-for-agent` | Reproducible, bounded, and backed by an Agent Brief | Coding agent |
| `ready-for-human` | High-risk security, product direction, or one-way architecture call | Maintainer |
| `wontfix` | Duplicate, already fixed on main, or matches `.out-of-scope/` | Closed |

## Procedure

1. **Out-of-scope check**: Scan `.out-of-scope/` first; if the request conflicts with an explicit boundary, cite the rule and mark `wontfix`.
2. **Codebase verification**: Search current code and tests to check whether the bug or capability already exists (`aitools search`, `aitools repo-map`).
3. **Classify**: Ask at most one clarifying round via `grill-user` only if ownership (`ready-for-agent` vs `ready-for-human`) hinges on product intent.
4. **Author brief or record exclusion**: Rewrite `ready-for-agent` items following [AGENT-BRIEF.md](AGENT-BRIEF.md), or record new broad boundary decisions in `.out-of-scope/` following [OUT-OF-SCOPE.md](OUT-OF-SCOPE.md).
