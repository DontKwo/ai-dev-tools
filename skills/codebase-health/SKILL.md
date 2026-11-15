---
name: codebase-health
description: >-
  Audit and improve codebase quality by pruning unused imports and dead code, inferring type annotations, auditing variable naming quality, and checking for identifier typos. Use when refactoring, cleaning modules, or preparing releases.
---

# Codebase Health

Clean up zombie code, augment type hints, verify variable clarity, and correct spelling mistakes.

## Procedures

### 1. Prune Unused Imports and Dead Code

Detect and remove unused imports safely using AST analysis:

```bash
aitools prune [target]
```

Options:
- `--dry-run`: Display unreferenced imports without altering files.

### 2. Infer Type Annotations

Analyze function signatures and apply type annotations:

```bash
aitools boost [target]
```

Options:
- `--dry-run`: Print inferred signatures without writing changes.

### 3. Check Variable Naming Quality

Audit source code for single-letter and uninformative identifiers (Rule 38):

```bash
aitools vars [target]
```

### 4. Scan Code for Spelling Typos

Find spelling errors in identifiers and comments (Rule 39):

```bash
aitools spell [target]
```

## Verification

After applying modifications:
1. Run repository unit tests to confirm zero regressions.
2. Run `aitools lint . --level strict` to confirm clean status.

