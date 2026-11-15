#!/usr/bin/env python3
"""Installs or uninstalls the git pre-commit lint hook as a marked block.
Existing hook content is preserved; only the ai-dev-tools block is added, replaced, or removed.
"""

import argparse
import re
import stat
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import IS_WINDOWS

REPO_ROOT = Path(__file__).resolve().parent.parent
LINTER_SCRIPT = REPO_ROOT / "scripts" / "claudemd_linter.py"

PYTHON_CMD = "python" if IS_WINDOWS else "python3"
SHEBANG = "#!/usr/bin/env sh"
BEGIN_MARKER = "# BEGIN AI-DEV-TOOLS"
END_MARKER = "# END AI-DEV-TOOLS"
BLOCK_RE = re.compile(rf"\n*{re.escape(BEGIN_MARKER)}.*?{re.escape(END_MARKER)}\n*", re.DOTALL)


def create_hook_block() -> str:
    linter_posix = str(LINTER_SCRIPT).replace("\\", "/")
    return f"""{BEGIN_MARKER}
echo "Running claudemd_linter on staged files..."
if command -v uv >/dev/null 2>&1; then
    uv run --no-project python "{linter_posix}" --staged
else
    {PYTHON_CMD} "{linter_posix}" --staged
fi
if [ $? -ne 0 ]; then
    echo ""
    echo "[!] COMMIT REJECTED: claudemd_linter found rule violations."
    echo "    Fix all violations listed above before committing."
    echo "    To bypass only if truly necessary: git commit --no-verify"
    exit 1
fi
{END_MARKER}"""


def create_hook_content() -> str:
    return f"{SHEBANG}\n{create_hook_block()}\n"


def merge_block(existing: str) -> str:
    block = create_hook_block()
    if BEGIN_MARKER in existing and END_MARKER in existing:
        return BLOCK_RE.sub(lambda _match: f"\n{block}\n", existing, count=1).lstrip("\n")
    lines = existing.splitlines()
    if lines and lines[0].startswith("#!"):
        return "\n".join([lines[0], block, *lines[1:]]) + "\n"
    return f"{SHEBANG}\n{block}\n{existing}"


def choose_action(hook_file: Path) -> str:
    if not sys.stdin.isatty():
        return "append"
    print(f"\n[?] Existing pre-commit hook found at: {hook_file}")
    print("    [A] Add lint block to existing hook (default)")
    print("    [O] Overwrite")
    print("    [S] Skip")
    choice = input("    Choose action [A/O/S, default A]: ").strip().lower()
    if choice in ("o", "overwrite"):
        return "overwrite"
    if choice in ("s", "skip"):
        return "skip"
    return "append"


def install_hook(target_repo: Path, action: str = "append") -> None:
    git_dir = target_repo / ".git"
    if not git_dir.is_dir():
        print(f"[!] Error: {target_repo} is not a git repository (.git folder not found).")
        return

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_file = hooks_dir / "pre-commit"

    if hook_file.exists():
        chosen = choose_action(hook_file) if action == "ask" else action
        if chosen == "skip":
            print(f"[-] Skipped: {hook_file}")
            return
        if chosen == "overwrite":
            hook_file.write_text(create_hook_content(), encoding="utf-8")
            print(f"[+] Overwrote pre-commit hook at: {hook_file}")
        else:
            existing = hook_file.read_text(encoding="utf-8", errors="replace")
            hook_file.write_text(merge_block(existing), encoding="utf-8")
            print(f"[+] Added linter block to pre-commit hook: {hook_file}")
    else:
        hook_file.write_text(create_hook_content(), encoding="utf-8")
        print(f"[+] Created pre-commit hook at: {hook_file}")

    try:
        hook_file.chmod(hook_file.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except OSError:
        return


def uninstall_hook(target_repo: Path) -> None:
    hook_file = target_repo / ".git" / "hooks" / "pre-commit"
    if not hook_file.is_file():
        print(f"[-] No pre-commit hook found in {target_repo}")
        return

    existing = hook_file.read_text(encoding="utf-8", errors="replace")
    if BEGIN_MARKER not in existing or END_MARKER not in existing:
        print(f"[-] Pre-commit hook has no ai-dev-tools block, left untouched: {hook_file}")
        return

    remainder = BLOCK_RE.sub("\n", existing, count=1)
    meaningful = [ln for ln in remainder.splitlines() if ln.strip() and not ln.startswith("#!")]
    if meaningful:
        hook_file.write_text(remainder.strip("\n") + "\n", encoding="utf-8")
    else:
        hook_file.unlink()
    print(f"[+] Removed pre-commit hook block from {hook_file}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Install claudemd_linter git pre-commit hook.")
    parser.add_argument("target", nargs="?", default=".", help="Target git repository path (default: current directory)")
    parser.add_argument("--uninstall", action="store_true", help="Remove only the ai-dev-tools block from the pre-commit hook")
    parser.add_argument("--action", choices=["ask", "overwrite", "append", "skip"], default="append")
    args = parser.parse_args()

    target = Path(args.target).resolve()
    if args.uninstall:
        uninstall_hook(target)
    else:
        install_hook(target, action=args.action)


if __name__ == "__main__":
    main()
