# Style & Tone
- Be terse. No preamble, conversational filler ("certainly!", "here is the code", "hope this helps"), or apologies.
- Avoid AI writing patterns: no em dashes (rewrite sentences cleanly), no negative parallelisms (`"not just X, but Y"`), no copulative avoidance (`"serves as"`, `"stands as"`), no hype/fluff vocabulary (`"pivotal"`, `"delve"`, `"testament"`, `"tapestry"`, `"robust"`, `"boasts"`, `"seamlessly"`), and no internal citation metadata (`oaicite`, `[cite: ...]`, `【...】`).
- Write only for current behavior. Never add compatibility `shims`, `legacy` branches, or `deprecated` functions unless explicitly requested.
- Every function signature must have explicit parameter and return type annotations.
- Keep comments <= 2 lines. State only what code does now. Use `# long-comment-ok` only when multi-line explanation is strictly necessary (such as complex algorithms or mathematical derivations).

# Proactive Architectural Overhauls
- If code becomes unsustainable, propose a modular overhaul (decomposing monolithic files > 400 lines, deduplicating logic, untangling dependencies).
- Formulate the proposal via `grill-user` with target architecture and execute in verifiable steps using `workspace-checkpoint` and `tdd` upon approval.

# Autonomous Skill Selection & Execution
- Never require user invocation of skills; casual prompts receive full power-user rigor.
- Automatically activate appropriate skills: `grill-user`/`domain-modeling` (ambiguity), `tdd`/`smart-test`/`diagnosing-bugs` (features/fixes), `prototype`/`react-astryx`/`ux-audit` (UI), `workspace-checkpoint`/`codebase-design` (refactoring), `lint-and-fix`/`definition-of-done` (verification).

# Frontend UI Design
- When building frontends from scratch, evaluate React. If chosen, use Meta Astryx templates for WCAG AA components and theme tokens; write custom CSS only for domain styling.

# Python Execution
- Run Python commands through uv: `uv run --no-project --python "<venv_python>" <command>`.
- Always pass `--no-project` to prevent uv from initializing new projects or auto-creating virtual environments.
- Reuse an existing virtual environment as close as possible to the run root. Locate `<venv_python>` using this search precedence:
  1. Search upward from the command run root (working directory) toward the project root and filesystem root for `.venv` or `venv`.
     - Windows: `<found_venv>\Scripts\python.exe`
     - Linux/macOS: `<found_venv>/bin/python`
  2. If upward directory search finds no virtual environment, check the active `VIRTUAL_ENV` or `CONDA_PREFIX` environment variables.
  3. Check `.vscode/settings.json` for `python.defaultInterpreterPath` if present.
  4. If no virtual environment exists anywhere in the directory hierarchy, do not create one. Halt and ask the user for the target Python interpreter path (or permission to use host Python). Never initialize a new environment (`uv venv`, `uv sync`, bare `uv run`, `python -m venv`, `virtualenv`, `conda`).
- Always wrap `<venv_python>` in double quotes to handle paths with spaces.
- If `uv` is unavailable on PATH, fall back to executing `"<venv_python>" <command>` directly.
- Formulate commands explicitly:
  - Scripts: `uv run --no-project --python "<venv_python>" <script_path> [args]`
  - Modules & test runners: `uv run --no-project --python "<venv_python>" python -m <module> [args]` (e.g. `-m pytest`, `-m unittest`)
  - Inline expressions: `uv run --no-project --python "<venv_python>" python -c "<code>"`
- Never install packages into the environment without explicit user approval.
- Repository tools from `ai-dev-tools` may execute with the host runner (`uv run --no-project python <script>`) when the target project virtual environment lacks tool dependencies.
- See %USERPROFILE%\projects\ai-dev-tools\templates\PYTHON_RULES.md for additional environment context.

# Proactive Quality
- Treat short prompts as full tasks held to full engineering standards.
- Infer unstated requirements (tests, UX, error handling, performance) and apply them via the `implicit-requirements` skill.
- Find problems yourself by reading code, running the program, and exercising the UI as a user.
- Fix root causes, not symptoms.
- Fix small related defects in the same change and list larger ones as follow-ups.
- Never stop at the literal task if related defects of the same kind are obvious.

# Testing Standard
- Always create and maintain comprehensive automated tests for every module, function, and UI control in the repository.
- List failure modes and cover each with a test or state the mitigation before declaring done.
- Prefer generated tests (table-driven, property-based, model-based random sequences) to hand-written happy paths.
- For user-facing apps, test every UI action against every supported kind of data.
- Never weaken a test to make it pass, and never delete existing tests.
- Report exactly what ran and what did not run via the `exhaustive-testing` skill.

# UI/UX Standard
- Keep existing visual identity unless told otherwise; verify responsiveness from 360px phones to large desktops.
- Fast and measured performance; meet WCAG AA contrast (minimum 4.5:1), 44px touch targets, and full keyboard use.
- Include empty, loading, and error states on every screen with specific friendly error messages.
- Provide confirm or undo for destructive actions.
- Use colors from theme tokens only; check both light and dark themes.
- Prevent unreadable text, tiny inputs, or default browser highlight artifacts (see `ux-audit` skill).

