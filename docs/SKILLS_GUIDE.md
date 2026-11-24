# Agent Skills Guide

This document describes the agent skills catalog and execution model in `ai-dev-tools`.

## How Skills Work

Agent skills (`skills/`) are modular procedural runbooks designed for AI coding assistants (such as Google Antigravity, Claude Code, Cursor, Windsurf, Cline, and OpenAI Codex).

Skills are not intended for manual execution by human developers. Instead, the AI assistant automatically detects when a task matches a skill and loads the relevant instructions into context. This progressive disclosure pattern keeps prompt context small during everyday tasks while providing deep domain guidance when complex scenarios arise.

## Skill Types

The repository includes two categories of skills:

1. **Autonomous Skills**: The AI assistant invokes these automatically when matching situations occur (such as diagnosing a bug, checking test impact, refactoring code, or sanitizing secrets).
2. **Workflow Skills**: The AI assistant activates these when the user asks for a structured process (such as turning a discussion into a specification, breaking a spec into tickets, or conducting a session retro).

## Autonomous Skills Catalog

| Skill | Companion Files | Purpose |
|:---|:---|:---|
| `clean-encoding` | None | Repair mojibake, double-encoded UTF-8, and stray character corruption. |
| `code-review` | None | Run parallel standards and specification reviewers on git diffs. |
| `codebase-context` | None | Generate compact symbol maps, slices, packed bundles, and token budgets. |
| `codebase-design` | `DEEPENING.md`, `DESIGN-IT-TWICE.md` | Apply deep-module design vocabulary, seams, and parallel interface sketches. |
| `codebase-health` | None | Prune dead code, boost type hints, audit identifiers, and check spelling. |
| `dependency-guard` | None | Detect undeclared external imports and hallucinated package names. |
| `diagnosing-bugs` | None | Run a 6-phase hypothesis loop with debug probes and regression tests. |
| `doc-to-markdown` | None | Convert PDF, DOCX, XLSX, PPTX, CSV, HTML, and IPYNB to Markdown. |
| `domain-modeling` | `GLOSSARY-FORMAT.md`, `ADR-FORMAT.md` | Maintain canonical glossary terms and architecture decision records. |
| `exhaustive-testing` | None | Drive interactive handlers, hostile inputs, and model-based invariants. |
| `grill-user` | None | Walk decision trees in frontier rounds with repository fact-checks. |
| `implicit-requirements` | None | Infer and verify unstated error handling, test, and performance checks. |
| `lint-and-fix` | None | Run the 112-rule linter, UI audits, and safe auto-fixers. |
| `prototype` | None | Build single-file HTML logic simulators and multi-variant UI spikes. |
| `research` | None | Run isolated subagent investigations citing primary code and git history. |
| `secret-sanitizer` | None | Scan source files and diffs for leaked credentials and API keys. |
| `smart-test` | None | Map git diffs to affected unit test suites and execute them selectively. |
| `tdd` | `tests.md`, `mocking.md` | Execute vertical red-green-refactor cycles at public seams with minimal mocks. |
| `ux-audit` | None | Audit UI responsiveness (360px+), WCAG AA contrast, themes, and states. |
| `workspace-checkpoint` | None | Save workspace snapshot checkpoints and restore state in one step. |
| `writing-for-agents` | `SKILL-MECHANICS.md` | Author concise instruction pointers without context bloat. |

## Workflow Skills Catalog

| Skill | Companion Files | Purpose |
|:---|:---|:---|
| `ask-aitools` | `PHASE-BOUNDARIES.md` | Route tasks to the right skill and manage phase transitions. |
| `definition-of-done` | None | Run pre-flight verification gates, visual PR summary, and risk checks. |
| `handoff` | None | Write a redacted, secret-free session handoff file in OS temp storage. |
| `implement` | None | Execute an approved spec or ticket with checkpoints, TDD cycles, and review. |
| `improve-codebase-architecture` | None | Check complexity and import hotspots, emit Mermaid charts, and review candidates. |
| `session-wrap-up` | None | Run an environment retro and record durable knowledge to memory files. |
| `setup-ai-dev-tools` | None | Onboard a repository with glossary entries, trackers, and rule sync. |
| `to-spec` | None | Synthesize settled decisions into a structured spec with agreed test seams. |
| `to-tickets` | None | Break specs into vertical tracer-bullet tickets with dependency edges. |
| `triage` | `AGENT-BRIEF.md`, `OUT-OF-SCOPE.md` | Classify issues and PRs against scope boundaries and write agent briefs. |
| `wait-what` | None | Clarify dense technical explanations into simplified technical terms. |
| `wayfinder` | None | Navigate multi-session work with a living decision graph. |

## Skill Structure

Each skill lives in its own subdirectory under `skills/<skill-name>/` containing:
- `SKILL.md`: Required instruction file with YAML frontmatter specifying `name` and `description`, followed by step-by-step procedures.
- Companion files (optional): Supplemental reference patterns, formats, or checklists.

## Verification

Skill validity is checked automatically by the unit test suite:

```bash
uv run --no-project python -m unittest tests/test_behavior_layer.py
```

The test suite verifies that every skill has valid YAML frontmatter and that its declared name matches its directory.


---

## Related Documentation

- [Project Overview](../README.md)
- [Rule Files Reference](RULE_FILES.md)
- [Developer Guide](DEVELOPMENT.md)
- [112 Linter Rules Reference](LINTER_RULES.md)
- [Security Policy](../SECURITY.md)
