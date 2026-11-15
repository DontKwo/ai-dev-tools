---
name: research
description: >-
  Dispatch a fresh-context research investigation against primary source files,
  git history, or documentation and return concise cited findings. Use when an
  open question needs deep file reading or log inspection without filling the
  main conversation window.
---

# Fresh-context research

Investigate technical questions against primary evidence in an isolated subagent so exploratory logs never crowd active implementation context.

## Workflow

1. **Frame one crisp question**: Specify what must be answered, which entry points or search tools (`aitools search`, `aitools repo-map`, `aitools imports`) apply, and what output shape is required.
2. **Read primary sources only**: Inspect actual source code, tests, git commit history (`git log`, `git blame`), and installed docs. Cite exact `file:line` pointers or verbatim command output.
3. **Return structured synthesis**:
   - **Direct answer**: Two to four sentences resolving the question.
   - **Primary evidence**: Exact symbol names, config keys, and `file:line` references observed directly.
   - **Gaps / unverified**: Anything absent or ambiguous in checked files.
