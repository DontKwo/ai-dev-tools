"""Context Mode runtime: sandboxed command execution, SQLite FTS5 indexing, and compaction continuity."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from token_compressor import compress_command_output  # noqa: 12

DEFAULT_DB_NAME = ".ai_context_index.sqlite"
INDEXABLE_SUFFIXES = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".rs", ".kt", ".java", ".cs", ".ps1",
    ".md", ".txt", ".yaml", ".yml", ".toml", ".json", ".html", ".css", ".sh",
}
SKIP_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build",
    "target", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".gradle",
}


def _open_db(root_dir: Path, db_path: Path | None = None) -> sqlite3.Connection:
    """Open or initialize SQLite database containing FTS5 index and session events."""
    resolved_db = (db_path or (root_dir / DEFAULT_DB_NAME)).resolve()
    resolved_db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(resolved_db))
    conn.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS docs_fts "
        "USING fts5(rel_path, title, body, tokenize='porter unicode61')"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS files_meta "
        "(rel_path TEXT PRIMARY KEY, mtime REAL NOT NULL, size INTEGER NOT NULL)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS session_events "
        "(id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, event_type TEXT NOT NULL, "
        "detail TEXT NOT NULL, files_json TEXT NOT NULL)"
    )
    conn.commit()
    return conn


def ctx_execute(
    cmd: list[str],
    cwd: Path | None = None,
    max_lines: int = 80,
    timeout_sec: int = 60,
) -> dict[str, Any]:
    """Run subprocess without shell and distill verbose output into a bounded summary."""
    if not cmd:
        return {"exit_code": 1, "summary": "No command provided.", "original_chars": 0, "compressed_chars": 20, "savings_pct": 0.0}

    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_sec,
        check=False,
    )
    raw_combined = proc.stdout + (("\n" + proc.stderr) if proc.stderr else "")
    compressed_text, savings_ratio = compress_command_output(" ".join(cmd), raw_combined)
    lines = compressed_text.splitlines()
    if len(lines) > max_lines and max_lines >= 10:
        head_count = max_lines // 2
        tail_count = max_lines - head_count
        omitted = len(lines) - max_lines
        lines = lines[:head_count] + [f"... [{omitted} lines omitted by ctx_execute] ..."] + lines[-tail_count:]
    summary = "\n".join(lines)
    return {
        "exit_code": proc.returncode,
        "summary": summary,
        "original_chars": len(raw_combined),
        "compressed_chars": len(summary),
        "savings_pct": round(savings_ratio * 100.0, 1),
    }


def index_workspace(root_dir: Path, db_path: Path | None = None) -> dict[str, int]:
    """Index repository text files incrementally into SQLite FTS5 for fast snippet retrieval."""
    resolved_root = root_dir.resolve()
    conn = _open_db(resolved_root, db_path=db_path)
    try:
        existing_meta = {
            row[0]: float(row[1])
            for row in conn.execute("SELECT rel_path, mtime FROM files_meta").fetchall()
        }
        seen_paths: set[str] = set()
        indexed_count = 0
        skipped_count = 0

        for candidate in resolved_root.rglob("*"):
            if not candidate.is_file() or candidate.suffix.lower() not in INDEXABLE_SUFFIXES:
                continue
            if any(part in SKIP_DIRS for part in candidate.parts):
                continue
            stat_info = candidate.stat()
            if stat_info.st_size > 256_000:
                continue
            rel_path = candidate.relative_to(resolved_root).as_posix()
            seen_paths.add(rel_path)
            if rel_path in existing_meta and abs(existing_meta[rel_path] - stat_info.st_mtime) < 1e-3:
                skipped_count += 1
                continue
            text = candidate.read_text(encoding="utf-8", errors="replace")
            first_line = text.splitlines()[0].strip() if text.splitlines() else candidate.name
            conn.execute("DELETE FROM docs_fts WHERE rel_path = ?", (rel_path,))
            conn.execute(
                "INSERT INTO docs_fts (rel_path, title, body) VALUES (?, ?, ?)",
                (rel_path, first_line[:120], text),
            )
            conn.execute(
                "INSERT OR REPLACE INTO files_meta (rel_path, mtime, size) VALUES (?, ?, ?)",
                (rel_path, float(stat_info.st_mtime), int(stat_info.st_size)),
            )
            indexed_count += 1

        stale_paths = set(existing_meta.keys()) - seen_paths
        for stale in stale_paths:
            conn.execute("DELETE FROM docs_fts WHERE rel_path = ?", (stale,))
            conn.execute("DELETE FROM files_meta WHERE rel_path = ?", (stale,))
        conn.commit()
        return {"indexed": indexed_count, "unchanged": skipped_count, "removed": len(stale_paths)}
    finally:
        conn.close()


def _sanitize_fts_query(query_text: str) -> str:
    """Convert raw user query text into safe FTS5 prefix search tokens."""
    tokens = re.findall(r"[A-Za-z0-9_]+", query_text)
    return " ".join(f'"{tok}"' for tok in tokens)


def search_index(
    query: str,
    root_dir: Path,
    limit: int = 8,
    db_path: Path | None = None,
    auto_index: bool = True,
) -> list[dict[str, Any]]:
    """Query local FTS5 index with BM25 ranking and return compact matched snippets."""
    resolved_root = root_dir.resolve()
    resolved_db = (db_path or (resolved_root / DEFAULT_DB_NAME)).resolve()
    if auto_index and not resolved_db.is_file():
        index_workspace(resolved_root, db_path=resolved_db)

    fts_query = _sanitize_fts_query(query)
    if not fts_query:
        return []

    conn = _open_db(resolved_root, db_path=resolved_db)
    try:
        rows = conn.execute(
            "SELECT rel_path, title, snippet(docs_fts, 2, '>>>', '<<<', '...', 20), bm25(docs_fts) "
            "FROM docs_fts WHERE docs_fts MATCH ? ORDER BY bm25(docs_fts) LIMIT ?",
            (fts_query, max(1, limit)),
        ).fetchall()
        return [
            {"path": row[0], "title": row[1], "snippet": row[2], "score": round(float(row[3]), 4)}
            for row in rows
        ]
    finally:
        conn.close()


def record_session_event(
    root_dir: Path,
    event_type: str,
    detail: str,
    files: list[str] | None = None,
    db_path: Path | None = None,
) -> None:
    """Persist compact session continuity events for post-compaction recovery."""
    resolved_root = root_dir.resolve()
    conn = _open_db(resolved_root, db_path=db_path)
    try:
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        conn.execute(
            "INSERT INTO session_events (ts, event_type, detail, files_json) VALUES (?, ?, ?, ?)",
            (now_iso, event_type, detail, json.dumps(files or [])),
        )
        conn.commit()
    finally:
        conn.close()


def build_continuity_summary(
    root_dir: Path,
    limit: int = 20,
    db_path: Path | None = None,
) -> str:
    """Emit concise session recovery markdown combining recent events and live git state."""
    resolved_root = root_dir.resolve()
    conn = _open_db(resolved_root, db_path=db_path)
    try:
        rows = conn.execute(
            "SELECT ts, event_type, detail, files_json FROM session_events ORDER BY id DESC LIMIT ?",
            (max(1, limit),),
        ).fetchall()
    finally:
        conn.close()

    git_res = subprocess.run(
        ["git", "status", "-sb"],
        cwd=str(resolved_root),
        capture_output=True,
        text=True,
        check=False,
    )
    lines = [f"# Session Continuity Summary: {resolved_root.name}"]
    if git_res.returncode == 0 and git_res.stdout.strip():
        lines.append("## Git State")
        lines.extend(git_res.stdout.strip().splitlines()[:15])
    lines.append("## Recent Events")
    if not rows:
        lines.append("- No recorded session events yet.")
    else:
        for ts_val, ev_type, detail, files_raw in reversed(rows):
            file_list = json.loads(files_raw) if files_raw else []
            files_suffix = f" ({', '.join(file_list)})" if file_list else ""
            lines.append(f"- [{ts_val}] `{ev_type}`: {detail}{files_suffix}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for Context Mode sandbox execution, FTS5 search, and session logs."""
    parser = argparse.ArgumentParser(description="Context Mode token-saving workspace utility.")
    sub = parser.add_subparsers(dest="cmd")

    exec_p = sub.add_parser("exec", help="Execute command with compressed bounded output")
    exec_p.add_argument("--cwd", type=Path, default=Path.cwd())
    exec_p.add_argument("--max-lines", type=int, default=80)
    exec_p.add_argument("command", nargs=argparse.REMAINDER)

    idx_p = sub.add_parser("index", help="Index repository files into SQLite FTS5")
    idx_p.add_argument("target", nargs="?", type=Path, default=Path.cwd())

    search_p = sub.add_parser("search", help="Search SQLite FTS5 index with BM25 ranking")
    search_p.add_argument("query", help="Search keywords")
    search_p.add_argument("target", nargs="?", type=Path, default=Path.cwd())
    search_p.add_argument("--limit", type=int, default=8)
    search_p.add_argument("--reindex", action="store_true")

    rec_p = sub.add_parser("record", help="Record compaction continuity event")
    rec_p.add_argument("event_type", help="Event category (edit, test, commit, note)")
    rec_p.add_argument("detail", help="Short summary of event")
    rec_p.add_argument("--target", type=Path, default=Path.cwd())
    rec_p.add_argument("--files", nargs="*", default=[])

    sum_p = sub.add_parser("summary", help="Print session continuity summary")
    sum_p.add_argument("target", nargs="?", type=Path, default=Path.cwd())
    sum_p.add_argument("--limit", type=int, default=20)

    args = parser.parse_args(argv)
    if args.cmd == "exec":
        cmd_parts = [part for part in args.command if part != "--"]
        payload = ctx_execute(cmd_parts, cwd=args.cwd, max_lines=args.max_lines)
        sys.stdout.write(json.dumps(payload, indent=2) + "\n")
        return int(payload["exit_code"])
    if args.cmd == "index":
        stats = index_workspace(args.target)
        sys.stdout.write(json.dumps(stats, indent=2) + "\n")
        return 0
    if args.cmd == "search":
        if args.reindex:
            index_workspace(args.target)
        hits = search_index(args.query, args.target, limit=args.limit)
        sys.stdout.write(json.dumps(hits, indent=2) + "\n")
        return 0
    if args.cmd == "record":
        record_session_event(args.target, args.event_type, args.detail, files=args.files)
        sys.stdout.write("Recorded session continuity event.\n")
        return 0
    if args.cmd == "summary":
        sys.stdout.write(build_continuity_summary(args.target, limit=args.limit) + "\n")
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
