---
name: writing-for-agents
description: >-
  Author concise, high-signal AGENTS.md instructions, SKILL.md workflows, and
  repo pointer docs without wasting context tokens or adding ignored no-op
  rules. Use when creating or editing skills, AGENTS.md, or agent manuals.
---

# Writing for coding agents

Keep every token in agent instructions high-signal, scannable, and cheap to maintain as the codebase changes.

Read [SKILL-MECHANICS.md](SKILL-MECHANICS.md) when designing skill YAML frontmatter, invocation modes (`disable-model-invocation`), or folder layouts.

## Core authoring principles

- **Pointers over copies**: Point to canonical files (`See docs/DEV_MANUAL.md`) instead of duplicating long manuals into `AGENTS.md`.
- **Leading action words**: Start bullet rules with strong imperative verbs (`Run`, `Check`, `Avoid`, `Pin`) so models scan priorities fast.
- **Positive framing**: State what the agent should do (`Use ast.parse to inspect Python functions`) instead of vague prohibitions alone.
- **Line-budget hierarchy**: Reserve `AGENTS.md` (at most 120 lines) for universal repo invariants; push step-by-step domain workflows into on-demand `SKILL.md` files.
- **Prune no-op rules**: Delete instructions that duplicate obvious defaults or that repeated reviews ignore in favor of deterministic hooks or `linter_custom.yaml` checks.
- **Style linter compliance**: Ensure Markdown files pass `aitools lint . --level strict` with zero em dashes, zero curly quotes/emojis, and clean sentence-case headings starting at `# H1`.
