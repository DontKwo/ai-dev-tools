---
name: definition-of-done
description: >-
  Pre-flight verification checklist required before finalizing work and opening a pull request. Use to ensure test coverage, documentation, accessibility, and clean diagnostics.
---

# Definition of Done

Finalize changes and verify quality standards before proposing code merges.

## Trigger

Execute as the final validation phase before opening a pull request.

## Checklist

1. **Build & Diagnostics**
   - Project builds cleanly without warnings or errors.
   - Codebase passes strict AST and style linting (`scripts/claudemd_linter.py`).
   - Static type checks pass without unaccounted suppressions.

2. **Automated Testing**
   - All unit, integration, and regression test suites pass.
   - Failure modes (empty inputs, boundaries, errors) have active test coverage.
   - No tests disabled, weakened, or skipped to achieve passing status.

3. **User Interface (When Applicable)**
   - Views verified across mobile (360px) through desktop (1920px) viewports.
   - Both light and dark color schemes validated for readability and token consistency.
   - Loading skeletons, empty state placeholders, and error messages functional.
   - Zero console errors, unhandled promise rejections, or accessibility violations.

4. **Documentation & Memory**
   - Existing documentation (`README.md`, setup guides) updated for behavioral changes.
   - No unsolicited documentation files introduced.
   - Memory updates proposed through `session-wrap-up` protocol.

5. **Pull Request Preparation**
   - Git commit history organized into small, logical changes.
   - PR description populated with required sections: Summary, Assumptions, How verified, Not verified, Risks, Follow-ups.
