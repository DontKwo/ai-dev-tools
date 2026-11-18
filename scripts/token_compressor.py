"""Token compressor for agent terminal commands.
Compresses command outputs by 60% to 90% to prevent context bloat.
"""

import re
import sys


def compress_git_status(raw: str) -> str:
    """Compress git status output into a concise summary."""
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    modified = []
    untracked = []
    branch = "unknown"

    for line in lines:
        if line.startswith("# On branch") or line.startswith("On branch"):
            branch = line.split()[-1]
        elif line.startswith("modified:"):
            modified.append(line.split()[-1])
        elif line.startswith("Untracked files:") or line.startswith("Changes not staged"):
            continue
        elif not line.startswith("(") and not line.startswith("no changes added"):
            if "/" in line or "." in line:
                untracked.append(line)

    summary = [f"Branch: {branch}"]
    if modified:
        summary.append(f"Modified ({len(modified)}): " + ", ".join(modified[:10]))
        if len(modified) > 10:
            summary.append(f"  ... and {len(modified) - 10} more modified")
    if untracked:
        summary.append(f"Untracked ({len(untracked)}): " + ", ".join(untracked[:10]))
        if len(untracked) > 10:
            summary.append(f"  ... and {len(untracked) - 10} more untracked")
    if not modified and not untracked:
        summary.append("Working tree clean.")

    return "\n".join(summary)


def compress_test_output(raw: str) -> str:
    """Condense test runner logs, keeping failures while trimming passing noise."""
    lines = raw.splitlines()
    if not lines:
        return ""

    has_failures = any("FAILED" in line or "FAIL:" in line or "ERROR:" in line for line in lines)
    if not has_failures:
        for line in reversed(lines):
            if re.search(r"Ran \d+ tests? in", line) or re.search(r"\d+ passed", line):
                return f"[PASS] {line.strip()}"
        return "[PASS] All tests passed."

    failure_lines = []
    capturing = False
    for line in lines:
        if any(marker in line for marker in ("FAIL:", "ERROR:", "Traceback", "FAILED")):
            capturing = True
        if capturing:
            failure_lines.append(line)
        if line.startswith("Ran ") or line.startswith("FAILED ("):
            failure_lines.append(line)
            capturing = False

    return "\n".join(failure_lines) if failure_lines else raw


def compress_command_output(command: str, raw_output: str) -> tuple[str, float]:
    """Compress terminal output based on command type and return savings ratio."""
    cmd_lower = command.lower()
    original_len = len(raw_output)
    if original_len == 0:
        return "", 0.0

    if "git status" in cmd_lower:
        compressed = compress_git_status(raw_output)
    elif any(runner in cmd_lower for runner in ("pytest", "unittest", "cargo test", "npm test")):
        compressed = compress_test_output(raw_output)
    else:
        # Fallback: remove empty lines and deduplicate repetitive lines
        seen_lines: set[str] = set()
        deduped = []
        for line in raw_output.splitlines():
            stripped = line.strip()
            if stripped and stripped not in seen_lines:
                deduped.append(line)
                seen_lines.add(stripped)
        compressed = "\n".join(deduped)

    new_len = len(compressed)
    savings = max(0.0, 1.0 - (new_len / max(1, original_len)))
    return compressed, savings


def main() -> int:
    """CLI entrypoint for standalone token compression."""
    if len(sys.argv) < 2:
        return 0

    command_name = sys.argv[1]
    input_text = sys.stdin.read()
    result, savings = compress_command_output(command_name, input_text)
    header = f"[RTK-Filter: {savings * 100:.1f}% token savings]\n"
    sys.stdout.write(header + result + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
