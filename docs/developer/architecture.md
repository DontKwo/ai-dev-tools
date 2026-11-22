# Developer Architecture Manual

This document details the internal architecture, configuration pipelines, and execution engines of AI-Dev-Tools.

---

## Architectural Overview

AI-Dev-Tools consists of three primary execution layers:

```
+-------------------------------------------------------------------+
|                        User Entrypoints                           |
|  [GUI: setup_gui.py]      [CLI: apply_config.py]    [Unified: adt]|
+-------------------------------------------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|                       Declarative Config                          |
|         [config.yaml] <---> [yaml_utils.py (Pure-Python)]         |
+-------------------------------------------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|                         Execution Engine                          |
|   - Template Expander (templates/INSTRUCTIONS_TEMPLATE.md)        |
|   - File Installer (install_file: append / overwrite / skip)      |
|   - Backup Manager (.bak preservation on overwrite)               |
|   - Skills Provisioner (configure_skills)                         |
|   - MCP Server Registrar (configure_mcp_servers)                  |
|   - Git Pre-Commit Hook Installer (install_hooks.py)              |
+-------------------------------------------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|                   Verification & Linting Engine                   |
|     - AST Safety Analyzer                                         |
|     - Dependency Guard & Hallucination Detector                   |
|     - Secret Sanitizer                                            |
|     - Custom User Rules (linter_custom.yaml)                      |
+-------------------------------------------------------------------+
```

---

## Key Modules

### `scripts/apply_config.py`
The CLI runner script that loads YAML configuration, translates it into concrete file generation targets, runs data-loss risk analysis, prints dry-run reports, and executes filesystem updates.

### `scripts/setup_gui.py`
The desktop GUI application powered by a local loopback HTTP server and dark/light theme-token WebView frontend (`scripts/setup_gui_ui.html`), separating configuration state (`SetupGuiModel`) for full headless testing (`--self-test`).

### `scripts/yaml_utils.py`
A pure-Python YAML parser and serializer with PyYAML fallback. Eliminates external pip dependencies so configuration parsing operates in zero-dependency environments.

### `templates/INSTRUCTIONS_TEMPLATE.md`
The single canonical template from which all assistant-specific rule files (`CLAUDE.md`, `AGENTS.md`, `.cursorrules`, `.clinerules`, `.windsurfrules`, `.aider.conventions.md`, `.github/copilot-instructions.md`) are compiled.

---

## Data Loss Protection Protocol

Before writing any file, the execution engine evaluates the target path:

1. **New File**: Clean write; reports zero risk.
2. **Existing File + `write_mode: append`**:
   - Searches for `<!-- BEGIN AI-DEV-TOOLS -->` and `<!-- END AI-DEV-TOOLS -->`.
   - Replaces only the enclosed block.
   - Retains all user-authored content outside the markers.
3. **Existing File + `write_mode: overwrite`**:
   - Flags a `DATA LOSS RISK` warning.
   - Calculates the byte size of existing contents.
   - Saves a complete copy to `<target_path>.bak` before replacing the file.
4. **Existing File + `write_mode: skip`**:
   - Leaves the existing file untouched.

---

## Cross-Platform Build Pipeline

GitHub Actions (`.github/workflows/ci.yml`) compiles `scripts/setup_gui.py` into standalone executables using PyInstaller on every push:
- Windows: `adt-setup-Windows.exe`
- macOS: `adt-setup-macOS.zip`
- Linux: `adt-setup-Linux.tar.gz`

Executables bundle the pure-Python YAML engine, WebView UI assets, and rule templates directly inside the binary.

---

## Related Documentation

- [Project Overview](../../README.md)
- [System Architecture](../ARCHITECTURE.md)
- [Developer Guide](../DEVELOPMENT.md)
- [Security Policy](../../SECURITY.md)
