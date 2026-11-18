"""AST code graph and blast-radius analyzer for impact assessment.
Maps symbol definitions, calls, and imports to calculate change risk.
"""

import ast
import json
import sys
from pathlib import Path


def parse_file_symbols(file_path: Path) -> tuple[set[str], set[str], set[str]]:
    """Extract defined symbols, imported modules, and call targets from a Python file."""
    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(file_path))
    except (UnicodeDecodeError, OSError, SyntaxError):
        return set(), set(), set()

    defined_symbols: set[str] = set()
    imports: set[str] = set()
    calls: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            defined_symbols.add(node.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".")[0])
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)

    return defined_symbols, imports, calls


def build_code_graph(root_dir: Path) -> dict[str, dict]:
    """Scan directory tree and construct file-level dependency and call graph."""
    graph: dict[str, dict] = {}

    for file_path in root_dir.rglob("*.py"):
        if any(ignored in file_path.parts for ignored in (".venv", "venv", "__pycache__", ".git")):
            continue
        rel_str = str(file_path.relative_to(root_dir)).replace("\\", "/")
        defs, imps, cls = parse_file_symbols(file_path)
        graph[rel_str] = {
            "path": rel_str,
            "is_test": "test" in rel_str.lower() or "tests/" in rel_str.lower(),
            "definitions": sorted(defs),
            "imports": sorted(imps),
            "calls": sorted(cls),
            "dependents": [],
        }

    for file_name, file_info in graph.items():
        stem = Path(file_name).stem
        for other_name, other_info in graph.items():
            if file_name == other_name:
                continue
            if stem in other_info["imports"] or any(d in other_info["calls"] for d in file_info["definitions"]):
                file_info["dependents"].append(other_name)

    return graph


def calculate_risk(dependents_count: int, has_tests: bool) -> str:
    """Calculate blast-radius risk level based on dependent count and test coverage."""
    if dependents_count > 6 or not has_tests:
        return "High"
    if dependents_count > 2:
        return "Medium"
    return "Low"


def analyze_blast_radius(root_dir: Path, target_path: Path) -> dict:
    """Calculate blast radius and affected tests for a modified file."""
    graph = build_code_graph(root_dir)
    target_rel = str(target_path.relative_to(root_dir) if target_path.is_absolute() else target_path).replace("\\", "/")

    file_data = graph.get(target_rel, {
        "path": target_rel,
        "dependents": [],
        "definitions": [],
        "is_test": False,
    })

    direct_dependents = sorted(file_data.get("dependents", []))
    affected_tests = [dep for dep in direct_dependents if graph.get(dep, {}).get("is_test", False)]

    # Transitive expansion
    transitive: set[str] = set(direct_dependents)
    for dep in direct_dependents:
        transitive.update(graph.get(dep, {}).get("dependents", []))

    all_tests = [f for f in transitive if graph.get(f, {}).get("is_test", False)]
    risk = calculate_risk(len(transitive), len(all_tests) > 0)

    return {
        "target": target_rel,
        "direct_dependents": direct_dependents,
        "transitive_dependents": sorted(transitive),
        "affectedTests": sorted(set(all_tests)),
        "risk": risk,
    }


def main() -> int:
    """CLI entry point for code review graph inspection."""
    if len(sys.argv) < 2:
        sys.stdout.write("Usage: code_review_graph.py <root_or_file>\n")
        return 1

    target = Path(sys.argv[1]).resolve()
    if target.is_file():
        root = target.parent
        report = analyze_blast_radius(root, target)
        sys.stdout.write(json.dumps(report, indent=2) + "\n")
    else:
        graph = build_code_graph(target)
        sys.stdout.write(f"Scanned {len(graph)} files in {target.name}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
