# User Guide

This guide covers daily terminal workflows for developers using `ai-dev-tools`.

## Human vs Agent Responsibilities

- **For AI Agents**: Skills (`skills/`) and MCP server tools (`mcp/`) run autonomously. The AI assistant loads skills and calls MCP tools automatically during planning, coding, and debugging. You do not need to invoke them manually.
- **For Developers**: The CLI shortcuts below give you direct control in your terminal to lint, auto-fix, and test changes before committing.

## Everyday Developer Commands

You can use either the unified `adt` CLI dispatcher or individual utility shortcuts.

### 1. Unified CLI (`adt`)

The `adt` command provides a single entry point for all developer commands:
```bash
adt lint                  # Run linter on git diff
adt lint --profile safe   # Run linter with safe profile
adt fix                   # Apply safe auto-fixes
adt test                  # Run tests impacted by changes
adt doctor                # Run diagnostic environment audit
adt init                  # Run interactive configuration wizard
```

### 2. Lint Changes (`ailint` / `adt lint`)
Run the 91-rule AST and style linter. By default, it checks only files modified in git:
```bash
adt lint
```
To run with a specific rule profile:
```bash
adt lint --profile safe       # Essential bug, hallucination, and security checks
adt lint --profile standard   # AST safety and dependencies with relaxed prose checks
adt lint --profile strict     # Full 91-rule enforcement (default)
```
To run a full audit across the entire repository:
```bash
adt lint . --full --level strict
```

### 3. Auto-Fix Common Issues (`aifix` / `adt fix`)
Apply deterministic, safe fixes (such as `== None` to `is None`, curly quote normalization, and emoji removal):
```bash
adt fix
```
Or run directly:
```bash
uv run --no-project python scripts/lint_fixer.py .
```

### 4. Smart Test Runner (`aitest` / `adt test`)
Detect modified files from git diffs and run only the unit test suites impacted by those changes:
```bash
adt test
```
Or run directly:
```bash
uv run --no-project python scripts/smart_test_runner.py
```

### 5. Health Check (`aidoctor` / `adt doctor`)
Check that your tools, environment paths, and instruction files are valid:
```bash
adt doctor
```

## Configuring Profiles and Overrides

Configure profiles and rule toggles in `.aitools.toml`:
```toml
[linter]
profile = "strict"    # Presets: "strict" (default), "standard", "safe"
diff_only = true
disable = [1, 5, 38]  # Disable specific rule codes
enable = []           # Enable specific rule codes

# Define custom named profiles
[linter.profiles.team]
level = "standard"
skip = [1, 5, 38]
```

## Automated CI/CD & Pre-Commit Hooks

### Pre-Commit Hooks
Run automated linter and secret checks before commit via `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/DontKwo/ai-dev-tools
    rev: v0.2.0
    hooks:
      - id: adt-lint
      - id: adt-secrets
```

### GitHub Actions
Verify pull requests and commits using the composite action:
```yaml
# .github/workflows/ai-guardrails.yml
name: AI Guardrails
on: [push, pull_request]

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: DontKwo/ai-dev-tools@main
        with:
          profile: strict
```

## Additional Codebase Utilities

When you need specific diagnostics from the command line:

- **Dead Code Pruner (`aiprune`)**: Identify and clean unused imports and unreferenced functions.
- **Type Booster (`aiboost`)**: Infer parameter and return type hints based on default values and call sites.
- **Dependency Guard (`aideps`)**: Scan for undeclared external imports or hallucinated package names.
- **Encoding Cleaner (`scripts/clean_encoding.py`)**: Repair mojibake and double-encoded UTF-8 sequences.
- **Codebase Context (`airepo`, `aitree`, `aislice`)**: Generate compact AST symbol trees, directory hierarchies, or file slices.

## Power User Reference

- [docs/DEV_MANUAL.md](DEV_MANUAL.md): Full CLI flags and programmatic APIs for every script.
- [docs/RULE_FILES.md](RULE_FILES.md): Supported assistants, root vs global rule files, and synchronization.
- [docs/SKILLS_GUIDE.md](SKILLS_GUIDE.md): Autonomous agent skills catalog and execution model.
- [docs/LINTER_RULES.md](LINTER_RULES.md): Specifications for all 91 linter rules.
- [docs/SETUP_GUIDE.md](SETUP_GUIDE.md): Installation details across operating systems.
- [docs/FAQ.md](FAQ.md): Common questions, verification levels, and rule suppressions.
