# Defensive Security Audit Specification

## Overview
Checklists and pattern rules derived from vulnerability disclosures for static code inspection.

## Vulnerability Patterns
- **Injection Flaws**: Dynamic code execution (`eval`, `exec`), unescaped shell commands, raw SQL string concatenation.
- **Insecure Deserialization**: `yaml.load()` without SafeLoader, untrusted `pickle.loads()`, `marshal.loads()`.
- **Broken Access Control & IDOR**: Direct object references lacking user tenancy checks.
- **Path Traversal**: Unsanitized filesystem paths with `..` sequences.
- **Secret Exposure**: Hardcoded private keys, OAuth tokens, and high-entropy API credentials.
