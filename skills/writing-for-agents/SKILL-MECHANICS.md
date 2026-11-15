# Skill mechanics and invocation modes

Every skill lives in a flat subdirectory `skills/<kebab-case-name>/SKILL.md`, paired with `agents/openai.yaml` and optional focused companion Markdown files.

## YAML frontmatter fields

```yaml
---
name: my-skill-name
disable-model-invocation: true # Omit for model-invoked skills
description: >-
  One crisp sentence for user-invoked skills, or capability + explicit triggers
  ("Use when...") for model-invoked skills.
---
```

## Choosing user-invoked vs model-invoked

| Mode | Frontmatter (`SKILL.md`) | Codex policy (`agents/openai.yaml`) | Description style |
| :--- | :--- | :--- | :--- |
| User-invoked workflow | Set `disable-model-invocation: true` | `allow_implicit_invocation: false` | Concise one-line menu summary |
| Model-invoked capability | Omit `disable-model-invocation` | Omit `policy` block | Include capability plus `"Use when..."` triggers |

Keep both files synchronized so Claude Code, Antigravity, Cursor, and Codex enforce identical reachability rules.

## Progressive disclosure layout

Keep `SKILL.md` focused on the core procedure (under 80 to 120 lines where practical) and split heavy checklists, reference tables, or templates into companion files in the same skill folder (`REFERENCE.md`, `FORMAT.md`).
