# Installing ai-dev-tools

## Claude Code, Codex, Copilot CLI, and VS Code plugin

Install as a plugin so skills stay updated automatically when the repository advances:

### Claude Code

```bash
/plugin marketplace add DontKwo/ai-dev-tools
/plugin install ai-dev-tools@ai-dev-tools
```

### GitHub Copilot CLI

```bash
copilot plugin marketplace add DontKwo/ai-dev-tools
copilot plugin install ai-dev-tools@ai-dev-tools
```

### VS Code

Add to `settings.json`:

```json
{
  "chat.plugins.marketplaces": [
    "DontKwo/ai-dev-tools"
  ]
}
```

### Gemini CLI

```bash
gemini skills install https://github.com/DontKwo/ai-dev-tools.git
```

### Universal agents via skills.sh

Works for Cursor, Windsurf, Cline, Antigravity, OpenAI Codex, and Claude Code:

```bash
npx skills@latest add DontKwo/ai-dev-tools
```

## Full local CLI, MCP server, and linter setup

Clone the repository and run the setup script for your platform to register rules, the 28-tool MCP server, the `aitools` CLI shortcuts, and synchronized skills across all detected editors:

```cmd
setup.bat
```

On macOS and Linux:

```bash
chmod +x setup.sh
./setup.sh
```

Or synchronize skills directly from a local clone (pass `--link` to symlink instead of copy):

```bash
uv run --no-project python scripts/skills_manager.py sync --scope both --link
```
