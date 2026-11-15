# Glossary format specification

Keep project terminology brief, opinionated, and strictly scoped to concepts unique to the codebase.

## Single-context repositories

Place one `GLOSSARY.md` file at the repository root:

```md
# Glossary

One or two sentences describing what this project does and which bounded context it owns.

## Terms

**Ticket**:
A vertical slice of user-visible work with an agreed public test seam.
_Avoid:_ Issue-task, chunk, story

**Seam**:
An explicit boundary where components meet and observable tests attach.
_Avoid:_ Boundary-hook, intercept-point
```

## Multi-context repositories

Add a root `GLOSSARY-MAP.md` linking each context directory to its own `GLOSSARY.md` when multiple independent domains share one repository.

## Authoring rules

1. **Pick one canonical winner**: List rejected synonyms after `_Avoid:_` so agents and linters converge on one name.
2. **Define what it IS**: Keep each definition to one or two direct sentences. Skip implementation play-by-play.
3. **Exclude generic programming words**: Skip standard library or pattern jargon (`DTO`, `factory`, `timeout`, `helper`) unless the project assigns special domain meaning.
4. **Sync `_Avoid:_` synonyms**: Mirror clear 1:1 banned aliases into `linter_custom.yaml` so Rule 91 flags drift automatically.
