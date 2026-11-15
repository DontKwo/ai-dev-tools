# ai-dev-tools

Portable environment configuration and automated tooling to configure any machine (Windows, Linux, or macOS) across AI developer tools (Claude Code, Cursor, Cline, Roo Code, Google Antigravity, OpenAI Codex, Windsurf, GitHub Copilot, Aider) with unified style rules, an AST linter, auto-fixers, context optimizers, and a native MCP server.

---

## Supported AI Tools

`scripts/configure.py` installs rule instructions and registers MCP servers for each supported environment:

| AI Tool | Global Target | Workspace Target | Format Notes |
|:---|:---|:---|:---|
| **Claude Code** | `~/.claude/CLAUDE.md` | `CLAUDE.md` | Standard markdown rules |
| **Cursor IDE** | `~/.cursorrules` | `.cursorrules` & `.cursor/rules/developer-rules.mdc` | Includes Cursor MDC frontmatter |
| **Cline & Roo Code** | `~/.clinerules` | `.clinerules` | Standard markdown rules |
| **Google Antigravity (AGY)** | `~/.gemini/config/AGENTS.md` | `AGENTS.md` & `.agent/rules/user_rules.md` | Native Antigravity rules and skills |
| **OpenAI Codex & ChatGPT** | `~/.codex/instructions.md` | `AGENTS.md` & `OPENAI.md` | Universal agent markdown convention |
| **Windsurf IDE** | `~/.windsurfrules` | `.windsurfrules` | Codeium / Windsurf configuration |
| **GitHub Copilot** | N/A | `.github/copilot-instructions.md` | Workspace copilot instructions |
| **Aider CLI** | `~/.aider.conventions.md` | `.aider.conventions.md` | Aider conventions format |

---

## Install as a plugin

Install skills directly into your harness so updates track upstream changes cleanly (see [.agents/install-block.md](.agents/install-block.md)):

- **Claude Code**: `/plugin marketplace add DontKwo/ai-dev-tools` then `/plugin install ai-dev-tools@ai-dev-tools`
- **GitHub Copilot CLI**: `copilot plugin marketplace add DontKwo/ai-dev-tools` then `copilot plugin install ai-dev-tools@ai-dev-tools`
- **VS Code**: Add `"DontKwo/ai-dev-tools"` to `chat.plugins.marketplaces` in `settings.json`
- **Gemini CLI**: `gemini skills install https://github.com/DontKwo/ai-dev-tools.git`
- **Universal (skills.sh)**: `npx skills@latest add DontKwo/ai-dev-tools`

## Quickstart

Run the installer for your platform:

### Windows
```cmd
setup.bat
```

### Linux & macOS
```bash
chmod +x setup.sh
./setup.sh
```

### Direct CLI Invocation
```bash
# Configure all tools globally
uv run --no-project python scripts/configure.py --tools all --scope global

# Configure specific tools in workspace
uv run --no-project python scripts/configure.py --tools cursor,cline --scope workspace

# Interactive setup menu
uv run --no-project python scripts/configure.py
```

---

## Three Tool Interfaces

The tooling suite exposes 3 complementary access methods:

1. **Agent Skills (`skills/`)**: On-demand workflow runbooks for AI agents across Google Antigravity, Claude Code, Cursor, Windsurf, Cline, and Codex. Skills use progressive disclosure, loading into prompt context only when triggered.
2. **Native MCP Server (`mcp/server.py`)**: Standard Model Context Protocol server exposing 28 tools for direct tool calling in Claude Desktop, Claude Code, Cursor, Windsurf, Cline, and Antigravity.
3. **Unified CLI & Shortcuts (`bin/`)**: Top-level `aitools` command plus individual shell shortcuts for terminal execution.

---

## Tool Reference

