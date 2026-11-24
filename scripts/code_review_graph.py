"""AST code graph and blast-radius analyzer for impact assessment.
Maps symbol definitions, calls, and imports to calculate change risk and SQLite cache.
"""

from __future__ import annotations

import argparse
import ast
from collections import deque
import json
from pathlib import Path
import re
import sqlite3
import sys

IGNORED_GRAPH_DIRS = {".venv", "venv", "__pycache__", ".git", "node_modules", "dist", "build", "target"}
MULTI_LANG_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".rs", ".kt", ".cs", ".ps1"}
GENERIC_CALL_NAMES = {
    "main", "run", "get", "set", "init", "setup", "parse", "load", "save",
    "close", "open", "read", "write", "update", "render", "format", "check",
    "test", "helper", "start", "stop", "build", "create", "delete",
}


def find_repo_root(start_path: Path) -> Path:
    """Walk upward from start_path to locate repository root markers cleanly."""
    candidate = start_path.resolve() if start_path.is_dir() else start_path.resolve().parent
    for parent in [candidate] + list(candidate.parents):
        if any((parent / marker).exists() for marker in (".git", "pyproject.toml", "package.json", "Cargo.toml")):
            return parent
    return candidate


def parse_file_symbols(file_path: Path) -> tuple[set[str], set[str], set[str]]:
    """Extract defined symbols, imported modules, and call targets from source files."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except (UnicodeDecodeError, OSError):
        return set(), set(), set()

    defined_symbols: set[str] = set()
    imports: set[str] = set()
    calls: set[str] = set()

    if file_path.suffix.lower() == ".py":
        try:
            tree = ast.parse(content, filename=str(file_path))
        except SyntaxError:
            return set(), set(), set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                defined_symbols.add(node.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split(".")[0])
                    imports.add(alias.name.split(".")[-1])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split(".")[0])
                    imports.add(node.module.split(".")[-1])
                for alias in node.names:
                    imports.add(alias.name)
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    calls.add(node.func.attr)
        return defined_symbols, imports, calls

    # Regex extraction for TS/JS, Rust, Kotlin, C#, and PowerShell modules.
    for match in re.finditer(r"\b(?:function|class|fn|fun|def|interface|struct)\s+([A-Za-z_][A-Za-z0-9_]*)", content):
        defined_symbols.add(match.group(1))
    for match in re.finditer(r"(?:from\s+['\"]([^'\"]+)['\"]|use\s+([A-Za-z0-9_:]+)|import\s+([A-Za-z0-9_.]+))", content):
        token = match.group(1) or match.group(2) or match.group(3)
        if token:
            imports.add(token.split("/")[-1].split("::")[-1].split(".")[0].removesuffix(".js").removesuffix(".ts"))
    for match in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", content):
        calls.add(match.group(1))
    return defined_symbols, imports, calls


def build_code_graph(root_dir: Path, multi_language: bool = False) -> dict[str, dict]:
    """Scan directory tree and construct file-level dependency and call graph."""
    graph: dict[str, dict] = {}
    allowed_suffixes = MULTI_LANG_SUFFIXES if multi_language else {".py"}

    for file_path in root_dir.rglob("*"):
        if not file_path.is_file() or file_path.suffix.lower() not in allowed_suffixes:
            continue
        if any(ignored in file_path.parts for ignored in IGNORED_GRAPH_DIRS):
            continue
        rel_str = str(file_path.relative_to(root_dir)).replace("\\", "/")
        defs, imps, call_names = parse_file_symbols(file_path)
        graph[rel_str] = {
            "path": rel_str,
            "is_test": "test" in rel_str.lower() or "tests/" in rel_str.lower(),
            "definitions": sorted(defs),
            "imports": sorted(imps),
            "calls": sorted(call_names),
            "dependents": [],
        }

    for file_name, file_info in graph.items():
        stem = Path(file_name).stem
        distinct_defs = [sym for sym in file_info["definitions"] if sym not in GENERIC_CALL_NAMES]
        for other_name, other_info in graph.items():
            if file_name == other_name:
                continue
            imported_match = stem in other_info["imports"]
            symbol_match = any(sym in other_info["calls"] for sym in distinct_defs)
            if imported_match or symbol_match:
                file_info["dependents"].append(other_name)

    return graph


def save_graph_sqlite(graph: dict[str, dict], db_path: Path) -> None:
    """Persist code review graph tables into a local SQLite database."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("DROP TABLE IF EXISTS files")
        conn.execute("DROP TABLE IF EXISTS edges")
        conn.execute("CREATE TABLE files (path TEXT PRIMARY KEY, is_test INTEGER, definitions_json TEXT)")
        conn.execute("CREATE TABLE edges (source TEXT, dependent TEXT)")
        for file_path, info in graph.items():
            conn.execute(
                "INSERT INTO files (path, is_test, definitions_json) VALUES (?, ?, ?)",
                (file_path, 1 if info.get("is_test") else 0, json.dumps(info.get("definitions", []))),
            )
            for dep_path in info.get("dependents", []):
                conn.execute("INSERT INTO edges (source, dependent) VALUES (?, ?)", (file_path, dep_path))
        conn.commit()
    finally:
        conn.close()


