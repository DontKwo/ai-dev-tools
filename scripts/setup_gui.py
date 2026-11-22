"""Unified WebView Setup Assistant and HTTP backend for AI-Dev-Tools."""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

REPO_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from apply_config import (  # noqa: 12
    ConfigExecutionPlan,
    build_plan_from_config,
    detect_workspace_integrations,
    execute_plan,
    format_plan_preview,
    uninstall_configuration,
)
from capture_screenshots import capture_with_browser, find_headless_browser  # noqa: 12
from install_hooks import install_hook, uninstall_hook  # noqa: 12
from yaml_utils import load_yaml_file  # noqa: 12


@dataclasses.dataclass
class SetupGuiModel:
    workspace: str = dataclasses.field(default_factory=lambda: str(Path.cwd()))
    scope: str = "workspace"
    write_mode: str = "append"
    profile_level: str = "strict"
    skip_rules: str = ""
    tools: dict[str, bool] = dataclasses.field(
        default_factory=lambda: {
            "claude": True,
            "cursor": True,
            "cline": True,
            "antigravity": True,
            "codex": True,
            "windsurf": True,
            "copilot": True,
            "aider": True,
        }
    )
    targets: dict[str, bool] = dataclasses.field(
        default_factory=lambda: {
            "claude_md": True,
            "agents_md": True,
            "cursorrules": True,
            "clinerules": True,
            "windsurfrules": True,
            "aider_conventions": True,
            "copilot_instructions": True,
        }
    )
    mcp_enabled: bool = True
    mcp_server_name: str = "ai-dev-tools"
    skills_enabled: bool = True
    skill_bundle: str = "all"
    git_hook_enabled: bool = True
    git_pre_push_enabled: bool = True
    git_hook_command: str = "uv run --no-project python scripts/claudemd_linter.py . --diff"

    def to_config_dict(self) -> dict[str, Any]:
        parsed_skips: list[int | str] = []
        if self.skip_rules.strip():
            for item in self.skip_rules.split(","):
                cleaned = item.strip()
                if cleaned.isdigit():
                    parsed_skips.append(int(cleaned))
                elif cleaned:
                    parsed_skips.append(cleaned)

        return {
            "version": 1,
            "scope": self.scope,
            "write_mode": self.write_mode,
            "profile": {
                "level": self.profile_level,
                "skip_rules": parsed_skips,
                "description": f"Configured via GUI with {self.profile_level} profile.",
            },
            "tools": dict(self.tools),
            "targets": dict(self.targets),
            "mcp": {"enabled": self.mcp_enabled, "server_name": self.mcp_server_name},
            "skills": {"enabled": self.skills_enabled, "bundle": self.skill_bundle},
            "hooks": {"git_pre_commit": self.git_hook_enabled, "command": self.git_hook_command},
        }

    def load_from_config_dict(self, cfg: dict[str, Any]) -> None:
        if "scope" in cfg:
            self.scope = str(cfg["scope"])
        if "write_mode" in cfg:
            self.write_mode = str(cfg["write_mode"])
        prof = cfg.get("profile", {})
        if isinstance(prof, dict):
            self.profile_level = str(prof.get("level", "strict"))
            skips = prof.get("skip_rules", [])
            if isinstance(skips, list):
                self.skip_rules = ", ".join(str(rule_num) for rule_num in skips)
            elif isinstance(skips, str):
                self.skip_rules = skips
        elif isinstance(prof, str):
            self.profile_level = prof

        for section_name, attr_name in (("tools", "tools"), ("targets", "targets")):
            section = cfg.get(section_name, {})
            if isinstance(section, dict):
                target_map = getattr(self, attr_name)
                for key_name, flag in section.items():
                    target_map[key_name.lower()] = bool(flag)

        mcp_sec = cfg.get("mcp", {})
        if isinstance(mcp_sec, dict):
            self.mcp_enabled = bool(mcp_sec.get("enabled", True))
            self.mcp_server_name = str(mcp_sec.get("server_name", "ai-dev-tools"))

        skills_sec = cfg.get("skills", {})
        if isinstance(skills_sec, dict):
            self.skills_enabled = bool(skills_sec.get("enabled", True))
            self.skill_bundle = str(skills_sec.get("bundle", "all"))

        hooks_sec = cfg.get("hooks", {})
        if isinstance(hooks_sec, dict):
            self.git_hook_enabled = bool(hooks_sec.get("git_pre_commit", True))
            self.git_hook_command = str(
                hooks_sec.get("command", "uv run --no-project python scripts/claudemd_linter.py . --diff")
            )

    def load_preset(self, preset_name: str) -> None:
        preset_file = REPO_ROOT / "configs" / f"{preset_name}.yaml"
        if preset_file.is_file():
            self.load_from_config_dict(load_yaml_file(preset_file))

    def calculate_plan(self) -> ConfigExecutionPlan:
        return build_plan_from_config(self.to_config_dict(), Path(self.workspace).resolve())

    def auto_detect(self) -> dict[str, str]:
        detection = detect_workspace_integrations(Path(self.workspace).resolve())
        detected_names = set(detection["detected_tools"])
        for tool_name in self.tools:
            self.tools[tool_name] = tool_name in detected_names
        return detection["tool_reasons"]

    def to_state_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    def update_from_state_dict(self, data: dict[str, Any]) -> None:
        if "workspace" in data:
            self.workspace = str(data["workspace"])
        if "scope" in data:
            self.scope = str(data["scope"])
        if "write_mode" in data:
            self.write_mode = str(data["write_mode"])
        if "profile_level" in data:
            self.profile_level = str(data["profile_level"])
        if "skip_rules" in data:
            self.skip_rules = str(data["skip_rules"])
        if isinstance(data.get("tools"), dict):
            for key_name, flag in data["tools"].items():
                self.tools[str(key_name)] = bool(flag)
        if isinstance(data.get("targets"), dict):
            for key_name, flag in data["targets"].items():
                self.targets[str(key_name)] = bool(flag)
        if "mcp_enabled" in data:
            self.mcp_enabled = bool(data["mcp_enabled"])
        if "mcp_server_name" in data:
            self.mcp_server_name = str(data["mcp_server_name"] or "ai-dev-tools")
        if "skills_enabled" in data:
            self.skills_enabled = bool(data["skills_enabled"])
        if "skill_bundle" in data:
            self.skill_bundle = str(data["skill_bundle"] or "all")
        if "git_hook_enabled" in data:
            self.git_hook_enabled = bool(data["git_hook_enabled"])
        if "git_pre_push_enabled" in data:
            self.git_pre_push_enabled = bool(data["git_pre_push_enabled"])
        if "git_hook_command" in data:
            self.git_hook_command = str(data["git_hook_command"])


