#!/usr/bin/env bash
# Developer AI Tools Setup for Linux & macOS

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIGURATOR="$SCRIPT_DIR/scripts/configure.py"

echo "======================================================================"
echo "               Developer AI Tools Setup (Linux/macOS)"
echo "======================================================================"
echo "This setup configures AI developer tools (Claude Code, Cursor, Cline,"
echo "Google Antigravity, OpenAI Codex, Windsurf, GitHub Copilot, and Aider)"
echo "with unified coding rules, automated AST linting, an MCP server, and"
echo "33 agent workflow skills."
echo ""
echo "Before any files are modified, you will see a plain-prose preview of"
echo "all planned actions and can approve, reject, or customize each one."
echo "======================================================================"
echo ""
echo "Repo directory: $SCRIPT_DIR"
echo ""

# Check for uv or Python
PY_RUNNER=""
if command -v uv >/dev/null 2>&1; then
    PY_RUNNER="uv run --no-project python"
    echo "[OK] uv detected: $(uv --version)"
elif command -v python3 >/dev/null 2>&1; then
    PY_RUNNER="python3"
    echo "[OK] Python detected: $(python3 --version 2>&1)"
elif command -v python >/dev/null 2>&1; then
    PY_RUNNER="python"
    echo "[OK] Python detected: $(python --version 2>&1)"
else
    echo "[!] ERROR: Neither uv nor Python 3 was found in your PATH."
    echo "    Please install uv (https://docs.astral.sh/uv/) or Python 3.9+."
    exit 1
fi

echo ""
echo "Choose configuration mode:"
echo "  [1] Guided Interactive Setup (Recommended: choose tools, scope, and review plan)"
echo "  [2] Configure ALL AI Tools globally (previews plan before applying)"
echo "  [3] Configure Claude Code only globally (previews plan before applying)"
echo ""

read -r -p "Select option [1, 2, or 3, default 1]: " mode_choice
mode_choice="${mode_choice:-1}"

case "$mode_choice" in
    1)
        echo ""
        $PY_RUNNER "$CONFIGURATOR"
        ;;
    2)
        echo ""
        $PY_RUNNER "$CONFIGURATOR" --tools all --scope global --action append
        ;;
    3)
        echo ""
        $PY_RUNNER "$CONFIGURATOR" --tools claude --scope global --action append
        ;;
    *)
        echo ""
        $PY_RUNNER "$CONFIGURATOR"
        ;;
esac

# Optional vulture install
echo ""
echo "----------------------------------------------------------------------"
echo "Optional Dependency: Vulture Dead Code Analyzer"
echo "----------------------------------------------------------------------"
echo "Vulture statically scans Python code for unreferenced functions and dead"
echo "code. It is only required if you run full whole-repository audits (--level full)."
echo ""
read -r -p "[?] Install optional 'vulture' package? [y/N]: " inst_vulture
case "$inst_vulture" in
    [Yy]*)
        if command -v uv >/dev/null 2>&1; then
            uv tool install vulture || echo "[!] Could not install vulture automatically."
        else
            pip install vulture || echo "[!] Could not install vulture automatically."
        fi
        ;;
    *)
        echo "[=] Skipped vulture installation."
        ;;
esac

# Global terminal shortcuts
echo ""
echo "----------------------------------------------------------------------"
echo "Optional Convenience: Global Terminal Shortcuts"
echo "----------------------------------------------------------------------"
echo "Adding symlinks to ~/.local/bin lets you run shortcuts like 'aitools',"
echo "'ailint', and 'aifix' directly from your shell."
echo ""
read -r -p "[?] Install global shortcuts into ~/.local/bin? [Y/n]: " inst_shortcuts
case "$inst_shortcuts" in
    [Nn]*)
        echo "[=] Skipped global shortcuts."
        ;;
    *)
        mkdir -p "$HOME/.local/bin"
        for cmd_file in "$SCRIPT_DIR/bin/"*; do
            cmd_name="$(basename "$cmd_file")"
            if [ "${cmd_name##*.}" != "cmd" ]; then
                ln -sf "$cmd_file" "$HOME/.local/bin/$cmd_name"
            fi
        done
        chmod +x "$SCRIPT_DIR/bin/"*
        echo "[OK] Symlinks created in ~/.local/bin/ (ensure ~/.local/bin is in your PATH)."
        ;;
esac

echo ""
echo "Setup finished. Selected AI tools configured."