| Capability | Script | Skill | CLI | Description |
|:---|:---|:---|:---|:---|
| **Unified CLI** | `scripts/cli.py` | N/A | `aitools` | Top-level entry point for lint, fix, ui, skills, doctor, and config. |
| **91-Rule Linter** | `scripts/claudemd_linter.py` | `lint-and-fix` | `ailint` | AST, multi-framework UI, custom config, and style linter (diff default, `--full` for repo). |
| **Link Checker** | `scripts/link_checker.py` | N/A | `ailinks` | Audits local markdown links, heading anchors, and release download targets. |
| **Multi-Framework UI** | `scripts/aiui.py` | `lint-and-fix` | `aiui` | Manifest generation, runtime evidence parsing, and layout audits. |
| **Skills Manager** | `scripts/skills_manager.py` | N/A | `aiskills` | Status matrix, enable, disable, and sync skills across 6 editors. |
| **Safe Auto-Fixer** | `scripts/lint_fixer.py` | `lint-and-fix` | `aifix` | Applies deterministic fixes (`== None`, smart quotes, emojis). |
| **Plan Griller** | `scripts/grill_user.py` | `grill-user` | `aigrill` | Interrogates plans, architecture, and tradeoffs. |
| **Dead Code Pruner** | `scripts/prune_dead_code.py` | `codebase-health` | `aiprune` | Removes unused imports and unreferenced functions. |
| **Type Booster** | `scripts/boost_types.py` | `codebase-health` | `aiboost` | Infers and writes missing parameter and return type hints. |
| **Variable Auditor** | `scripts/check_variable_names.py` | `codebase-health` | `aivars` | Flags single-letter and uninformative identifiers (Rule 38). |
| **Typo Checker** | `scripts/spell_checker.py` | `codebase-health` | `aispell` | Audits code identifiers and comments for spelling errors. |
| **Symbol Map** | `scripts/repo_map.py` | `codebase-context` | `airepo` | Generates compact AST symbol and dependency trees. |
| **Directory Tree** | `scripts/dir_overview.py` | `codebase-context` | `aitree` | Token-efficient visual hierarchy with line counts and sizes. |
| **File Slicer** | `scripts/slice_file.py` | `codebase-context` | `aislice` | Views targeted line ranges with line numbers. |
| **Context Packer** | `scripts/pack_context.py` | `codebase-context` | `aicontext` | Bundles files into prompt packages with token counts. |
| **Token Counter** | `scripts/token_budget.py` | `codebase-context` | `aitokens` | Calculates token budgets and per-file token usage. |
| **AST Diff Redactor** | `scripts/redact_diff.py` | `codebase-context` | `aidiff` | Compresses git diffs for LLM prompts, saving 60-80% tokens. |
| **Fast Search** | `scripts/fast_search.py` | `codebase-context` | `aisearch` | Regex search with context lines, caps, and file filters. |
| **Dependency Scanner** | `scripts/check_dependencies.py` | `dependency-guard` | `aideps` | Flags undeclared external imports and hallucinated packages. |
| **Rollback Manager** | `scripts/rollback.py` | `workspace-checkpoint` | `airollback` | Saves workspace snapshots and restores state in one step. |
| **Document Converter** | `scripts/to_markdown.py` | `doc-to-markdown` | `aimd` | Converts PDF, DOCX, XLSX, PPTX, CSV, HTML to clean Markdown. |
| **Encoding Cleaner** | `scripts/clean_encoding.py` | `clean-encoding` | `aitools clean` | Repairs mojibake sequences and character corruption. |
| **Smart Test Runner** | `scripts/smart_test_runner.py` | `smart-test` | `aitest` | Maps git diffs to impacted test suites and executes them. |
| **Secret Scanner** | `scripts/secret_sanitizer.py` | `secret-sanitizer` | `aisec` | Scans code and git diffs for leaked API keys and tokens. |
| **Rule Synchronizer** | `scripts/sync_rules.py` | N/A | `aisync` | Synchronizes instruction files across all installed tools. |
| **Hook Installer** | `scripts/install_antigravity_hooks.py` | N/A | `aihook` | Installs git pre-commit and Antigravity task hooks. |
| **Environment Doctor** | `scripts/doctor.py` | N/A | `aidoctor` | Audits tool configs, MCP registration, and filepaths. |
| **Implicit Requirements** | N/A | `implicit-requirements` | N/A | Infers unstated quality, error handling, and performance checks. |
| **Exhaustive Testing** | N/A | `exhaustive-testing` | N/A | Stateful action crawl, seeded corpus, and property test matrix. |
| **UX Auditor** | N/A | `ux-audit` | N/A | Multi-viewport responsive checks, WCAG AA contrast, and themes. |
| **Definition of Done** | N/A | `definition-of-done` | N/A | Pre-flight verification checklist for clean branches and PRs. |
| **Session Wrap-up** | N/A | `session-wrap-up` | N/A | Records durable knowledge and user preferences into memory files. |

---

## Agent skills

The repository ships 33 modular skills under `skills/` (see [.agents/invocation.md](.agents/invocation.md) for invocation rules):

### User-invoked workflow skills (12)

Invoke these workflows explicitly by name (`disable-model-invocation: true`, `allow_implicit_invocation: false`):

| Skill | Companion files | Purpose |
| :--- | :--- | :--- |
| `ask-aitools` | `PHASE-BOUNDARIES.md` | Route tasks to the right `ai-dev-tools` skill and phase transition. |
| `definition-of-done` | -- | Run pre-flight verification gates, visual PR summary, and Merge Danger rating. |
| `handoff` | -- | Write a redacted, secret-free session handoff file in OS temp storage. |
| `implement` | -- | Execute an approved spec/ticket with checkpoints, TDD cycles, lint, and review. |
| `improve-codebase-architecture` | -- | Run complexity/import hotspot checks, emit HTML Mermaid report, and grill candidates. |
| `session-wrap-up` | -- | Run a 7-lever environment retro (`linter_custom.yaml` / `AGENTS.md`) and commit `memory/`. |
| `setup-ai-dev-tools` | -- | Onboard a repo (`aitools config --init-config`, `GLOSSARY.md`, tracker docs, sync). |
| `to-spec` | -- | Synthesize settled decisions into a structured spec with agreed test seams. |
| `to-tickets` | -- | Break specs into vertical tracer-bullet tickets with `Blocked by` edges. |
| `triage` | `AGENT-BRIEF.md`, `OUT-OF-SCOPE.md` | Classify issues/PRs against `.out-of-scope/` and write durable Agent Briefs. |
| `wait-what` | -- | Re-pitch dense explanations in Simplified Technical English via `GLOSSARY.md`. |
| `wayfinder` | -- | Navigate multi-session epics with a living `wayfinder:map` decision DAG. |

