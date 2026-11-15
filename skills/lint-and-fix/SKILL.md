---
name: lint-and-fix
description: >-
  Run the 91-rule code quality, AST safety, multi-framework UI quality, custom
  config rules, and anti-AI writing linter or execute deterministic auto-fixers.
  Use when validating code changes, auditing code style, fixing comparison
  syntax, checking UI stability, or verifying linter_custom.yaml rules.
---

# Lint and auto-fix

Execute static analysis, UI quality verification, custom rule scanning, and mechanical repairs on code and documentation.

## Commands

### 1. Run the linter

Run the 91-rule AST, multi-framework UI, custom config (Rule 91), and writing style auditor:

```bash
aitools lint [target] --level strict
```

Options:

- `--level standard`: Enforces anti-AI writing guards, core AST safety, math equation formatting, and custom `linter_custom.yaml` rules (Rule 91).
- `--level strict`: Adds term decomposition, banner removal, unit annotations, descriptive naming, stable UI IDs, and UI layout checks (rules 46 to 54 and 80 to 91).
- `--level full`: Strict type hints, zero prints, dead code checks, and complete UI quality rules (rules 1 to 91).
- `--diff`: Lints only files with git modifications (default in git repositories).
- `--full`: Forces a whole-repository audit.
- `--ui-evidence <path>`: Specifies path to custom `ui_evidence.json` trace.
- `--skip <codes>`: Comma-separated list of rule numbers to skip.
- `--only <codes>`: Run specific rule numbers only.
- `--no-cache`: Re-scan without reusing cached file results.

### 2. Custom repository and personal rules

Initialize or validate `linter_custom.yaml` (gitignored personal or repo-specific `remove`, `replace`, `allowed_vars`, `banned_vars`, and `file_guards` enforced under Rule 91):

```bash
aitools config --init-config
aitools doctor
```

### 3. Multi-framework UI audit (aiui)

Inspect, generate manifests, and audit UI evidence across desktop, mobile, and web frameworks:

```bash
# Initialize test driver template for a framework
aitools ui init --framework pyqt [target]

# Generate static ui_manifest.json
aitools ui manifest [target]

# Summarize runtime ui_evidence.json
aitools ui evidence [target]

# Run combined UI audit
aitools ui audit [target]
```

### 4. Run the auto-fixer

Apply deterministic fixes for safe syntax violations and `linter_custom.yaml` `replace` entries (UI rules require manual fixes):

```bash
aitools fix [target]
```

Options:

- `--dry-run`: Preview suggested replacements without modifying files.
- `--fix-emojis`: Strip emoji characters from code and docstrings.

## Verification

1. Check terminal output for report file paths (`lint_report_<target>.txt`).
2. Fix every reported violation until the terminal outputs `None. Lint clean.`
3. Ensure all unit tests pass after applying auto-fixes.
