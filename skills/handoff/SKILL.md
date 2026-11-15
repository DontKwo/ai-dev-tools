---
name: handoff
disable-model-invocation: true
description: Package current goal, locked decisions, open questions, and clean file pointers into a portable redacted handoff Markdown file.
---

# Portable session handoff

Save clean, self-contained session state into a timestamped Markdown file in the OS temporary directory so a fresh session (or teammate) picks up immediately after `/clear` or tool switching.

## Procedure

1. Gather essential context only:
   - Active goal and branch (`git branch --show-current`).
   - Locked decisions and rejected options (so the next session avoids repeating resolved debates).
   - Open questions or failing verification commands with exact observed errors.
   - Exact file paths and symbol names inspected directly.
2. Run a secret hygiene pass before writing: verify zero API keys, tokens, credentials, personal paths, or internal hostnames appear (`aitools secrets` semantics).
3. Write the file to `<os_temp_dir>/handoff-<YYYYMMDD-HHMM>-<slug>.md` (use Python `tempfile.gettempdir()` cleanly) with this structure:

```md
# Handoff: <Short topic>

## Goal
## Locked decisions
## Current state and failing checks
## Open questions
## File pointers
## Suggested next skill
```

4. Print the absolute path to the generated handoff file and recommend which skill (`/implement`, `/to-spec`, `diagnosing-bugs`, or `grill-user`) to invoke next.
