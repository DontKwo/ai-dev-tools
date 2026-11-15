# ADR format specification

Store Architecture Decision Records in `docs/adr/` with zero-padded sequential numbers (`0001-slug.md`, `0002-slug.md`).

Create `docs/adr/` lazily when the first ADR is accepted.

## Minimal template

```md
# Use AST parsing for static linter checks

Static rules parse Python AST trees directly via stdlib ast to guarantee zero runtime side effects and deterministic line numbers.
```

An ADR can be a single short paragraph. Value comes from recording what was decided and why, so keep formatting lean.

## Optional sections

Include optional sections only when genuinely needed:

- **Status**: Frontmatter (`proposed | accepted | superseded by ADR-NNNN`) when revisiting active decisions.
- **Considered options**: Brief bullet list when rejected alternatives are likely to be suggested again later.
- **Consequences**: Non-obvious downstream operational constraints or migration costs.

## Qualifying criteria

All three must hold before creating an ADR:

1. **Hard to reverse**: Changing course later carries substantial migration or API cost.
2. **Surprising without context**: A future engineer reading the code would ask why this path was chosen.
3. **Real tradeoff**: Meaningful alternatives existed and concrete constraints drove the choice.

Skip ADRs for obvious defaults, local formatting choices, or easily reversible refactors.
