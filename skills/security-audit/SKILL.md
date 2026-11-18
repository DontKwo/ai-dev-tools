---
name: security-audit
description: Run defensive static code security audits to detect injection flaws, hardcoded credentials, unsafe deserialization, and path traversal vulnerabilities.
---

# Defensive Security Audit

Perform systematic static security audits on application code and diffs before merges.

## Audit Checklist

1. **Injection Vulnerabilities**:
   - Verify no dynamic execution (`eval()`, `exec()`, raw `os.system()`).
   - Check all subprocess calls use structured argument lists.
   - Verify all SQL queries use parameterized placeholders (`?` or `:name`).

2. **Deserialization & Parsers**:
   - Ensure all YAML loading uses `yaml.safe_load()` or explicit `Loader=yaml.SafeLoader`.
   - Disallow untrusted `pickle.loads()` and `marshal.loads()`.

3. **Secrets & Credentials**:
   - Scan for hardcoded API keys, private keys, and OAuth tokens.
   - Verify credentials are read from environment variables or secure key vaults.

4. **Access Control & Path Traversal**:
   - Ensure file operations resolve and constrain paths within allowed directories.
   - Guard against `..` relative traversal in user-supplied filenames.
