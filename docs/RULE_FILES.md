# AI Assistant Rule Files

This document explains how instruction files configure AI coding assistants in `ai-dev-tools`.

## Overview

AI coding assistants read instruction files to align with project standards, style rules, and verification requirements. This repository configures assistants at both the user level (global) and the repository level (workspace).

## Global Configuration vs Workspace Rules

### Global Configuration (Developer Machine)
When you run `setup.bat`, `setup.sh`, or `scripts/configure.py`, configuration files are written to your user home directory (such as `~/.claude/CLAUDE.md` or `~/.gemini/config/AGENTS.md`). These global rules ensure that every project you open inherits unified guidelines for terse communication, type annotations, and automated linting.

### Workspace Rules (Repository Root)
The root directory of this repository includes canonical instruction files:
- `AGENTS.md`
- `CLAUDE.md`
- `.cursorrules`
- `.clinerules`
- `.windsurfrules`
- `.aider.conventions.md`

These files exist in the repository so that fresh clones, external contributors, and continuous integration environments (like GitHub Actions or cloud VMs) receive the exact same rules without requiring local machine setup first.

## Supported AI Assistants

| Assistant | Global Path | Workspace Path | Format Notes |
|:---|:---|:---|:---|
| **Claude Code** | `~/.claude/CLAUDE.md` | `CLAUDE.md` | Standard markdown rules |
| **Cursor IDE** | `~/.cursorrules` | `.cursorrules` & `.cursor/rules/developer-rules.mdc` | Includes Cursor MDC frontmatter |
| **Cline & Roo Code** | `~/.clinerules` | `.clinerules` | Standard markdown rules |
| **Google Antigravity (AGY)** | `~/.gemini/config/AGENTS.md` | `AGENTS.md` & `.agent/rules/user_rules.md` | Native Antigravity rules and skills |
| **OpenAI Codex & ChatGPT** | `~/.codex/instructions.md` | `AGENTS.md` & `OPENAI.md` | Universal agent markdown convention |
| **Windsurf IDE** | `~/.windsurfrules` | `.windsurfrules` | Codeium / Windsurf configuration |
| **GitHub Copilot** | N/A | `.github/copilot-instructions.md` | Workspace copilot instructions |
| **Aider CLI** | `~/.aider.conventions.md` | `.aider.conventions.md` | Aider conventions format |

## Synchronizing Rule Files

The repository templates live in `templates/`. To synchronize changes across all root instruction files, run the rule synchronizer:

```bash
uv run --no-project python scripts/sync_rules.py
```

Or use the shortcut:

```bash
aisync
```

## Behavior Layer Verification

The test suite enforces that all canonical rule files remain present and consistent:

```bash
uv run --no-project python -m unittest tests/test_behavior_layer.py
```

This test checks that each rule file contains required sections for quality, testing standards, UI guidelines, interaction rules, and memory management.


---

## Related Documentation

- [Project Overview](../README.md)
- [Agent Skills Guide](SKILLS_GUIDE.md)
- [Developer Guide](DEVELOPMENT.md)
- [112 Linter Rules Reference](LINTER_RULES.md)
- [Security Policy](../SECURITY.md)