### Model-invoked autonomous skills (21)

Available to both agents and humans when matching situations arise:

| Skill | Companion files | Purpose |
| :--- | :--- | :--- |
| `clean-encoding` | -- | Repair mojibake, double-encoded UTF-8, and stray character corruption. |
| `code-review` | -- | Run parallel Standards (`aitools lint` + Fowler smells) and Spec reviewers on diffs. |
| `codebase-context` | -- | Generate compact symbol maps, slices, packed bundles, and token budgets. |
| `codebase-design` | `DEEPENING.md`, `DESIGN-IT-TWICE.md` | Apply deep-module design vocabulary, seams, and parallel interface sketches. |
| `codebase-health` | -- | Prune dead code, boost type hints, audit identifiers, and check spelling. |
| `dependency-guard` | -- | Detect undeclared external imports and hallucinated package names. |
| `diagnosing-bugs` | -- | Run a 6-phase hypothesis loop with `[DEBUG-...]` probes and regression tests. |
| `doc-to-markdown` | -- | Convert PDF, DOCX, XLSX, PPTX, CSV, HTML, and IPYNB to Markdown. |
| `domain-modeling` | `GLOSSARY-FORMAT.md`, `ADR-FORMAT.md` | Maintain `GLOSSARY.md` (`_Avoid:_` -> `linter_custom.yaml`) and `docs/adr/`. |
| `exhaustive-testing` | -- | Drive interactive handlers, hostile inputs, and model-based invariants. |
| `grill-user` | -- | Walk decision trees in frontier rounds with repo fact-checks and `--async` defaults. |
| `implicit-requirements` | -- | Infer and verify unstated error handling, test, and performance checks. |
| `lint-and-fix` | -- | Run the 91-rule linter (`linter_custom.yaml` Rule 91), UI audits, and safe fixes. |
| `prototype` | -- | Build throwaway single-file HTML logic simulators and multi-variant UI spikes. |
| `research` | -- | Run isolated subagent investigations citing primary code and git history. |
| `secret-sanitizer` | -- | Scan source files and diffs for leaked credentials and API keys. |
| `smart-test` | -- | Map git diffs to affected unit test suites and execute them selectively. |
| `tdd` | `tests.md`, `mocking.md` | Execute vertical red-green-refactor cycles at public seams with minimal mocks. |
| `ux-audit` | -- | Audit UI responsiveness (360px+), WCAG AA contrast, themes, and states. |
| `workspace-checkpoint` | -- | Save workspace snapshot checkpoints and restore state in one step. |
| `writing-for-agents` | `SKILL-MECHANICS.md` | Author concise `AGENTS.md` and `SKILL.md` pointers without context bloat. |

---

## Repository Structure

```
ai-dev-tools/
├── .claude-plugin/ # Native Claude Code, Codex, Copilot CLI, and VS Code plugin manifests
├── bin/            # 27 shell shortcuts (sh and .cmd wrappers)
├── docs/           # Setup manual and linter rule specifications
├── mcp/            # Model Context Protocol server exposing 28 native tools
├── memory/         # Plain Markdown durable preferences, decisions, and repo profiles
├── scripts/        # Core Python linters, analyzers, and utilities
├── skills/         # 33 modular agent skills with SKILL.md runbooks and openai.yaml
├── templates/      # Instruction rules, engineering standards, and MCP templates
└── tests/          # Unit tests covering rules, tools, and behavior layer
```

---

## Testing & Verification

Run the test suite:
```bash
uv run --no-project python -m unittest discover tests
```

Run the strict linter:
```bash
uv run --no-project python scripts/claudemd_linter.py . --level strict
```

---

## Documentation Links

- [docs/USER_GUIDE.md](docs/USER_GUIDE.md): Detailed manual on using each tool to audit, clean, and lint codebases.
- [docs/FAQ.md](docs/FAQ.md): Questions on lint levels, AST rules, and rule suppressions.
- [docs/LINTER_RULES.md](docs/LINTER_RULES.md): Specifications for linter rules (91 rules across AST, UI, custom config, and style), suppression comments, and verification levels.
- [docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md): Step-by-step setup walkthrough across Windows, macOS, and Linux.

## Developer Tools Disclaimer
DEVELOPER TOOLS DISCLAIMER: ai-dev-tools provides automated AST analysis, code inspection, and refactoring scripts. The software is provided AS IS without warranty of any kind. The author assumes no liability for code modifications, data loss, or build errors resulting from automated tool execution.
