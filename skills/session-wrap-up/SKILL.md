---
name: session-wrap-up
description: >-
  Consolidate lessons learned, user preferences, and architectural decisions into repository memory files at the conclusion of a session. Use when finalizing work before pull request creation.
---

# Session Wrap-up

Record durable knowledge and user preferences into repository memory before completing work.

## Trigger

Execute at the conclusion of every coding session immediately before opening a pull request.

## Procedure

1. Review session activity to identify:
   - User preferences regarding style, workflow, or tools.
   - Architectural and design decisions agreed upon.
   - Project-specific facts, configurations, or conventions discovered.
   - Post-mortem lessons learned from errors or test failures.
2. Verify target file paths:
   - `memory/preferences.md`: User tastes and workflow expectations.
   - `memory/user-profile.md`: Persistent user background and operating context.
   - `memory/decisions.md`: High-level system design and architectural choices.
   - `memory/lessons-learned.md`: Solutions to pitfalls or tricky edge cases.
   - `memory/projects/<repo>.md`: Specific repository architecture and stack facts.
3. Check entries against constraints:
   - Plain Markdown format.
   - Entry line format: `- YYYY-MM-DD: <text>`.
   - Newest entries placed first.
   - Stale or contradicted entries deleted or marked superseded.
   - Never store secrets, tokens, or private credentials.
   - Never duplicate style or tone rules from `AGENTS.md`.
4. Create memory updates as a distinct, dedicated git commit.
5. If `scripts/agent_memory.py` is present in the repository, invoke it to manage updates; otherwise edit the markdown files directly.
