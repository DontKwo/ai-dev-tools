---
name: implement
disable-model-invocation: true
description: Execute an approved spec or ticket end-to-end with checkpoints, TDD cycles, strict linting, and dual-axis review.
---

# Implement spec or ticket

Drive an approved specification or ordered ticket list to merge-ready code cleanly and deterministically.

## Execution sequence

1. **Pre-flight inspection**: Read the spec/ticket, target files, and `GLOSSARY.md` if present. Save a workspace safety snapshot when making multi-file edits:
   ```bash
   aitools checkpoint save "pre-implement"
   ```
2. **Parallelize independent tickets (optional)**: When a spec defines multiple independent tickets with zero `Blocked by` overlap, isolate each branch or use parallel worktrees (`git worktree`) per ticket; otherwise work sequentially along the dependency DAG in one branch.
3. **Vertical TDD loop**: Implement each behavioral slice using [tdd](../tdd/SKILL.md) (red test at public seam -> minimal green implementation -> refactor). Run tests frequently via `aitools test`.
4. **Domain and design check**: Keep interfaces deep (see `codebase-design`) and update `GLOSSARY.md` / `docs/adr/` if structural choices lock in.
5. **Static and runtime verification**:
   ```bash
   aitools lint . --level strict
   aitools secrets --diff
   aitools deps
   ```
6. **Code review**: Run [code-review](../code-review/SKILL.md) against `git diff main...HEAD` and resolve every **Blocker** before finishing.
7. **Hand off to finish**: Recommend running `/definition-of-done` before opening the pull request.
