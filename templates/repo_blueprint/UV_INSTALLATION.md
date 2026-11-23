# Developer `uv` Installation Guide

> **For Everyday Users**: You do **not** need `uv`, Python, or any command-line tool to use `<AppName>`. Download the standalone desktop app or mobile APK directly from the [Download Table](../README.md#download).

Developers working on Python source code, running test suites, or executing the strict repository linter use [Astral `uv`](https://docs.astral.sh/uv/) for deterministic Python environment management.

---

## Platform Instructions

### Windows

Choose either the official standalone installer or a Windows package manager:

#### Official Standalone Installer (PowerShell)

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

#### Package Managers (`winget` or `scoop`)

```powershell
winget install --id=astral-sh.uv -e
# or
scoop install main/uv
```

### macOS

Choose either the official standalone installer or a macOS package manager:

#### Official Standalone Installer

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### Package Managers (Homebrew or MacPorts)

```bash
brew install uv
# or
sudo port install uv
```

### Linux

Choose the official standalone installer (`curl` or `wget`) or `pipx`:

#### Official Standalone Installer

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

With `wget`:

```bash
wget -qO- https://astral.sh/uv/install.sh | sh
```

#### Isolated PyPI Install (`pipx`, All Platforms)

```bash
pipx install uv
```

---

## Verification & Updating (All Platforms)

Open a new terminal window after installing so `PATH` reloads cleanly, then check your version:

```bash
uv --version
```

Standalone installations (`irm` / `curl` installer scripts) can update in place anytime:

```bash
uv self update
```

Always execute repository Python commands using `--no-project` with the target virtual environment or system runner as documented in [Developer Guide](DEVELOPMENT.md).

---

## Related Documentation

- [Project Overview](../README.md)
- [Developer Guide](DEVELOPMENT.md)
- [Desktop Installation Guide](INSTALLATION.md)
- [Security Policy](../SECURITY.md)
