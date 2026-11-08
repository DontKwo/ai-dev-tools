# Frequently Asked Questions (FAQ)

## What are the different lint levels?

The linter (`claudemd_linter.py`) supports three distinct verification levels:
- **`--level standard`**: Focuses on anti-AI writing guards, core AST safety, and basic equation formatting.
- **`--level strict`** *(Default)*: Includes all `standard` checks and adds term decomposition, banner removal, unit annotations, and descriptive naming checks (Rule 38).
- **`--level full`**: Includes everything in `strict` and adds strict type hints enforcement, zero-prints policy, dead code removal, and strict Qt GUI rules. This level is highly opinionated and typically run only when requested by the user.

*Note: Verification levels are distinct from the scan scope. For example, `--full` scans the whole repository, while `--diff` (the default) scans only git-changed files.*

## How do AST rules work?

The linter utilizes Python's built-in `ast` module to construct Abstract Syntax Trees (ASTs) of the target files. It traverses these trees to enforce rules programmatically instead of relying solely on regular expressions. This allows the linter to accurately identify variable assignments, function definitions, missing type hints, bare `except:` blocks, mutable default arguments, and circular imports without being confused by string literals or comments.

## How do I suppress a rule?

We use a strict suppression policy. You should only suppress a check if the code is genuinely correct as-is and cannot be refactored to comply with the rules.

To suppress checks:
- **Inline suppression**: End a line with `# noqa` to suppress all checks on that line, or specify codes like `# noqa: 11, 25` to suppress specific rules.
- **Multi-line comments exemption**: Place `# long-comment-ok` on or directly above a multi-line comment block to exempt it from the 2-line comment limit (Rule 17).

You can audit all suppressions in your codebase by running the linter with the `--noqa` flag.