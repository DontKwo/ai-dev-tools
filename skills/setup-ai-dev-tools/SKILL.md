---
name: setup-ai-dev-tools
disable-model-invocation: true
description: Interactive repository onboarding wizard for configuring linter_custom.yaml, GLOSSARY.md, issue tracker docs, and multi-editor sync.
---

# Set up ai-dev-tools in a repository

Bootstrap a target project cleanly with portable custom linter rules, domain docs, issue tracker conventions, and synchronized editor skills.

## Interactive onboarding steps

1. **Inspect existing setup**: Run read-only checks to discover git remotes, existing `.aitools.toml`, `linter_custom.yaml`, `GLOSSARY.md`, `docs/adr/`, and installed editor folders:
   ```bash
   aitools doctor
   ```
2. **Initialize config templates**: If `.aitools.toml` or `linter_custom.yaml` is absent, generate starter configurations cleanly:
   ```bash
   aitools config --init-config
   ```
3. **Configure project custom linter rules (`linter_custom.yaml`)**: Offer via `grill-user` to populate project-specific `remove`, `replace`, `allowed_vars` (engineering/domain symbols), and `ignore_paths`.
4. **Configure optional agent conventions**:
   - Offer to create root `GLOSSARY.md` (`domain-modeling`) when domain terms need canonical definitions.
   - Ask which issue tracker (`GitHub Issues`, `GitLab Issues`, or local `.scratch/<feature>/issues/`) and triage labels (`triage`) the team uses, recording short pointers in `docs/agents/issue-tracker.md` and `docs/agents/triage-labels.md` only when approved.
5. **Sync instructions and skills across editors**:
   ```bash
   aitools sync
   aitools skills sync --scope workspace
   ```
6. **Verify end-to-end health**:
   ```bash
   aitools lint . --level strict
   aitools doctor
   ```
