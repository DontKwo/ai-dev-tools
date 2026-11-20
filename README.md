# ai-dev-tools

Make AI coding assistants self-verifying, token-efficient, and regression-free.

`ai-dev-tools` equips AI coding environments (Claude Code, Cursor, Google Antigravity, Cline, Windsurf, Codex, and GitHub Copilot) with unified rules, automated AST linting, and autonomous agent skills. Instead of relying solely on natural language prompts, the tool suite programmatically enforces code quality, catches hallucinations, and verifies correctness.

---

## Interactive Setup: Choose Your Path

AI-Dev-Tools provides two streamlined setup paths:

### Path A: Standalone Setup GUI (Common Users)

No Python commands or file editing required. Built automatically on every release.

1. Download the standalone executable for your operating system:
   - **Windows**: `adt-setup.exe`
   - **Linux**: `adt-setup-linux`
   - **macOS**: `adt-setup-macos`
2. Run the application to inspect your target workspace.
3. Choose your assistants, review the live safety check, and click **Apply Changes**.

*Or launch from source:* `python scripts/setup_gui.py` (or `adt gui`).

Detailed guide: [Everyday User Quickstart](docs/user/quickstart.md).

---

### Path B: Declarative YAML & CLI (Power Users)

Edit the configuration directly in any text editor and apply with flags:

1. Open [config.yaml](config.yaml) (shipped with full functionality and strict linting by default).
2. Choose your active assistants, write mode (`append`, `overwrite`, or `skip`), and rule profile.
3. Apply the settings via terminal:
   ```bash
   python scripts/apply_config.py --config config.yaml
   ```
4. Optional dry-run preview:
   ```bash
   python scripts/apply_config.py --config config.yaml --dry-run
   ```

Preset configurations are available in `configs/`:
- `configs/full.yaml` (Full functionality, all tools, all skills, strict linting)
- `configs/strict.yaml` (Strict profile for core assistants)
- `configs/standard.yaml` (Relaxed prose and comment styling)
- `configs/safe.yaml` (Essential bug, package, and secret safeguards with zero style churn)
- `configs/minimal.yaml` (Lightweight setup)

Detailed guides:
- [YAML Configuration Guide](docs/power-users/yaml-guide.md)
- [CLI Reference](docs/power-users/cli-reference.md)
- [Rule Strictness Profiles](docs/power-users/profiles.md)

---

## Documentation by Role

| Audience | Documentation | Description |
| :--- | :--- | :--- |
| **Everyday Users** | [User Quickstart](docs/user/quickstart.md) | 3-step setup via executable, zero terminal commands |
| **Power Users** | [YAML Guide](docs/power-users/yaml-guide.md) | Complete key-by-key schema documentation for `config.yaml` |
| **Power Users** | [CLI Reference](docs/power-users/cli-reference.md) | Flags, dry-run previews, JSON output, and automation |
| **Power Users** | [Rule Profiles](docs/power-users/profiles.md) | Full vs Standard vs Safe profile comparison |
| **Developers** | [Architecture Manual](docs/developer/architecture.md) | Execution engine, data-loss protection, and CI build pipeline |
| **Developers** | [Extending Guide](docs/developer/extending.md) | Adding assistants, custom skills, and custom linter rules |
| **Reference** | [91 Linter Rules](docs/LINTER_RULES.md) | Complete catalog of AST safety, security, and quality rules |

---

## Install as an Agent Plugin

Install skills directly into your agent harness:

- **Claude Code**: `/plugin marketplace add DontKwo/ai-dev-tools` then `/plugin install ai-dev-tools@ai-dev-tools`
- **GitHub Copilot CLI**: `copilot plugin marketplace add DontKwo/ai-dev-tools` then `copilot plugin install ai-dev-tools@ai-dev-tools`
- **VS Code**: Add `"DontKwo/ai-dev-tools"` to `chat.plugins.marketplaces` in `settings.json`
- **Gemini CLI**: `gemini skills install https://github.com/DontKwo/ai-dev-tools.git`
- **Universal (skills.sh)**: `npx skills@latest add DontKwo/ai-dev-tools`

---

## Everyday Developer Commands

You can run individual tool commands (`ailint`, `aifix`, `aitest`, `aidoctor`) or use the unified CLI dispatcher `adt`:

| Command | Alternative | Direct Script | Description |
|:---|:---|:---|:---|
| `adt lint` | `ailint` | `scripts/claudemd_linter.py` | Run 91-rule AST and style linter on git diffs (`--profile safe\|standard\|strict`). |
| `adt fix` | `aifix` | `scripts/lint_fixer.py` | Apply deterministic auto-fixes (operators, formatting, quotes). |
| `adt test` | `aitest` | `scripts/smart_test_runner.py` | Run only test suites impacted by changed files. |
| `adt doctor` | `aidoctor` | `scripts/doctor.py` | Audit tool configuration, environment paths, and health. |
| `adt apply` | - | `scripts/apply_config.py` | Apply declarative YAML configuration with dry-run support. |
| `adt gui` | - | `scripts/setup_gui.py` | Launch interactive graphical setup wizard. |

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
