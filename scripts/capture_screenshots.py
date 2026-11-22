"""Capture deterministic desktop and mobile screenshots from a running local app or URL."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

BROWSER_CANDIDATES_WIN = [
    os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Microsoft", "Edge", "Application", "msedge.exe"),
    os.path.join(os.environ.get("ProgramFiles", ""), "Microsoft", "Edge", "Application", "msedge.exe"),
    os.path.join(os.environ.get("ProgramFiles", ""), "Google", "Chrome", "Application", "chrome.exe"),
]

BROWSER_CANDIDATES_POSIX = [
    "google-chrome",
    "chromium",
    "chromium-browser",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
]


def find_headless_browser() -> str | None:
    """Locate Edge or Chrome binary for headless screenshot capture."""
    if os.name == "nt":
        for candidate in BROWSER_CANDIDATES_WIN:
            if candidate and Path(candidate).is_file():
                return candidate
        for name in ("msedge", "chrome"):
            found = shutil.which(name)
            if found:
                return found
        return None

    for candidate in BROWSER_CANDIDATES_POSIX:
        if os.path.sep in candidate:
            if Path(candidate).is_file():
                return candidate
        else:
            found = shutil.which(candidate)
            if found:
                return found
    return None


def wait_for_url(url: str, timeout_sec: float = 15.0) -> bool:
    """Wait until local HTTP server responds with status 200."""
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.5) as resp:
                if resp.status < 500:
                    return True
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(0.2)
    return False


def capture_with_browser(url: str, output_png: Path, width: int = 1280, height: int = 800, virtual_budget_ms: int = 1800) -> bool:
    """Capture a viewport PNG using Chromium headless mode."""
    browser = find_headless_browser()
    if not browser:
        return False

    output_png.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as profile_dir:
        cmd = [
            browser,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--hide-scrollbars",
            f"--user-data-dir={profile_dir}",
            f"--window-size={width},{height}",
            f"--virtual-time-budget={virtual_budget_ms}",
            f"--screenshot={output_png}",
            url,
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=45)
    return res.returncode == 0 and output_png.is_file() and output_png.stat().st_size > 1000


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture PNG screenshots from a local URL.")
    parser.add_argument("--url", required=True, help="HTTP URL to capture")
    parser.add_argument("--out", required=True, type=Path, help="Destination PNG file path")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=800)
    parser.add_argument("--delay-ms", type=int, default=1800)
    args = parser.parse_args()

    if not wait_for_url(args.url):
        sys.stderr.write(f"Server did not respond in time: {args.url}\n")
        return 1
    if not capture_with_browser(args.url, args.out, args.width, args.height, args.delay_ms):
        sys.stderr.write("Headless browser capture failed.\n")
        return 1
    print(f"[OK] Saved screenshot: {args.out}")  # noqa: 25
    return 0


if __name__ == "__main__":
    sys.exit(main())
