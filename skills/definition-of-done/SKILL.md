---
name: definition-of-done
description: Pre-flight verification checklist and PR summary package with merge danger rating before opening a pull request.
---

# Definition of done

Finalize changes, verify quality gates, and prepare a clear pull request package before proposing a merge.

## Trigger

Invoke when all planned tickets or edits are complete and ready for branch verification and PR drafting.

## Verification gates

1. **Automated tests**: Run the test runner (`aitools test` or project test command) and confirm every suite passes with zero skipped or relaxed assertions and explicit failure-mode coverage.
2. **Linter and style**: Run `aitools lint . --level strict` (and confirm `None. Lint clean.`).
3. **Security and dependencies**: Run `aitools secrets --diff` (`secret-sanitizer`) and `aitools deps` (`dependency-guard`).
4. **Documentation links**: Run `ailinks .` to verify zero broken local file paths or heading anchors.
5. **User interface (when applicable)**: Run `aitools ui audit` (`ux-audit`), checking 360px through 1920px viewports, light and dark themes, empty/loading/error states, and accessibility.
6. **Clean diff**: Confirm no `[DEBUG-...]` instrumentation, leftover temporary files, or unrequested documentation files remain.
7. **CI/CD pipeline polling**: After pushing commits or opening a PR, poll the remote CI/CD status (GitHub Actions, GitLab CI). If any job fails, diagnose the failure, fix it locally, verify with tests/linter, and update using `git commit --amend --no-edit` and `git push --force-with-lease` until all remote checks succeed.

## PR summary structure

Prepare the pull request description with these sections:

- **Summary**: Concise overview plus a visual aid when faster to read than prose (ASCII file tree, call graph, or Mermaid diagram tracing what changed).
- **Before and after**: Compact comparison table or command output showing measurable behavioral change.
- **Verification**: Exact commands executed and observed counts (explicitly state anything not verified under a **Not verified** section).
- **Merge danger**: Rate risk across two explicit axes:
  - **Door**: `Two-way` (easily reverted config, UI, or internal helper change) or `One-way` (schema migration, public API/contract break, or irreversible data mutation).
  - **Blast radius**: Low / Medium / High: list affected modules, callers, or deployment targets.
- **Assumptions, risks, and follow-ups**: State assumed defaults, known edge cases, and deferred follow-up items.

## Next step

Run `/session-wrap-up` after PR preparation to capture durable lessons and environment improvements in `memory/`.
