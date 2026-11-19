# ai-dev-tools

> Make AI coding assistants self-verifying, token-efficient, and regression-free.

`ai-dev-tools` equips AI coding environments (Claude Code, Cursor, Google Antigravity, Cline, Windsurf, Codex, and GitHub Copilot) with unified rules, automated AST linting, and autonomous agent skills. Instead of relying solely on natural language prompts, the tool suite programmatically enforces code quality, catches hallucinations, and verifies correctness.

---

## Quickstart

### Run the Installer

Run the interactive setup wizard for your operating system:

#### Windows
```cmd
setup.bat
```

#### Linux & macOS
```bash
chmod +x setup.sh
./setup.sh
```

### Install as a Plugin

Install skills directly into your agent harness:

- **Claude Code**: `/plugin marketplace add DontKwo/ai-dev-tools` then `/plugin install ai-dev-tools@ai-dev-tools`
- **GitHub Copilot CLI**: `copilot plugin marketplace add DontKwo/ai-dev-tools` then `copilot plugin install ai-dev-tools@ai-dev-tools`
- **VS Code**: Add `"DontKwo/ai-dev-tools"` to `chat.plugins.marketplaces` in `settings.json`
- **Gemini CLI**: `gemini skills install https://github.com/DontKwo/ai-dev-tools.git`
- **Universal (skills.sh)**: `npx skills@latest add DontKwo/ai-dev-tools`

---

## How It Works

`ai-dev-tools` separates autonomous agent operations from developer terminal commands:

- **Autonomous Agent Skills (`skills/`)**: Skills are procedural runbooks for AI assistants. The assistant loads them into prompt context dynamically when matching tasks arise (such as debugging, running test cycles, or checking secrets). Developers do not need to call or manage skills manually.
- **Model Context Protocol Server (`mcp/server.py`)**: Exposes native analysis tools over JSON-RPC for MCP-compatible editors and agents.
- **Developer CLI Utilities (`bin/`)**: Lightweight command-line shortcuts for developers to lint, auto-fix, and test changes directly in the terminal.

---

## Everyday Developer Commands

You can run individual tool commands (`ailint`, `aifix`, `aitest`, `aidoctor`) or use the unified CLI dispatcher `adt`:

| Command | Alternative | Direct Script | Description |
|:---|:---|:---|:---|
| `adt lint` | `ailint` | `scripts/claudemd_linter.py` | Run 91-rule AST and style linter on git diffs (`--profile safe\|standard\|strict`). |
| `adt fix` | `aifix` | `scripts/lint_fixer.py` | Apply deterministic auto-fixes (operators, formatting, quotes). |
| `adt test` | `aitest` | `scripts/smart_test_runner.py` | Run only test suites impacted by changed files. |
| `adt doctor` | `aidoctor` | `scripts/doctor.py` | Audit tool configuration, environment paths, and health. |
| `adt init` | - | `scripts/configure.py` | Interactive setup wizard with rule profile selection. |

---

## Pre-Commit Integration

Add `ai-dev-tools` to your `.pre-commit-config.yaml` to verify changes before commit:

```yaml
repos:
  - repo: https://github.com/DontKwo/ai-dev-tools
    rev: v0.2.0
    hooks:
      - id: adt-lint
      - id: adt-secrets
```

---

## GitHub Actions CI/CD Integration

Verify code quality and guardrails on pull requests using the composite action:

```yaml
# .github/workflows/ai-guardrails.yml
name: AI Guardrails
on: [push, pull_request]

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: DontKwo/ai-dev-tools@main
        with:
          profile: strict
```

---

## Verification

Run the test suite:
```bash
uv run --no-project python -m unittest discover tests
```

Run the strict linter:
```bash
uv run --no-project python scripts/claudemd_linter.py . --level strict
```

---

## Documentation for Power Users

- [User Guide](docs/USER_GUIDE.md): Developer manual for terminal workflows and CLI utilities.
- [AI Assistant Rule Files](docs/RULE_FILES.md): Supported environments, global vs workspace files, and rule synchronization.
- [Agent Skills Guide](docs/SKILLS_GUIDE.md): Catalog of autonomous agent skills and progressive disclosure model.
- [Developer Manual](docs/DEV_MANUAL.md): Complete CLI flags and programmatic APIs for all scripts.
- [Linter Rules](docs/LINTER_RULES.md): Specifications for all 91 rules across AST safety, UI stability, and style.
- [Setup Guide](docs/SETUP_GUIDE.md): Installation options across operating systems.
- [FAQ](docs/FAQ.md): Common questions, verification levels, and rule suppressions.

---

## Acknowledgements & Third-Party Credits

This project builds on, adapts, or preserves work from the open-source community:
- [Matt Pocock (`mattpocock/skills`)](https://github.com/mattpocock/skills) for workflow skills and prompt engineering routines.
- [Jesse Vincent (`obra/superpowers`)](https://github.com/obra/superpowers) for agentic software engineering discipline and TDD methodology.
- [Dietrich Gebert (`DietrichGebert/ponytail`)](https://github.com/DietrichGebert/ponytail) for the minimalist senior developer decision ladder.
- [Meta Platforms, Inc. (`meta/astryx`)](https://github.com/meta/astryx) for accessible React 19 UI component templates and design token schemas.
- [RTK Authors (`rtk-ai/rtk`)](https://github.com/rtk-ai/rtk) for terminal token compression patterns.
- [Tirth Patel (`tirth8205/code-review-graph`)](https://github.com/tirth8205/code-review-graph) for AST blast-radius analysis and code graph modeling.
- [Mert Köseoğlu (`mksglu/context-mode`)](https://github.com/mksglu/context-mode) for sandbox execution and SQLite FTS5 search patterns.
- [Erkam Yaman (`erkamyaman/rust-anything`)](https://github.com/erkamyaman/rust-anything) for behavior recording and migration replay patterns.
- [elementalsouls (`elementalsouls/Claude-BugHunter`)](https://github.com/elementalsouls/Claude-BugHunter) for defensive security audit checklists.

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for full license details.

## Developer Tools Disclaimer

DEVELOPER TOOLS DISCLAIMER: ai-dev-tools provides automated AST analysis, code inspection, and refactoring scripts. The software is provided AS IS without warranty of any kind. The author assumes no liability for code modifications, data loss, or build errors resulting from automated tool execution.
