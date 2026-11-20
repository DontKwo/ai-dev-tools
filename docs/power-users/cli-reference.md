# CLI Reference for scripts/apply_config.py

The `scripts/apply_config.py` script applies declarative YAML configurations to your project or home directory.

## Synopsis

```bash
python scripts/apply_config.py [OPTIONS]
```

Or via the unified CLI:
```bash
adt apply [OPTIONS]
```

---

## Options

### Configuration & Path Options
- `--config <path>`, `-c <path>`: Path to YAML configuration file. Defaults to `config.yaml` in the repository root.
- `--workspace <path>`, `-w <path>`: Target workspace directory. Defaults to the current working directory.

### Execution Control
- `--dry-run`, `-d`: Calculates and outputs the full configuration plan without writing files to disk.
- `--yes`, `-y`: Bypasses the confirmation prompt and applies changes immediately.
- `--json`: Outputs the complete execution plan and data-loss checks as JSON for integration with tools and scripts.

### Override Options
- `--write-mode {append,overwrite,skip}`, `-m {append,overwrite,skip}`: Overrides the `write_mode` defined in YAML.
- `--tools <list>`, `-t <list>`: Comma-separated list of tools to configure (for example, `--tools claude,cursor,antigravity`).
- `--profile {full,strict,standard,safe,minimal}`, `-p {profile}`: Overrides the profile defined in YAML.
- `--no-hooks`: Disables Git pre-commit hook installation regardless of YAML setting.
- `--no-mcp`: Disables Model Context Protocol configuration regardless of YAML setting.
- `--no-skills`: Disables AI agent skill installation regardless of YAML setting.

---

## Usage Examples

### Preview changes in dry-run mode
```bash
python scripts/apply_config.py --config configs/safe.yaml --dry-run
```

### Apply configuration non-interactively
```bash
python scripts/apply_config.py --config config.yaml --yes
```

### Apply only to Claude and Cursor with append mode
```bash
python scripts/apply_config.py --tools claude,cursor --write-mode append --yes
```

### Export execution plan to JSON
```bash
python scripts/apply_config.py --json > plan.json
```
