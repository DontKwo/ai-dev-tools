# Memory Protocol

This repository is public. Everything in this directory (`memory/`) is public. Never store secrets, tokens, credentials, or sensitive personal data here.

## Entry Protocol

- Format: Plain Markdown list.
- Line schema: `- YYYY-MM-DD: <text>` (single fact or rule per line).
- Ordering: Newest entries first.
- Maintenance: Stale or contradicted entries are removed or marked superseded.
- Lifecycle: Read relevant memory files at session start; propose memory updates at session end through `session-wrap-up`.
- Scope: `AGENTS.md` remains canonical for style and tone rules; memory files must not duplicate it.

## Repository Files

- `memory/preferences.md`: User tastes, interaction preferences, and working conventions.
- `memory/user-profile.md`: Persistent user profile facts and general technical interests.
- `memory/lessons-learned.md`: Solutions to mistakes, unexpected pitfalls, and tool bugs.
- `memory/decisions.md`: Architectural decisions and systemic designs.
- `memory/projects/<repo>.md`: Specific project context, repository architecture, and commands.
