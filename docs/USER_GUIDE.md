# User Guide

This guide provides a detailed manual on using each tool in `ai-dev-tools` to audit, clean, and lint your codebases.

## Auditing and Context Gathering

- **AST Symbol Tree (`airepo` / `scripts/repo_map.py`)**: Use this tool to generate a compressed AST-level structural map of your codebase. This helps provide concise context to LLMs.
- **Directory Overview (`aitree` / `scripts/dir_overview.py`)**: Generates a token-efficient visual hierarchy of your repository, including line counts and file sizes.
- **File Slicer (`aislice` / `scripts/slice_file.py`)**: View targeted line ranges of files to provide exact contexts.
- **Dependency Guard (`aideps` / `scripts/check_dependencies.py`)**: Scan your project for hallucinated imports and undeclared external packages.

## Linting the Codebase

- **45-Rule AST Linter (`ailint` / `scripts/claudemd_linter.py`)**:
  This is the core linting engine. By default, it runs over Git diffs.
  To run a full codebase audit:
  ```bash
  uv run --no-project python scripts/claudemd_linter.py . --full --level strict
  ```
  This will flag AST issues, missing type hints, AI writing patterns, and UI/UX standard violations.

## Cleaning and Auto-Fixing

- **Safe Auto-Fixer (`aifix` / `scripts/lint_fixer.py`)**:
  Applies low-risk deterministic fixes such as replacing `== None` with `is None`, standardizing Unicode, and stripping emojis.
  ```bash
  uv run --no-project python scripts/lint_fixer.py .
  ```
- **Dead Code Pruner (`aiprune` / `scripts/prune_dead_code.py`)**:
  Automatically tracks down and removes unused imports and unreferenced functions.
- **Type Booster (`aiboost` / `scripts/boost_types.py`)**:
  Infers missing parameter and return type hints based on default values and usage, adding them safely to your function signatures.
- **Encoding Cleaner (`clean-encoding` / `scripts/clean_encoding.py`)**:
  Repairs corrupted double-encoded UTF-8 sequences and mojibake in your files.