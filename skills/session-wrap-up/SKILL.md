---
name: session-wrap-up
description: Run a 7-lever environment retrospective and consolidate durable memory updates as a separate commit.
---

# Session wrap-up

Convert session friction into permanent tooling guardrails and record durable knowledge in repository memory.

## Part 1: Seven-lever environment retrospective

Review every surprise, retry, wrong turn, or correction from the session and trace each back to a permanent fix across seven levers:

| Lever | Question to ask | Concrete artifact to update |
| :--- | :--- | :--- |
| 1. Navigation | Did the agent search aimlessly or read wrong files? | Add entry pointers to `AGENTS.md` or update `GLOSSARY.md` |
| 2. Automated checks | Did a mechanical mistake repeat across edits? | Add a rule in `linter_custom.yaml` or git hook (`aihook`) |
| 3. Coding standards | Was a style or naming rule violated repeatedly? | Add banned terms or `banned_vars` to `linter_custom.yaml` |
| 4. Global instructions | Were repo-wide conventions unclear or missing? | Update `AGENTS.md` (keep within line budget) |
| 5. Tool economy | Did verbose bash loops waste tokens? | Prefer `aitools` commands (`airepo`, `aitest`, `aisearch`) |
| 6. No-op rules | Were any instructions ignored, stale, or redundant? | Prune dead rules via [writing-for-agents](../writing-for-agents/SKILL.md) |
| 7. Information access | Was required doc/test/runtime evidence unreachable? | Document the command in repo docs or MCP config |

Apply immediate zero-risk config fixes, or propose larger architectural changes with `grill-user` before modifying shared instructions.

## Part 2: Memory consolidation

Identify durable knowledge from the session:

- `memory/preferences.md`: User workflow tastes and communication expectations.
- `memory/user-profile.md`: Persistent operating context.
- `memory/decisions.md`: System design choices and rationale.
- `memory/lessons-learned.md`: Verified solutions to tricky pitfalls.
- `memory/projects/<repo>.md`: Repository-specific stack and layout facts.

Check every memory entry against constraints:

- Plain Markdown line format: `- YYYY-MM-DD: <text>`.
- Place newest entries first; delete or supersede stale entries.
- Store zero secrets, tokens, private paths, or personal names.
- Avoid duplicating canonical rules already defined in `AGENTS.md`.
- Commit memory updates in a distinct commit separate from feature edits.
