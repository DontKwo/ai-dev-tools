# Glossary

Canonical terminology for `ai-dev-tools`, covering its static linter, multi-editor tooling sync, and agent workflow skills.

## Terms

**Rule**:
A numbered check (1 through 91) enforced by `scripts/claudemd_linter.py`, spanning anti-AI prose guards, Python AST safety, engineering discipline, multi-framework UI quality, and custom user rules.
_Avoid:_ Guardrail check, lint item

**Verification level**:
One of three named linter rule presets (`standard`, `strict`, `full`) applied across the active scan scope (`--diff`, `--staged`, or `--full`).
_Avoid:_ Lint tier, severity mode

**Custom linter config**:
A repository or user `linter_custom.yaml` file (templated from `linter_custom.example.yaml`) defining local `remove`, `replace`, `allowed_vars`, `banned_vars`, `banned_imports`, and `file_guards` enforced under Rule 91.
_Avoid:_ Custom blacklist, personal YAML

**Seam**:
An explicit public boundary (CLI entrypoint, exported function, API route, or UI interaction) where modules meet and where `tdd` behavioral tests attach.
_Avoid:_ Intercept point, boundary hook

**Tracer bullet**:
One thin vertical slice through all required layers, complete with an observable red-green test at the seam, shipped end-to-end before widening scope.
_Avoid:_ Horizontal layer, skeleton stub

**User-invoked skill**:
A workflow skill marked `disable-model-invocation: true` in `SKILL.md` and `allow_implicit_invocation: false` in `agents/openai.yaml` that runs when invoked by name (for example `/implement`).
_Avoid:_ Manual command, slash macro

**Model-invoked skill**:
An autonomous capability skill without `disable-model-invocation` whose `description` guides both the model and human users on when to trigger it.
_Avoid:_ Auto skill, background prompt

**Frontier round**:
A breadth-first `grill-user` batch of one to four independent open design questions at the current decision tree frontier, each paired with a concrete recommended default.
_Avoid:_ Random interview, waterfall Q&A

**Merge danger**:
A two-axis pre-merge risk rating pairing **Door** (`Two-way` reversible change vs `One-way` irreversible migration or contract change) with **Blast radius** (affected modules and call volume).
_Avoid:_ Risk score, PR threat level

**Agent brief**:
A triaged `ready-for-agent` ticket written purely in behavioral terms (expected behavior, observed failure, scope bounds, test seam) with zero volatile line numbers.
_Avoid:_ Code patch prompt, task blurb

**Out-of-scope rule**:
A concise boundary note stored under `.out-of-scope/` documenting what a project intentionally excludes so future triage closes recurring drift quickly.
_Avoid:_ Wontfix FAQ, reject list
