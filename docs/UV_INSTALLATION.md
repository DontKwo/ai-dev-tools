# Developer `uv` Installation Guide

> **For Everyday Users**: You do **not** need `uv`, Python, or any command-line tool to use the `AI-Dev-Tools` Setup Assistant. Download the standalone app from the [Download Table](../README.md#download).

Developers working on Python source code, running the unit test suite, or executing the strict repository linter use [Astral `uv`](https://docs.astral.sh/uv/) for deterministic Python environment management.

---

## Windows

Choose either the official standalone installer or a Windows package manager:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
# or package managers:
winget install --id=astral-sh.uv -e
scoop install main/uv
```

---

## macOS

Choose either the official standalone installer or Homebrew / MacPorts:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# or package managers:
brew install uv
sudo port install uv
```

---

## Linux

Use the official standalone installer (`curl`, `wget`, or isolated `pipx`):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# or with wget:
wget -qO- https://astral.sh/uv/install.sh | sh
# or isolated pipx:
pipx install uv
```

---

## Verification & Updating (All Platforms)

Restart your terminal so `PATH` updates, then run:

```bash
uv --version
uv self update
```

---

## Related Documentation

- [Project Overview](../README.md)
- [Developer Guide](DEVELOPMENT.md)
- [Desktop Installation Guide](INSTALLATION.md)
- [Security Policy](../SECURITY.md)
