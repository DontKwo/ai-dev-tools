"""CLI tool for UI test harness initialization, manifest generation, and audit verification."""

import argparse
import base64
import hashlib
import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.ui_combinations import generate_required_cases  # noqa: 12
from scripts.ui_config import UiConfig, load_ui_config  # noqa: 12
from scripts.ui_engine import build_manifest, evaluate_evidence_rules, evaluate_static_rules  # noqa: 12
from scripts.ui_evidence import load_ui_evidence  # noqa: 12
from scripts.ui_models import UiManifest  # noqa: 12

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "ui_audit"


def init_framework(target_dir: Path, framework: str) -> int:
    src_dir = TEMPLATE_DIR / framework.lower()
    if not src_dir.is_dir():
        print(f"Error: Unknown framework '{framework}'. Available: pyqt, web, android, flutter, ios, tkinter, wxpython, kivy, textual, dotnet")  # noqa: 25
        return 1

    dest_dir = target_dir / "ui_audit"
    dest_dir.mkdir(parents=True, exist_ok=True)
    for f in src_dir.glob("*"):
        if f.is_file():
            shutil.copy2(f, dest_dir / f.name)

    uilint_file = target_dir / ".uilint.toml"
    if not uilint_file.exists():
        content = (
            f'[project]\nframeworks = ["{framework}"]\n\n'
            "[tests]\nevidence = \"ui_evidence.json\"\n\n"
            "[combos]\nexhaustive_state_max = 8\nordered_triples_max_actions = 6\n"
        )
        uilint_file.write_text(content, encoding="utf-8")

    print(f"Initialized UI audit helper for {framework} in {dest_dir}")  # noqa: 25
    return 0


def run_manifest_cmd(target_dir: Path, output_path: Path | None = None) -> int:
    config = load_ui_config(target_dir)
    manifest = build_manifest(target_dir, config)
    out = output_path or (target_dir / "ui_manifest.json")
    out.write_text(json.dumps(manifest.to_dict(), indent=2), encoding="utf-8")
    print(f"Wrote manifest with {len(manifest.controls)} controls and {len(manifest.screens)} screens to {out}")  # noqa: 25
    return 0


def run_evidence_summary(target_dir: Path) -> int:
    config = load_ui_config(target_dir)
    manifest = build_manifest(target_dir, config)
    evidence_file = target_dir / config.evidence_path
    evidence = load_ui_evidence(evidence_file, manifest)
    if evidence is None:
        print(f"No valid evidence file at {evidence_file}")  # noqa: 25
        return 1

    trusted_interactions = [i for i in evidence.interactions if i.trusted]
    print(f"Run ID: {evidence.run_id} ({evidence.framework})")  # noqa: 25
    print(f"Trusted interactions: {len(trusted_interactions)}")  # noqa: 25
    print(f"Cases executed: {len(evidence.cases)}")  # noqa: 25
    print(f"Layout findings: {len(evidence.layout_findings)}")  # noqa: 25
    print(f"A11y findings: {len(evidence.a11y_findings)}")  # noqa: 25
    return 0


def run_audit(target_dir: Path) -> int:
    config = load_ui_config(target_dir)
    manifest = build_manifest(target_dir, config)
    evidence = load_ui_evidence(target_dir / config.evidence_path, manifest)

    static_violations = evaluate_static_rules(target_dir, manifest, config)
    evidence_violations = evaluate_evidence_rules(target_dir, manifest, evidence, config)
    all_violations = static_violations + evidence_violations

    if not all_violations:
        print("None. UI audit clean.")  # noqa: 25
        return 0

    print(f"Found {len(all_violations)} UI violation(s):")  # noqa: 25
    for path, line, code in all_violations:
        print(f"  {path}:{line} | code={code}")  # noqa: 25
    return 1


def _find_chromium_executable() -> str | None:
    candidates: list[str | None] = [
        shutil.which("chrome"),
        shutil.which("chromium"),
        shutil.which("msedge"),
    ]
    for env_key in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
        base = os.environ.get(env_key, "").strip()
        if not base:
            continue
        base_path = Path(base)
        candidates.append(str(base_path / "Google" / "Chrome" / "Application" / "chrome.exe"))
        candidates.append(str(base_path / "Microsoft" / "Edge" / "Application" / "msedge.exe"))
    for cand in candidates:
        if cand and Path(cand).is_file():
            return str(cand)
    return None


