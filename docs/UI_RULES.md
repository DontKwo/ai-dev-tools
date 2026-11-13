# UI Quality Rules Reference

Multi-framework UI quality rules extending claudemd_linter.py.
Covers static source analysis, runtime interaction evidence, and layout verification.

## Baseline Status (Phase 0)

- Unit test suite: 403 tests passing (0 failures, 0 errors).
- Strict linter baseline: clean on existing repository diff.
- Rule numbering: rules 1 through 45 preserved; UI rules assign codes 46 through 79.

## Deviations from Original Spec

1. Python 3.11+ / standard library tomllib used for parsing .uilint.toml when available; fallback parser provided for environments without tomllib.
2. Rule 47 in diff mode emits a project-level notice when UI source files are modified but ui_evidence.json is absent, rather than flooding diff output.
3. Tree-sitter is optional; regex and AST tokenizers provide complete coverage when native grammar wheels are not installed.
4. Auto-fixers are omitted for UI rules per specification instruction.

## Architecture

The UI validation pipeline operates across three tiers:

1. Static Layer: Toolkit adapters inspect source code and markup to extract declared controls, screens, tooltips, and layout hazards into ui_manifest.json.
2. Runtime Layer: Framework-specific drivers execute real user inputs, record interaction traces with trusted flags, and output ui_evidence.json.
3. Join Layer: Claudemd linter compares manifest expectations against runtime evidence, enforcing coverage, combination depth, and layout integrity.
