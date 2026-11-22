# AI-Dev-Tools Documentation Hub

Central documentation repository for users, power users, and developers.

---

## 1. Everyday Users

Simple, zero-code, graphical setup:

- [Everyday User Quickstart](user/quickstart.md) - 3-step setup via standalone application.
- [User Guide](USER_GUIDE.md) - Overview of AI assistants, rules, and benefits.
- [Frequently Asked Questions](FAQ.md) - Common questions, safety guarantees, and troubleshooting.

---

## 2. Power Users & Automation

Declarative configuration, command-line flags, and custom profiles:

- [YAML Configuration Guide](power-users/yaml-guide.md) - Complete key-by-key schema documentation for `config.yaml`.
- [CLI Reference](power-users/cli-reference.md) - Flags, commands (`adt lint`, `adt fix`, `adt test`), and dry-run previews.
- [Rule Strictness Profiles](power-users/profiles.md) - Detailed comparison of `strict`, `standard`, `safe`, and `minimal` profiles.

---

## 3. Developers & Contributors

Internal architecture, execution pipeline, and extending the tool suite:

- [Architecture Manual](developer/architecture.md) - Execution engine, safety guarantees, atomic writes, and state manifests.
- [Extending AI-Dev-Tools](developer/extending.md) - Adding AI assistants, custom skills, and custom rules.
- [Developer Manual](DEV_MANUAL.md) - API reference for internal scripts and modules.

---

## 4. Technical References

Detailed rules catalogs and skill references:

- [91 Linter Rules Reference](LINTER_RULES.md) - Comprehensive catalog of AST safety, security, and quality rules.
- [Skills Catalog Guide](SKILLS_GUIDE.md) - Autonomous agent skills reference (`.agent/skills/`, `.claude/skills/`).
- [Rule Files Reference](RULE_FILES.md) - Formats and locations for assistant instruction files.
- [UI Quality Rules](UI_RULES.md) - Visual and UX standards for frontend development.


---

## Related Documentation

- [Project Overview](../README.md)
- [Desktop Installation Guide](INSTALLATION.md)
- [Developer Guide](DEVELOPMENT.md)
- [Security Policy](../SECURITY.md)
- [MIT License](../LICENSE)