class SetupGuiServer:
    """Thread-safe local HTTP server backing the WebView Setup UI."""

    def __init__(self, model: SetupGuiModel | None = None) -> None:
        self.model = model or SetupGuiModel()
        self.shutdown_event = threading.Event()
        self.last_heartbeat = time.monotonic()
        self._server = self._build_server()

    def _build_server(self) -> ThreadingHTTPServer:
        parent = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format_str: str, *args: Any) -> None:
                _ = format_str, args

            def _send(self, code: int, body: bytes, content_type: str) -> None:
                self.send_response(code)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def _send_json(self, code: int, payload: dict[str, Any]) -> None:
                self._send(code, json.dumps(payload).encode("utf-8"), "application/json; charset=utf-8")

            def _read_json(self) -> dict[str, Any]:
                length = int(self.headers.get("Content-Length", "0") or "0")
                raw = self.rfile.read(length) if length > 0 else b"{}"
                return json.loads(raw.decode("utf-8") or "{}")

            def do_GET(self) -> None:
                scripts_dir = REPO_ROOT / "scripts"
                assets_dir = REPO_ROOT / "assets"
                if self.path in ("/", "/index.html"):
                    html_file = scripts_dir / "setup_gui_ui.html"
                    self._send(200, html_file.read_bytes(), "text/html; charset=utf-8")
                    return
                if self.path == "/setup_gui_theme.css":
                    css_file = scripts_dir / "setup_gui_theme.css"
                    self._send(200, css_file.read_bytes(), "text/css; charset=utf-8")
                    return
                if self.path == "/assets/icon.png" and (assets_dir / "icon.png").is_file():
                    self._send(200, (assets_dir / "icon.png").read_bytes(), "image/png")
                    return
                if self.path == "/api/state":
                    self._send_json(200, {"ok": True, "state": parent.model.to_state_dict()})
                    return
                self._send_json(404, {"ok": False, "error": "Not found"})

            def do_POST(self) -> None:
                parent.last_heartbeat = time.monotonic()
                if self.path == "/api/heartbeat":
                    self._send_json(200, {"ok": True})
                    return
                if self.path == "/api/shutdown":
                    parent.shutdown_event.set()
                    self._send_json(200, {"ok": True})
                    return
                data = self._read_json()
                if self.path == "/api/preset":
                    if isinstance(data.get("state"), dict):
                        parent.model.update_from_state_dict(data["state"])
                    parent.model.load_preset(str(data.get("name", "strict")))
                    self._send_json(200, {"ok": True, "state": parent.model.to_state_dict()})
                    return
                parent.model.update_from_state_dict(data)
                if self.path == "/api/detect":
                    reasons = parent.model.auto_detect()
                    summary = ", ".join(reasons.keys()) if reasons else "No existing assistants detected"
                    self._send_json(200, {"ok": True, "state": parent.model.to_state_dict(), "summary": summary})
                    return
                if self.path == "/api/preview":
                    plan = parent.model.calculate_plan()
                    self._send_json(200, {"ok": True, "preview": format_plan_preview(plan, show_diff=True)})
                    return
                if self.path == "/api/apply":
                    plan = parent.model.calculate_plan()
                    successes, errors = execute_plan(plan, dry_run=False)
                    if parent.model.git_pre_push_enabled:
                        install_hook(Path(parent.model.workspace).resolve(), action="append", hook_type="pre-push")
                    self._send_json(200, {"ok": errors == 0, "message": f"Applied {successes} item(s), {errors} error(s)."})
                    return
                if self.path == "/api/uninstall":
                    ws_path = Path(parent.model.workspace).resolve()
                    successes, errors = uninstall_configuration(ws_path, restore_backups=True, dry_run=False)
                    uninstall_hook(ws_path, hook_type="pre-push")
                    self._send_json(200, {"ok": errors == 0, "message": f"Uninstalled {successes} item(s), {errors} error(s)."})
                    return
                self._send_json(404, {"ok": False, "error": "Unknown API endpoint"})

        return ThreadingHTTPServer(("127.0.0.1", 0), Handler)

    @property
    def url(self) -> str:
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}/"

    def start(self) -> threading.Thread:
        thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        thread.start()
        return thread

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()


