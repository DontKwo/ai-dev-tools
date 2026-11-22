# YAML Configuration Guide

The `config.yaml` file defines all declarative settings for AI assistant rules, skill bundles, Model Context Protocol servers, and git hooks.

Power users can edit this file directly in any text editor, then run `python scripts/apply_config.py` to apply settings.

---

## Complete Schema Reference

```yaml
# Configuration schema version (always 1)
version: 1

# Installation scope: 'workspace' (current directory) or 'global' (user home directory)
scope: workspace

# File modification strategy:
# - 'append': Preserves existing custom content; inserts or updates bounded AI-DEV-TOOLS block.
# - 'overwrite': Replaces entire file; automatically saves backup to <filename>.bak.
# - 'skip': Leaves existing files untouched; only creates missing target files.
write_mode: append

# Active AI assistants (true = configure, false = skip)
tools:
  claude: true
  cursor: true
  cline: true
  antigravity: true
  codex: true
  windsurf: true
  copilot: true
  aider: true

# Rule Strictness Profile
profile:
  # Profile level: 'full', 'strict', 'standard', 'safe', or 'minimal'
  level: strict
  # Specific numeric linter rule codes to skip (optional override)
  skip_rules: []
  description: "Full functionality and strict linting."

# Individual instruction file targets
targets:
  claude_md: true
  agents_md: true
  cursorrules: true
  clinerules: true
  windsurfrules: true
  aider_conventions: true
  copilot_instructions: true

# Model Context Protocol (MCP) server configuration
mcp:
  enabled: true
  server_name: ai-dev-tools

# Agent Skills configuration
skills:
  enabled: true
  # Selected bundle: 'all', 'core', 'architecture', 'context', 'workflow', or 'none'
  bundle: all
  custom_skills: []

# Git Hooks configuration
hooks:
  git_pre_commit: true
  command: "uv run --no-project python scripts/claudemd_linter.py . --diff"
```

---

## Key Explanations

### `scope`
- `workspace`: Places files directly in the target repository (for example, `./CLAUDE.md`, `./.cursorrules`).
- `global`: Places files in your operating system user home directory (for example, `~/.claude/CLAUDE.md`, `~/.cursorrules`).

### `write_mode`
- `append` (Default): Safe mode. Searches for existing markers `<!-- BEGIN AI-DEV-TOOLS -->` and `<!-- END AI-DEV-TOOLS -->`. Any personal instructions outside these markers remain intact.
- `overwrite`: Clean slate. Writes the complete instructions file. If an existing file is present, a copy is saved with extension `.bak` to guarantee zero unrecoverable data loss.
- `skip`: Preserves existing files. Only writes target files if they do not yet exist.

### `profile`
Controls which coding standards and linter checks are enforced:
- `full` / `strict`: All 91 rules active. Strict AST validation, type annotations, dead code elimination, and writing hygiene.
- `standard`: Balanced profile. Core AST safety, dependency guards, and secret checks with relaxed prose and comment rules.
- `safe`: Recommended for existing repositories. Bug prevention, package validation, and secret sanitization with zero stylistic churn.
- `minimal`: Minimalist safety profile.

### `skills.bundle`
- `all`: Installs all 20+ specialized skills.
- `core`: Installs testing, linting, debugging, and bug diagnostic skills.
- `architecture`: Installs codebase context, design, and domain modeling skills.
- `context`: Installs token compression, file slicing, and context packing skills.
- `workflow`: Installs TDD, code review, and secret sanitization skills.

### `hooks.git_pre_commit`
When set to `true`, writes a Git pre-commit hook into `.git/hooks/pre-commit`. The hook runs the linter across staged changes before every commit.

---

## Applying the Configuration

Apply changes from the terminal:
```bash
python scripts/apply_config.py --config config.yaml
```

Preview changes and inspect data loss warnings before writing:
```bash
python scripts/apply_config.py --config config.yaml --dry-run
```


---

## Related Documentation

- [Project Overview](../../README.md)
- [CLI Reference](cli-reference.md)
- [Rule Profiles Reference](profiles.md)
- [Developer Guide](../DEVELOPMENT.md)
- [Security Policy](../../SECURITY.md)
