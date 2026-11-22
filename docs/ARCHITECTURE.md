# System Architecture

This document summarizes the modular architecture of `ai-dev-tools`, including its unified CLI, WebView setup wizard, 112-rule AST/repository linter, MCP server, and agent skills system.

## Core Layers

1. **User Entrypoints (`scripts/setup_gui.py`, `scripts/cli.py`, `bin/adt`)**:
   - `scripts/setup_gui.py` runs a local loopback HTTP server paired with a light/dark WebView HTML/CSS/JS frontend (`scripts/setup_gui_ui.html` and `scripts/setup_gui_theme.css`), supporting `--self-test` and `--screenshot`.
   - `scripts/cli.py` dispatches `adt` subcommands (`lint`, `fix`, `test`, `standardize`, `status-all`, `screenshots`, `crop-icons`, `git-hooks`, `links`, `doctor`).
2. **Configuration & Sync Engine (`scripts/apply_config.py`, `scripts/configure.py`, `scripts/sync_rules.py`, `scripts/yaml_utils.py`)**:
   - Compiles `templates/INSTRUCTIONS_TEMPLATE.md` into managed instruction blocks with automatic `.bak` backups and `.adt-state.json` manifests for clean uninstalls.
   - `templates/repo_blueprint/` provides the single source of truth for MIT `LICENSE`, `SECURITY.md`, `README.md`, `INSTALLATION.md`, `APK_INSTALLATION.md`, `UV_INSTALLATION.md`, `OPENFOAM_INSTALLATION.md`, and `.github/workflows/ci.yml`.
3. **112-Rule Verification Engine (`scripts/claudemd_linter.py`, `scripts/repo_standards_rules.py`, `scripts/link_checker.py`)**:
   - Combines AST static checks (Rules 1-45, 91-100), UI manifest/evidence audits (Rules 46-90), and cross-repository standards (Rules 101-112).

## Data Loss Protection

Every workspace write checks existing targets:
- `append`: replaces only content between `<!-- BEGIN AI-DEV-TOOLS -->` and `<!-- END AI-DEV-TOOLS -->`.
- `overwrite`: creates a collision-safe `.bak` backup before replacing atomically via temporary files.
- `skip`: leaves pre-existing files untouched.

## Related Documentation

- [Project Overview](../README.md)
- [Developer Guide](DEVELOPMENT.md)
- [Detailed Architecture Notes](developer/architecture.md)
- [Extending AI-Dev-Tools](developer/extending.md)
- [112 Linter Rules Reference](LINTER_RULES.md)
- [Security Policy](../SECURITY.md)