def _install_exception_hook() -> None:
    def _log_exc(exc_type: type[BaseException], exc_val: BaseException, exc_tb: Any) -> None:
        _ = exc_tb
        sys.stderr.write(f"Unhandled GUI exception ({exc_type.__name__}): {exc_val}\n")

    sys.excepthook = _log_exc


def run_self_test() -> int:
    """Verify local server startup, HTML rendering, and preview API cleanly."""
    srv = SetupGuiServer()
    srv.start()
    try:
        with urllib.request.urlopen(srv.url, timeout=5.0) as html_resp:
            html_body = html_resp.read().decode("utf-8")
            if html_resp.status != 200 or "AI-Dev-Tools Setup Assistant" not in html_body:
                return 1
        with urllib.request.urlopen(f"{srv.url}api/state", timeout=5.0) as state_resp:
            state_json = json.loads(state_resp.read().decode("utf-8"))
            if not state_json.get("ok"):
                return 1
        req = urllib.request.Request(
            f"{srv.url}api/preview",
            data=json.dumps(srv.model.to_state_dict()).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5.0) as prev_resp:
            prev_json = json.loads(prev_resp.read().decode("utf-8"))
            if not prev_json.get("ok"):
                return 1
        return 0
    finally:
        srv.stop()


def capture_gui_screenshot(out_png: Path) -> int:
    """Render WebView Setup Assistant headlessly and capture PNG screenshot."""
    srv = SetupGuiServer(SetupGuiModel(workspace="~/projects/my-app"))
    srv.start()
    try:
        success = capture_with_browser(srv.url, out_png, width=1220, height=820, virtual_budget_ms=1500)
        return 0 if success else 1
    finally:
        srv.stop()


def main() -> int:
    _install_exception_hook()
    parser = argparse.ArgumentParser(description="Launch unified WebView AI-Dev-Tools Setup Assistant.")
    parser.add_argument("--self-test", action="store_true", help="Run headless self-test and exit")
    parser.add_argument("--screenshot", type=Path, default=None, help="Capture GUI PNG screenshot to path and exit")
    args = parser.parse_args()

    if args.self_test:
        return run_self_test()
    if args.screenshot is not None:
        return capture_gui_screenshot(args.screenshot)

    srv = SetupGuiServer()
    srv.start()
    browser = find_headless_browser()
    try:
        if browser:
            profile_dir = Path(os.environ.get("TEMP", "/tmp")) / "adt-setup-webview"
            profile_dir.mkdir(parents=True, exist_ok=True)
            proc = subprocess.Popen(
                [browser, f"--app={srv.url}", f"--user-data-dir={profile_dir}", "--window-size=1180,820"]
            )
            while proc.poll() is None and not srv.shutdown_event.is_set():
                time.sleep(0.3)
        else:
            webbrowser.open(srv.url)
            while not srv.shutdown_event.is_set() and (time.monotonic() - srv.last_heartbeat) < 20.0:
                time.sleep(0.5)
    finally:
        srv.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
