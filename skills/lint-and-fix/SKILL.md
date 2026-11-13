---
name: lint-and-fix
description: >-
  Run the 79-rule code quality, AST safety, multi-framework UI quality, and anti-AI writing linter or execute guaranteed deterministic auto-fixers. Use when validating code changes, auditing code style, fixing comparison syntax, or checking UI stability.
---

# Lint and Auto-Fix

Execute static analysis, UI quality verification, and mechanical repairs on code and documentation.

## Commands

### 1. Run the Linter

Run the 79-rule AST, multi-framework UI, and writing style auditor:

```bash
uv run --no-project python scripts/claudemd_linter.py [target] --level strict
```

Options:
- `--level standard`: Enforces anti-AI writing guards, core AST safety, and math equation formatting.
- `--level strict`: Adds term decomposition, banner removal, unit annotations, descriptive naming, stable UI IDs, and UI layout checks.
- `--level full`: Strict type hints, zero prints, dead code checks, and complete UI quality rules (rules 46 to 79).
- `--diff`: Lints only files with git modifications (default in git repositories).
- `--full`: Forces a whole-repository audit.
- `--ui-evidence <path>`: Specifies path to custom ui_evidence.json trace.
- `--skip <codes>`: Comma-separated list of rule numbers to skip.
- `--only <codes>`: Run specific rule numbers only.

### 2. Multi-Framework UI Audit (aiui)

Inspect, generate manifests, and audit UI evidence across desktop, mobile, and web frameworks:

```bash
# Initialize test driver template for a framework
uv run --no-project python scripts/aiui.py init --framework pyqt [target]

# Generate static ui_manifest.json
uv run --no-project python scripts/aiui.py manifest [target]

# Summarize runtime ui_evidence.json
uv run --no-project python scripts/aiui.py evidence [target]

# Run combined UI audit
uv run --no-project python scripts/aiui.py audit [target]
```

### 3. Run the Auto-Fixer

Apply safe, mechanical fixes for deterministic violations (UI rules do not use auto-fixers):

```bash
uv run --no-project python scripts/lint_fixer.py [target]
```

Options:
- `--dry-run`: Preview suggested replacements without modifying files.
- `--fix-emojis`: Strip emoji characters from code and docstrings.

## Verification

1. Check terminal output for report file paths (`lint_report_<target>.txt`).
2. Fix all reported issues until the terminal outputs `None. Lint clean.`
3. Ensure all unit tests pass after applying auto-fixes.

