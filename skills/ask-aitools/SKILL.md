---
name: ask-aitools
description: Workflow router and skill recommender for choosing the right ai-dev-tools workflow and phase transition.
---

# Ask ai-dev-tools

Recommend the right sequence of skills, `aitools` CLI commands, and context-window transitions for what the user wants to accomplish next.

Read [PHASE-BOUNDARIES.md](PHASE-BOUNDARIES.md) when helping the user decide between continuing, `/clear`, `/handoff`, spawning a subagent, or `/compact`.

## Routing workflow

1. Read the user's request and inspect any mentioned files or git state briefly if needed.
2. Point to the shortest concrete path through the skill catalog below.
3. Recommend the single next command to invoke and explain in two sentences why it fits this point in the workflow.

## Core delivery flow

```text
grill-user -> prototype -> to-spec -> to-tickets -> implement (drives tdd) -> lint-and-fix -> code-review -> definition-of-done -> session-wrap-up
```

- Start with `grill-user` whenever intent, scope, or architecture has unresolved choices.
- Use `prototype` before `to-spec` when UI flows or logic interactions need hands-on exploration first.
- Run `/to-spec` to freeze settled design choices and test seams.
- Run `/to-tickets` to slice work into vertical tracer-bullet tickets with `Blocked by` edges.
- Run `/implement` to execute tickets via `workspace-checkpoint`, `tdd`, `aitools test`, `aitools lint --level strict`, and `code-review`.
- Run `/definition-of-done` for pre-flight checks, merge danger rating, and PR drafting, then `/session-wrap-up` for environment retro and `memory/` updates.

## On-ramps by situation

| Situation | Recommended entry | Follow-up |
| :--- | :--- | :--- |
| Foggy multi-session epic or unknown constraints | `/wayfinder` | `research` or `prototype`, then `/to-spec` |
| Failing test or unexpected runtime behavior | `diagnosing-bugs` | `tdd` regression test, then `aitools lint` |
| Incoming bug report, PR, or issue backlog | `/triage` | `/implement` (ready-for-agent) or `.out-of-scope/` |
| Large coupled module or shrinking change velocity | `/improve-codebase-architecture` | `codebase-design` + `grill-user` |
| New repository onboarding | `/setup-ai-dev-tools` | `aitools doctor` |
| Switching harnesses or mid-phase fork | `/handoff` | Fresh session or `/clear` |
| Dense or confusing technical explanation | `/wait-what` | Continue |

## Specialist model-invoked capabilities

- **Domain and design**: `domain-modeling` (`GLOSSARY.md` and `docs/adr/`), `codebase-design` (deep modules and seams), `implicit-requirements`.
- **Verification and UI**: `exhaustive-testing`, `smart-test` (`aitools test`), `ux-audit` (`aitools ui audit`), `code-review`.
- **Codebase hygiene and context**: `lint-and-fix` (`aitools lint` / `aitools fix`), `codebase-health` (`aiprune`, `aiboost`, `aivars`, `aispell`), `codebase-context` (`airepo`, `aitree`, `aicontext`), `clean-encoding`, `dependency-guard` (`aideps`), `secret-sanitizer` (`aisec`), `doc-to-markdown` (`aimd`), `workspace-checkpoint`.
- **Agent authoring**: `writing-for-agents`, `research`.
