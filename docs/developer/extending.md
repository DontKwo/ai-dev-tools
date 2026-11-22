# Extending AI-Dev-Tools

Instructions for developers adding new AI tool integrations, custom skill packages, or custom linter checks.

---

## 1. Adding a New AI Assistant

To add support for a new AI assistant:

1. Open `scripts/configure.py`.
2. Locate `get_tool_definitions()`.
3. Add a new dictionary entry defining paths and optional frontmatter:
   ```python
   "my_tool": {
       "name": "My Assistant",
       "global_paths": [home / ".mytool" / "rules.md"],
       "workspace_paths": [ws / ".mytool" / "rules.md"],
       "frontmatter": "",
   }
   ```
4. Update `config.yaml` to include `"my_tool": true` under `tools:`.
5. Update `SetupGuiModel` in `scripts/setup_gui.py` to add the tool to GUI presets.

---

## 2. Adding a New AI Skill

1. Create a new directory in `skills/<skill-name>/`.
2. Add a `SKILL.md` file with standard YAML frontmatter:
   ```yaml
   ---
   name: my-skill
   description: Brief explanation of what this skill does.
   ---
   ```
3. Add supporting scripts in `skills/<skill-name>/scripts/` if required.
4. Add the skill name to the appropriate bundle list in `SKILL_BUNDLES` inside `scripts/configure.py`.

---

## 3. Defining Custom Linter Rules

Create or edit `linter_custom.yaml` in your project root:
```yaml
rules:
  - id: custom_banned_term
    pattern: "TODO_URGENT"
    message: "Resolve urgent TODOs before committing."
    level: strict
```
Run verification:
```bash
uv run --no-project python scripts/claudemd_linter.py . --level strict
```


---

## Related Documentation

- [Project Overview](../../README.md)
- [System Architecture](../ARCHITECTURE.md)
- [Developer Guide](../DEVELOPMENT.md)
- [CLI Reference](../power-users/cli-reference.md)
- [Security Policy](../../SECURITY.md)
