"""CLI tool for UI test harness initialization, manifest generation, and audit verification."""

import argparse
import json
import shutil
import sys
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
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
