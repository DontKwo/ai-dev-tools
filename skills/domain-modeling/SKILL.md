---
name: domain-modeling
description: >-
  Maintain a canonical project vocabulary in GLOSSARY.md and record
  architectural choices in docs/adr/. Use when naming domain concepts,
  spotting synonym drift across code or docs, syncing _Avoid_ terms into
  linter_custom.yaml, or documenting hard-to-reverse technical decisions.
---

# Domain modeling

Align code identifiers, documentation, and conversation around one crisp ubiquitous language, backed by short Architecture Decision Records.

Load [GLOSSARY-FORMAT.md](GLOSSARY-FORMAT.md) before editing `GLOSSARY.md` or `GLOSSARY-MAP.md`. Load [ADR-FORMAT.md](ADR-FORMAT.md) when an architectural choice meets the ADR criteria.

## When to act

- **Proactively on new terms**: When you introduce or encounter a project-specific noun or verb, add or refine it in `GLOSSARY.md`.
- **Proactively on synonym drift**: When two words describe the same concept (`client` vs `customer`, `task` vs `ticket`), name the winner, list synonyms under `_Avoid:_`, and propose syncing those synonyms into `linter_custom.yaml` (`replace` or `remove`).
- **On explicit ADR triggers**: When settling a choice that is hard to reverse, surprising without context, or resolved among serious alternatives, offer to write `docs/adr/NNNN-<slug>.md`.

## Integration with linter_custom.yaml

Whenever an entry in `GLOSSARY.md` defines `_Avoid:_` terms, enforce them automatically:

- Use `replace` entries in `linter_custom.yaml` for synonyms with a direct 1:1 replacement (for example mapping a superseded alias to the canonical term).
- Use `remove` entries for banned ambiguous names that require human refactoring.
- Re-run `aitools lint . --level strict` after updating `linter_custom.yaml`.
