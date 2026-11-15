# Phase boundaries

A phase is a coherent stage of work inside a session: grilling, prototyping, writing a spec, implementing tickets, or reviewing a branch. A phase boundary sits between two finished stages, where you decide how to carry context forward.

Avoid resetting or compacting mid-phase, because interrupting active reasoning strips working hypotheses and half-verified file state.

## The five options ranked by fidelity

| Option | Action | Best used when |
| :--- | :--- | :--- |
| 1. Continue | Stay in current session | Next phase needs verbatim reasoning and smart-zone headroom remains |
| 2. `/clear` | Drop context cleanly | Current session exploration and dead ends are irrelevant next |
| 3. `/handoff` | Write redacted temp file | Moving to another harness, directory, colleague, or side task |
| 4. Subagent | Delegate isolated work | Task is tightly scoped and needs zero live steering (`code-review`, `research`) |
| 5. `/compact` | Summarize into fresh session | Context is heavy, staying in same repo/harness, and prior decisions matter |

## Decision order at the boundary

Work top to bottom and take the first match:

1. **Can you continue safely?** Keep the same session when the next phase directly builds on active reasoning (for example, `grill-user` straight into `prototype` or `implement`) and enough context budget remains.
2. **Is the prior trail disposable?** Run `/clear` after a completed branch merges or when switching to an unrelated topic. Zero summary loss, full clean window.
3. **Must context travel outside this session?** Run `/handoff` only when changing editors/models, moving across repositories, passing work to someone else, or parking an urgent side discovery without losing your place.
4. **Can it run unsupervised?** Delegate read-heavy exploration (`research`) or independent diff checks (`code-review`) to a fresh-context subagent so noise stays out of the parent window.
5. **Otherwise `/compact` with focus.** Pass an explicit instruction describing what the summary must preserve (for example, `/compact retain the locked schema decisions and failing test seam`).