def calculate_risk(dependents_count: int, has_tests: bool) -> str:
    """Calculate blast-radius risk level based on dependent count and test coverage."""
    if dependents_count > 6 or not has_tests:
        return "High"
    if dependents_count > 2:
        return "Medium"
    return "Low"


def analyze_blast_radius(root_dir: Path, target_path: Path, multi_language: bool = False) -> dict:
    """Calculate full transitive blast radius and affected tests for a modified file."""
    resolved_root = root_dir.resolve()
    resolved_target = target_path.resolve() if target_path.is_absolute() else (resolved_root / target_path).resolve()
    graph = build_code_graph(resolved_root, multi_language=multi_language)
    try:
        target_rel = resolved_target.relative_to(resolved_root).as_posix()
    except ValueError:
        target_rel = str(target_path).replace("\\", "/")

    file_data = graph.get(target_rel, {
        "path": target_rel,
        "dependents": [],
        "definitions": [],
        "is_test": False,
    })

    direct_dependents = sorted(file_data.get("dependents", []))
    transitive: set[str] = set()
    queue: deque[str] = deque(direct_dependents)
    while queue:
        current = queue.popleft()
        if current in transitive or current == target_rel:
            continue
        transitive.add(current)
        for next_dep in graph.get(current, {}).get("dependents", []):
            if next_dep not in transitive:
                queue.append(next_dep)

    all_tests = [path for path in transitive if graph.get(path, {}).get("is_test", False)]
    risk = calculate_risk(len(transitive), len(all_tests) > 0)
    return {
        "target": target_rel,
        "direct_dependents": direct_dependents,
        "transitive_dependents": sorted(transitive),
        "affectedTests": sorted(set(all_tests)),
        "risk": risk,
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for code review graph inspection and optional SQLite caching."""
    parser = argparse.ArgumentParser(description="Build AST/symbol code graph and blast-radius report.")
    parser.add_argument("target", nargs="?", default=".", help="File or repository directory to analyze")
    parser.add_argument("--multi-lang", action="store_true", help="Include TS/JS, Rust, Kotlin, C#, and PowerShell files")
    parser.add_argument("--db", type=Path, default=None, help="Optional SQLite output path for persisted graph")
    args = parser.parse_args(argv)

    target_path = Path(args.target).resolve()
    if target_path.is_file():
        repo_root = find_repo_root(target_path)
        report = analyze_blast_radius(repo_root, target_path, multi_language=args.multi_lang)
        sys.stdout.write(json.dumps(report, indent=2) + "\n")
        return 0

    graph = build_code_graph(target_path, multi_language=args.multi_lang)
    if args.db is not None:
        save_graph_sqlite(graph, args.db.resolve())
    sys.stdout.write(f"Scanned {len(graph)} files in {target_path.name}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
