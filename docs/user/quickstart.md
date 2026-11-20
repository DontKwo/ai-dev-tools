# Quickstart Guide for Everyday Users

Get started with AI-Dev-Tools in 3 simple steps without writing code or running terminal commands.

## Step 1: Download the Setup App

Download the standalone setup application for your operating system:

| Platform | Download File |
| :--- | :--- |
| **Windows** | `adt-setup.exe` |
| **Linux** | `adt-setup-linux` |
| **macOS** | `adt-setup-macos` |

Prebuilt binaries are available under the **Releases** or **Actions** tab of this repository. No Python installation is required.

## Step 2: Open the Setup Assistant

1. Double-click the downloaded setup application.
2. The setup assistant window opens displaying your current project folder.
3. Select which AI assistants you use:
   - Claude Code (`CLAUDE.md`)
   - Cursor IDE (`.cursorrules`)
   - Google Antigravity (`AGENTS.md`)
   - Cline / Roo Code (`.clinerules`)
   - GitHub Copilot (`.github/copilot-instructions.md`)
   - Windsurf, Aider, or OpenAI Codex

## Step 3: Click "Apply Changes"

1. Optional: Click **Preview Changes & Safety Check** to review what files will be created.
2. Click **Apply Changes**.
3. A confirmation dialog confirms that your assistants are configured.

You are done. Your AI tools will now adhere to clean coding standards, AST verification, and safety checks.

---

## Need More Details?

- To customize rules via YAML: see [YAML Configuration Guide](../power-users/yaml-guide.md).
- To run automated setup in terminal or scripts: see [CLI Reference](../power-users/cli-reference.md).
- To understand profiles and strictness levels: see [Rule Profiles](../power-users/profiles.md).
- For developer documentation: see [Developer Architecture](../developer/architecture.md).
