# Developer Guide

Build, test, lint, and package `ai-dev-tools` across Windows, macOS, and Linux. Everyday users do **not** need Python or terminal tools and should use the standalone downloads in the [Download Table](../README.md#download).

## Prerequisites

1. Python 3.10 through 3.13
2. `uv` (follow [Developer uv Installation Guide](UV_INSTALLATION.md))
3. Git

---

## Platform Setup

### Windows

```powershell
git clone https://github.com/DontKwo/ai-dev-tools.git
cd ai-dev-tools
.\setup.bat
```

### macOS

```bash
git clone https://github.com/DontKwo/ai-dev-tools.git
cd ai-dev-tools
chmod +x setup.sh && ./setup.sh
```

### Linux

```bash
git clone https://github.com/DontKwo/ai-dev-tools.git
cd ai-dev-tools
chmod +x setup.sh && ./setup.sh
```

---

## Running Tests & Linter

```bash
uv run --no-project python -m unittest discover tests
uv run --no-project python scripts/claudemd_linter.py . --level strict --full
uv run --no-project python scripts/link_checker.py .
uv run --no-project python scripts/setup_gui.py --self-test
```

## Standardizing Repositories

Use the built-in CLI subcommands to scaffold templates, check cross-repo status, capture WebView screenshots, and crop icons:

```bash
uv run --no-project python scripts/cli.py standardize /path/to/repo --app-name MyApp
uv run --no-project python scripts/cli.py status-all
uv run --no-project python scripts/install_hooks.py . --all-hooks
```

## Packaging Standalone Executables

Install PyInstaller in an isolated environment and bundle `scripts/setup_gui.py` together with `templates/`, `configs/`, `skills/`, `assets/`, `scripts/setup_gui_ui.html`, and `scripts/setup_gui_theme.css` (`; ` separator on Windows, `:` on macOS/Linux) using `--icon=assets/icon.ico`.

---

## Related Documentation

- [Project Overview](../README.md)
- [Developer uv Installation Guide](UV_INSTALLATION.md)
- [Desktop Installation Guide](INSTALLATION.md)
- [System Architecture](ARCHITECTURE.md)
- [Developer Manual](DEV_MANUAL.md)
- [112 Linter Rules Reference](LINTER_RULES.md)
- [Security Policy](../SECURITY.md)
