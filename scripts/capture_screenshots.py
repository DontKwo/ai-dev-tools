"""Capture deterministic desktop and mobile screenshots and sync visually changed PNGs."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

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
    "microsoft-edge",
    "msedge",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
]


def find_headless_browser() -> str | None:
    """Locate Chrome/Chromium/Edge binary for headless screenshot capture."""
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
    """Wait until local HTTP server responds cleanly."""
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.5) as resp:
                if resp.status < 500:
                    return True
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(0.2)
    return False


def capture_with_browser(
    url: str,
    output_png: Path,
    width: int = 1280,
    height: int = 800,
    virtual_budget_ms: int = 1800,
) -> bool:
    """Capture a viewport PNG using Chromium headless mode with resolved output path."""
    browser = find_headless_browser()
    if not browser:
        return False

    resolved_png = output_png.expanduser().resolve()
    resolved_png.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as profile_dir:
        cmd = [
            browser,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-background-networking",
            "--no-first-run",
            "--no-default-browser-check",
            "--hide-scrollbars",
            f"--user-data-dir={profile_dir}",
            f"--window-size={width},{height}",
            f"--virtual-time-budget={virtual_budget_ms}",
            f"--screenshot={resolved_png}",
            url,
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=45)
    return res.returncode == 0 and resolved_png.is_file() and resolved_png.stat().st_size > 1000


def compute_image_diff_rmse(path_a: Path, path_b: Path) -> float:
    """Compute RGB pixel RMSE (0-255 scale) between two PNG images, or 255.0 on size mismatch."""
    if not path_a.is_file() or not path_b.is_file():
        return 255.0
    if hashlib.sha256(path_a.read_bytes()).digest() == hashlib.sha256(path_b.read_bytes()).digest():
        return 0.0
    if importlib.util.find_spec("PIL") is None:
        return 255.0
    from PIL import Image, ImageChops  # noqa: 13

    with Image.open(path_a) as img_a, Image.open(path_b) as img_b:
        rgb_a = img_a.convert("RGBA")
        rgb_b = img_b.convert("RGBA")
        if rgb_a.size != rgb_b.size:
            return 255.0
        diff = ImageChops.difference(rgb_a, rgb_b)
        histogram = diff.histogram()
        total_pixels = rgb_a.size[0] * rgb_a.size[1] * 4
        sum_squares = sum((idx % 256) ** 2 * count for idx, count in enumerate(histogram))
        return (sum_squares / max(1, total_pixels)) ** 0.5


def sync_screenshot_directory(src_dir: Path, dest_dir: Path, threshold: float = 1.5) -> list[str]:
    """Copy PNGs from src_dir to dest_dir only when visually changed beyond threshold RMSE."""
    src_resolved = src_dir.resolve()
    dest_resolved = dest_dir.resolve()
    dest_resolved.mkdir(parents=True, exist_ok=True)
    updated: list[str] = []
    for candidate in sorted(src_resolved.glob("*.png")):
        if not candidate.is_file() or candidate.stat().st_size < 1000:
            continue
        target = dest_resolved / candidate.name
        rmse = compute_image_diff_rmse(candidate, target)
        if not target.is_file() or rmse > threshold:
            shutil.copy2(candidate, target)
            updated.append(f"{candidate.name} (rmse={rmse:.2f})")
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture PNG screenshots or sync visually changed PNG directories.")
    parser.add_argument("--url", default=None, help="HTTP URL to capture")
    parser.add_argument("--out", default=None, type=Path, help="Destination PNG file path")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=800)
    parser.add_argument("--delay-ms", type=int, default=1800)
    parser.add_argument("--sync-dir", nargs=2, metavar=("SRC", "DEST"), help="Sync changed PNGs from SRC into DEST")
    parser.add_argument("--threshold", type=float, default=1.5, help="RMSE pixel difference threshold for --sync-dir")
    args = parser.parse_args()

    if args.sync_dir:
        src_dir, dest_dir = Path(args.sync_dir[0]), Path(args.sync_dir[1])
        changed = sync_screenshot_directory(src_dir, dest_dir, threshold=args.threshold)
        if changed:
            sys.stdout.write("UPDATED_SCREENSHOTS: " + ", ".join(changed) + "\n")
        else:
            sys.stdout.write("SCREENSHOTS_UP_TO_DATE\n")
        return 0

    if not args.url or args.out is None:
        parser.error("Provide --url and --out, or --sync-dir SRC DEST.")

    if not wait_for_url(args.url):
        sys.stderr.write(f"Server did not respond in time: {args.url}\n")
        return 1
    if not capture_with_browser(args.url, args.out, args.width, args.height, args.delay_ms):
        sys.stderr.write("Headless browser capture failed.\n")
        return 1
    sys.stdout.write(f"[OK] Saved screenshot: {args.out}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
