# Rule Profiles Reference

AI-Dev-Tools provides preconfigured rule profiles to balance linter strictness against workflow friction.

---

## Profile Comparison

| Profile | Target Audience | Writing Hygiene (Rules 1-10) | Single-Letter Names (Rule 38) | AST Safety & Secrets |
| :--- | :--- | :--- | :--- | :--- |
| **full** / **strict** | New projects, rigorous codebases | Enforced | Enforced | Enforced |
| **standard** | Active teams, everyday coding | Relaxed | Relaxed | Enforced |
| **safe** | Existing codebases, established repos | Relaxed | Relaxed | Enforced |
| **minimal** | Single tool setup, lightweight | Relaxed | Relaxed | Essential only |

---

## Detailed Profile Profiles

### 1. Full / Strict (`configs/full.yaml`)
- **Intent**: Maximum code quality, strict typing, zero prose bloat.
- **Rules Enforced**: All 91 rules active.
- **Key Constraints**:
  - Functions require explicit parameter and return type hints.
  - Ban on single-letter variables (`k, v, x`).
  - Ban on em dashes and negative parallelisms in docstrings and comments.
  - Mandatory linter verification after changes.

### 2. Standard (`configs/standard.yaml`)
- **Intent**: Balanced quality checks for standard team environments.
- **Skipped Rules**: 1 (em dash), 5 (passive voice), 17 (type comment), 38 (single-letter variable).
- **Key Constraints**:
  - AST security checks remain fully active.
  - Undeclared dependency and hallucination checks active.
  - Secret scanning active.
  - Allows common shorthand identifiers (like `i, j` in loops or `x, y` in coordinates).

### 3. Safe Profile (`configs/safe.yaml`)
- **Intent**: For existing codebases where stylistic changes would cause noisy diffs.
- **Skipped Rules**: Stylistic prose, equation formatting, and naming pedantry.
- **Key Constraints**:
  - Fixes bugs and comparison syntax (`== None` -> `is None`).
  - Guards against hallucinated PyPI package imports.
  - Scans and redacts exposed credentials, API keys, and tokens.
  - Zero unwanted stylistic churn on clean working code.

### 4. Minimal (`configs/minimal.yaml`)
- **Intent**: Lightweight configuration for a single assistant with core AST safeguards.
- **Skills**: Disabled by default.
- **Git Hook**: Disabled by default.


---

## Related Documentation

- [Project Overview](../../README.md)
- [CLI Reference](cli-reference.md)
- [YAML Configuration Guide](yaml-guide.md)
- [112 Linter Rules Reference](../LINTER_RULES.md)
- [Security Policy](../../SECURITY.md)