def _cdp_roundtrip(ws_url: str, js_expr: str, wait_ms: int = 800) -> dict:
    host_port_path = ws_url.replace("ws://", "", 1)
    host_port, ws_path = host_port_path.split("/", 1)
    host, port_s = host_port.split(":", 1)
    sock = socket.create_connection((host, int(port_s)), timeout=10.0)
    try:
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        handshake = (
            f"GET /{ws_path} HTTP/1.1\r\nHost: {host_port}\r\n"
            f"Upgrade: websocket\r\nConnection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        )
        sock.sendall(handshake.encode("ascii"))
        buf = b""
        while b"\r\n\r\n" not in buf:
            buf += sock.recv(4096)
        time.sleep(wait_ms / 1000.0)
        payload = json.dumps({"id": 1, "method": "Runtime.evaluate", "params": {"expression": js_expr, "returnByValue": True}}).encode("utf-8")
        mask = os.urandom(4)
        header = bytearray([0x81])
        length = len(payload)
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.append(0x80 | 126)
            header.extend(struct.pack(">H", length))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack(">Q", length))
        header.extend(mask)
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        sock.sendall(bytes(header) + masked)
        raw = sock.recv(65536)
        idx = raw.find(b"{")
        if idx >= 0:
            return json.loads(raw[idx:].decode("utf-8", errors="ignore"))
        return {}
    finally:
        sock.close()


def run_verify_live(url: str, out_dir: Path | None = None) -> int:
    browser = _find_chromium_executable()
    if browser is None:
        print("Error: No headless Chrome/Edge executable found on system.")  # noqa: 25
        return 1
    profile_dir = tempfile.mkdtemp(prefix="aiui_verify_")
    port = 9239
    proc = subprocess.Popen(
        [browser, "--headless=new", "--disable-gpu", f"--remote-debugging-port={port}", f"--user-data-dir={profile_dir}", "--window-size=1440,900", url],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        ws_url = ""
        for _ in range(30):
            try:
                data = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=1.0).read().decode("utf-8"))
                if data and data[0].get("webSocketDebuggerUrl"):
                    ws_url = data[0]["webSocketDebuggerUrl"]
                    break
            except Exception:
                time.sleep(0.25)
        if not ws_url:
            print("Error: Timed out waiting for CDP endpoint.")  # noqa: 25
            return 1
        audit_js = (
            "(() => {"
            " const btns = Array.from(document.querySelectorAll('button'));"
            " const bright = btns.filter(b => {"
            "   const bg = getComputedStyle(b).backgroundColor;"
            "   const m = bg.match(/\\d+/g); if (!m || m.length < 3) return false;"
            "   if (m[3] === '0') return false;"
            "   return (+m[0]*0.299 + +m[1]*0.587 + +m[2]*0.114) > 200;"
            " }).map(b => b.textContent.trim().slice(0, 30));"
            " const textLen = (document.body.innerText || '').trim().length;"
            " return { textLen, brightButtons: bright, violationsVisible: (document.body.innerText || '').includes('VIOLATIONS') };"
            "})()"
        )
        res = _cdp_roundtrip(ws_url, audit_js, wait_ms=1500)
        audit_data = res.get("result", {}).get("result", {}).get("value", {})
        if out_dir is not None:
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "live_audit.json").write_text(json.dumps(audit_data, indent=2), encoding="utf-8")
        print(f"Live UI audit result: {json.dumps(audit_data)}")  # noqa: 25
        if audit_data.get("brightButtons") or audit_data.get("textLen", 0) == 0:
            return 1
        return 0
    finally:
        proc.terminate()
        shutil.rmtree(profile_dir, ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Multi-framework UI Quality & Audit Tool")
    subparsers = parser.add_subparsers(dest="subcommand")

    init_p = subparsers.add_parser("init", help="Initialize UI audit test driver in project")
    init_p.add_argument("--framework", required=True, help="Target UI framework name")
    init_p.add_argument("target", nargs="?", default=".", help="Target project root directory")

    man_p = subparsers.add_parser("manifest", help="Extract and write ui_manifest.json")
    man_p.add_argument("target", nargs="?", default=".", help="Target directory")
    man_p.add_argument("-o", "--output", help="Output path for ui_manifest.json")

    ev_p = subparsers.add_parser("evidence", help="Inspect and summarize ui_evidence.json")
    ev_p.add_argument("target", nargs="?", default=".", help="Target directory")

    audit_p = subparsers.add_parser("audit", help="Run static and runtime UI checks")
    audit_p.add_argument("target", nargs="?", default=".", help="Target directory")

    live_p = subparsers.add_parser("verify-live", help="Inspect running web app in headless Chromium")
    live_p.add_argument("--url", required=True, help="Target URL to inspect")
    live_p.add_argument("--out", help="Optional output directory for audit JSON")

    args = parser.parse_args()
    if args.subcommand == "init":
        sys.exit(init_framework(Path(args.target).resolve(), args.framework))
    elif args.subcommand == "manifest":
        out = Path(args.output).resolve() if args.output else None
        sys.exit(run_manifest_cmd(Path(args.target).resolve(), out))
    elif args.subcommand == "evidence":
        sys.exit(run_evidence_summary(Path(args.target).resolve()))
    elif args.subcommand == "audit":
        sys.exit(run_audit(Path(args.target).resolve()))
    elif args.subcommand == "verify-live":
        out_d = Path(args.out).resolve() if args.out else None
        sys.exit(run_verify_live(args.url, out_d))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
