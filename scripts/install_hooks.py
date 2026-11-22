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


def _create_pre_push_block() -> str:
    linter_posix = str(LINTER_SCRIPT).replace("\\", "/")
    link_posix = str(REPO_ROOT / "scripts" / "link_checker.py").replace("\\", "/")
    return f"""{BEGIN_MARKER}
echo "Running strict repository lint and documentation link check..."
if command -v uv >/dev/null 2>&1; then
    uv run --no-project python "{linter_posix}" . --diff --level strict && uv run --no-project python "{link_posix}" .
else
    {PYTHON_CMD} "{linter_posix}" . --diff --level strict && {PYTHON_CMD} "{link_posix}" .
fi
if [ $? -ne 0 ]; then
    echo ""
    echo "[!] PUSH REJECTED: strict linter or link_checker found violations."
    echo "    Fix all violations before pushing or bypass only with: git push --no-verify"
    exit 1
fi
{END_MARKER}"""


def create_hook_content(hook_type: str = "pre-commit") -> str:
    if hook_type == "pre-push":
        return f"{SHEBANG}\n{_create_pre_push_block()}\n"
    return f"{SHEBANG}\n{create_hook_block()}\n"


def merge_block(existing: str, hook_type: str = "pre-commit") -> str:
    block = _create_pre_push_block() if hook_type == "pre-push" else create_hook_block()
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


def install_hook(target_repo: Path, action: str = "append", hook_type: str = "pre-commit") -> None:
    git_dir = target_repo / ".git"
    if not git_dir.is_dir():
        print(f"[!] Error: {target_repo} is not a git repository (.git folder not found).")
        return

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_file = hooks_dir / hook_type

    if hook_file.exists():
        chosen = choose_action(hook_file) if action == "ask" else action
        if chosen == "skip":
            print(f"[-] Skipped: {hook_file}")
            return
        if chosen == "overwrite":
            hook_file.write_text(create_hook_content(hook_type), encoding="utf-8")
            print(f"[+] Overwrote {hook_type} hook at: {hook_file}")
        else:
            existing = hook_file.read_text(encoding="utf-8", errors="replace")
            hook_file.write_text(merge_block(existing, hook_type), encoding="utf-8")
            print(f"[+] Added linter block to {hook_type} hook: {hook_file}")
    else:
        hook_file.write_text(create_hook_content(hook_type), encoding="utf-8")
        print(f"[+] Created {hook_type} hook at: {hook_file}")

    try:
        hook_file.chmod(hook_file.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except OSError:
        return


def uninstall_hook(target_repo: Path, hook_type: str = "pre-commit") -> None:
    hook_file = target_repo / ".git" / "hooks" / hook_type
    if not hook_file.is_file():
        print(f"[-] No {hook_type} hook found in {target_repo}")
        return

    existing = hook_file.read_text(encoding="utf-8", errors="replace")
    if BEGIN_MARKER not in existing or END_MARKER not in existing:
        print(f"[-] {hook_type} hook has no ai-dev-tools block, left untouched: {hook_file}")
        return

    remainder = BLOCK_RE.sub("\n", existing, count=1)
    meaningful = [ln for ln in remainder.splitlines() if ln.strip() and not ln.startswith("#!")]
    if meaningful:
        hook_file.write_text(remainder.strip("\n") + "\n", encoding="utf-8")
    else:
        hook_file.unlink()
    print(f"[+] Removed {hook_type} hook block from {hook_file}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Install claudemd_linter git pre-commit and pre-push hooks.")
    parser.add_argument("target", nargs="?", default=".", help="Target git repository path (default: current directory)")
    parser.add_argument("--uninstall", action="store_true", help="Remove only the ai-dev-tools block from the hook")
    parser.add_argument("--pre-push", action="store_true", help="Target the git pre-push hook instead of pre-commit")  # noqa: 5
    parser.add_argument("--all-hooks", action="store_true", help="Install or remove both pre-commit and pre-push hooks")
    parser.add_argument("--action", choices=["ask", "overwrite", "append", "skip"], default="append")
    args = parser.parse_args()

    target = Path(args.target).resolve()
    hook_types = ["pre-commit", "pre-push"] if args.all_hooks else (["pre-push"] if args.pre_push else ["pre-commit"])
    for hook_type in hook_types:
        if args.uninstall:
            uninstall_hook(target, hook_type=hook_type)
        else:
            install_hook(target, action=args.action, hook_type=hook_type)


if __name__ == "__main__":
    main()
