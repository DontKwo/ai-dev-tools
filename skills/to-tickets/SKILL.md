---
name: to-tickets
description: Slice an approved spec or plan into vertical tracer-bullet tickets with explicit Blocked by edges.
---

# Convert spec into tickets

Break an approved specification into small, independently verifiable vertical tickets ready for implementation.

## Slicing rules

- **Vertical tracer bullets first**: Each ticket delivers one thin end-to-end behavioral slice (input validation -> core logic -> persisted state or output -> tests) instead of layer-by-layer horizontal chunks.
- **Expand-contract for wide refactors**: Split broad signature or schema changes into additive introduce -> migrate callers -> prune unused surface batches so main stays green at every step.
- **Explicit test seam per ticket**: Every ticket names the public seam where red-green tests attach and lists specific failure modes to test.
- **Dependency graph**: Declare explicit `Blocked by:` edges so independent tickets can run in parallel worktrees while serialized dependencies stay ordered.

## Ticket format

```md
# NN: Short behavioral title

Blocked by: none (or #01, #02)
Door: Two-way (or One-way -- explain migration rollback)

## Outcome
One to two sentences describing user- or caller-visible behavior after this ticket lands.

## Test seam
- Seam: `<module/command/endpoint>`
- Failure modes: empty input, invalid format, boundary value
```

## Storage destination

Check `docs/agents/issue-tracker.md` if present to create tickets in GitHub/GitLab Issues, or save numbered Markdown files under `.scratch/<feature>/issues/<NN>-<slug>.md` when working locally.