# Interaction
- Ask when the answer materially changes outcome, cannot be found in repo or memory, and is costly to reverse.
- When asking, run `grill-user` in frontier rounds (each question with a recommended answer and 2 or 3 options).
- Otherwise act and state assumptions clearly.
- Background and cloud agents without live conversation put questions with recommended defaults in the plan, ask only blocking ones, and list assumptions in the PR.

# Memory
- Read `memory/preferences.md`, `memory/user-profile.md`, and matching `memory/projects/<repo>.md` at session start if present.
- Run `session-wrap-up` at session end to propose updates as a separate commit when memory files are present.
- Never store secrets or sensitive personal data; memory files are public.
- `AGENTS.md` remains canonical for style rules; memory must not duplicate it.

# Cloud Agents
- When the global ai-dev-tools repository path is absent in a cloud VM or secondary machine, use repo-relative paths (e.g. `scripts/claudemd_linter.py`) and host runner `uv run --no-project python <script>`.
- Finish every session on a new branch with a pull request into main; never push directly to main.
- PR body must contain: Summary, Assumptions, How verified, Not verified, Risks, Follow-ups.
- Local workstation behavior remains exactly as specified today.

# Git Discipline & CI/CD Repair
- Use `git commit --amend --no-edit` and `git push --force-with-lease` for fixes and refinements; new commits are for new features or bug fixes.
- When pushing to remote repositories, poll CI/CD status. If jobs fail, diagnose, fix locally, verify with tests/linter, and update using `--amend` and `--force-with-lease` until green.
- Auto-scaffold standard CI/CD workflows in new repos; suggest CI/CD in existing repos without forcing.

# After Changes
- Reply with a brief list: what changed + confirmation it was tested (or state explicitly that it was not tested).
  Example: "Fixed off-by-one in parser. Added retry logic. All 27 unit tests passing."
- For cloud agent PR bodies, provide sections: Summary, Assumptions, How verified, Not verified, Risks, Follow-ups.

# Documentation
- Never create unsolicited .md documentation files (no unrequested READMEs, architecture summaries, or guides). Deliverables explicitly requested by the user are permitted. Internal agent artifacts and scratchpads are permitted. Editing existing documentation when modifying features is permitted.
- Check project documentation (e.g. docs/) for tool manuals, CLI flags, and APIs when available.

# Domain Rules
- For engineering, numerical, or thermodynamic tasks, follow %USERPROFILE%\projects\ai-dev-tools\templates\ENGINEERING_RULES.md if present. Domain equations adhering to these rules are exempt from single-letter variable checks (Rule 38).

# Linter (Mandatory)
- After every code change, run the linter:
  uv run --no-project python %USERPROFILE%\projects\ai-dev-tools\scripts\claudemd_linter.py . --level strict
- In git repositories with existing history, the linter runs with `--diff` by default so only changed files get linted. Run with `--full` only when the user explicitly requests a full repository audit.
- Verification levels (distinct from the `--full` scan scope):
  - `--level standard`: Anti-AI writing guards, core AST safety, equation formatting.
  - `--level strict` (Default): Adds term decomposition, banner removal, unit annotations, descriptive naming.
  - `--level full`: Strict type hints, zero prints, dead code removal, Qt GUI rules. Run only when requested by the user.
  - Fine-grained overrides: `--skip <codes>` or `--only <codes>` for targeted checks.
- When violations occur, inspect the report file path printed in terminal output. Fix every violation and re-run until the output reads "None. Lint clean." (the report file is deleted automatically once clean).
- `# noqa` / `# noqa: <codes>` suppresses checks; use only when code is genuinely correct as-is. For third-party, vendor, or generated code where modifications would break functionality, add targeted inline `# noqa: <code>` comments.

# Linter Security & Integrity
- AI agents are strictly forbidden from reading, inspecting, or editing `scripts/claudemd_linter.py`, `scripts/custom_linter.py`, or tampering with lint reports and cache files.
- The only exception is if the user explicitly instructs the AI to view or modify the linter script.
- Treat the linter as an external black-box verifier: run the command, read the output codes and line numbers, consult `docs/LINTER_RULES.md` for rule descriptions if needed, and fix the underlying code to satisfy the linter without attempting to weaken, circumvent, or suppress checks.

# Repository Structure & Release Standard (Rules 101-112)
- Keep `README.md` user-focused (`<= 120` lines): `assets/logo.png`, `## Download` table (one asset per OS), `## Screenshots` (real images), `## How to Use`, `## Safety & Disclaimers` (`main`-only fork warning, bypass discretion, AS-IS), and bottom `## Documentation` (User -> Developer -> AI/Technical -> Legal). Never put checksums, CI/CD details, `git clone`, or test/build commands in `README.md`.
- Keep all repos on `MIT License` (`Copyright (c) 2026 DontKwo`), canonical `SECURITY.md`, `THIRD_PARTY_NOTICES.md`, clickable links everywhere, circular `## Related Documentation` footers linking to `../README.md`, per-platform `### Windows` / `### macOS` / `### Linux` headings, dual branding (`logo.png` vs cropped `icon.png`/`.ico`), single `.github/workflows/ci.yml`, and WebView GUIs with `--self-test`.
