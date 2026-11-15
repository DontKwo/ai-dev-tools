"""Comprehensive test suite for multi-framework UI quality rules and audit engine."""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.claudemd_linter import collect_git_diff_files, detect_repo_hygiene_issues, scan_file
from scripts.ui_adapters import detect_adapters
from scripts.ui_adapters.tauri import TauriAdapter
from scripts.ui_adapters.android import AndroidAdapter
from scripts.ui_adapters.dotnet import DotNetAdapter
from scripts.ui_adapters.flutter import FlutterAdapter
from scripts.ui_adapters.ios import IosAdapter
from scripts.ui_adapters.kivy import KivyAdapter
from scripts.ui_adapters.pyqt import PyQtAdapter
from scripts.ui_adapters.textual import TextualAdapter
from scripts.ui_adapters.tkinter_adapter import TkinterAdapter
from scripts.ui_adapters.web import WebAdapter
from scripts.ui_adapters.wxpython import WxPythonAdapter
from scripts.ui_combinations import generate_required_cases, verify_screen_combinations
from scripts.ui_config import UiConfig, load_ui_config
from scripts.ui_engine import build_manifest, evaluate_evidence_rules, evaluate_static_rules
from scripts.ui_evidence import load_ui_evidence
from scripts.ui_layout import (
    Rect,
    check_element_overlaps,
    check_parent_clipping,
    check_target_size,
    check_viewport_overflow,
)
from scripts.ui_models import (
    CaseRecord,
    ControlRecord,
    InteractionRecord,
    LayoutFindingRecord,
    ScreenRecord,
    UiEvidence,
    UiManifest,
)


class TestUiQuality(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_ui_config_defaults(self) -> None:
        cfg = UiConfig()
        self.assertTrue(cfg.matches_id_pattern("main_window.save_button"))
        self.assertFalse(cfg.matches_id_pattern("INVALID ID!"))
        self.assertFalse(cfg.is_waived("any.id"))

    def test_ui_config_load_custom(self) -> None:
        toml_path = self.root / ".uilint.toml"
        toml_path.write_text(
            '[project]\nframeworks = ["pyqt6"]\nid_pattern = \'^[a-z_]+$\'\n\n'
            '[waivers]\n"btn_waived" = "legacy exempt"\n',
            encoding="utf-8",
        )
        cfg = load_ui_config(self.root)
        self.assertEqual(cfg.frameworks, ["pyqt6"])
        self.assertTrue(cfg.is_waived("btn_waived"))
        self.assertTrue(cfg.matches_id_pattern("valid_id"))
        self.assertFalse(cfg.matches_id_pattern("Invalid-Id"))

    def test_pyqt_adapter_extraction(self) -> None:
        adapter = PyQtAdapter()
        py_code = (
            "from PyQt6.QtWidgets import QPushButton, QDialog\n"
            "class SettingsDialog(QDialog):\n"
            "    def __init__(self):\n"
            "        self.btn_save = QPushButton('Save')\n"
        )
        facts = adapter.extract(self.root / "dialog.py", py_code)
        self.assertEqual(len(facts.screens), 1)
        self.assertEqual(len(facts.controls), 1)
        self.assertEqual(facts.controls[0].id, "btn_save")
        self.assertEqual(facts.controls[0].kind, "button")

    def test_web_adapter_extraction(self) -> None:
        adapter = WebAdapter()
        html = '<button data-testid="settings.submit_btn" title="Submit">Send</button>'
        facts = adapter.extract(self.root / "index.html", html)
        self.assertEqual(len(facts.controls), 1)
        self.assertEqual(facts.controls[0].id, "settings.submit_btn")
        self.assertTrue(facts.controls[0].can_disable)

    def test_android_adapter_extraction(self) -> None:
        adapter = AndroidAdapter()
        xml = '<Button xmlns:android="http://schemas.android.com/apk/res/android" android:id="@+id/btn_action" />'
        facts = adapter.extract(self.root / "activity_main.xml", xml)
        self.assertEqual(len(facts.controls), 1)
        self.assertEqual(facts.controls[0].id, "btn_action")

    def test_flutter_adapter_extraction(self) -> None:
        adapter = FlutterAdapter()
        dart = "ElevatedButton(key: Key('home.refresh_btn'), onPressed: () {});"
        facts = adapter.extract(self.root / "view.dart", dart)
        self.assertEqual(len(facts.controls), 1)
        self.assertEqual(facts.controls[0].id, "home.refresh_btn")

    def test_ios_adapter_extraction(self) -> None:
        adapter = IosAdapter()
        swift = 'let btn = UIButton()\nbtn.accessibilityIdentifier = "profile.edit"'
        facts = adapter.extract(self.root / "ProfileVC.swift", swift)
        self.assertEqual(len(facts.controls), 1)
        self.assertEqual(facts.controls[0].id, "profile.edit")

    def test_tkinter_wx_kivy_textual_dotnet_adapters(self) -> None:
        tk_facts = TkinterAdapter().extract(self.root / "app.py", "b = Button(root)")
        self.assertEqual(len(tk_facts.controls), 1)

        wx_facts = WxPythonAdapter().extract(self.root / "app.py", "btn = Button(self)")
        self.assertEqual(len(wx_facts.controls), 1)

        kv_facts = KivyAdapter().extract(self.root / "main.kv", "    id: submit_btn\n")
        self.assertEqual(len(kv_facts.controls), 1)

        txt_facts = TextualAdapter().extract(self.root / "tui.py", "from textual.widgets import Button\nyield Button('OK', id='ok_btn')")
        self.assertEqual(len(txt_facts.controls), 1)

        dn_facts = DotNetAdapter().extract(self.root / "win.xaml", '<Button x:Name="SaveBtn" />')
        self.assertEqual(len(dn_facts.controls), 1)

    def test_rule_46_stable_id(self) -> None:
        cfg = UiConfig()
        manifest = UiManifest(
            controls=[
                ControlRecord(
                    id="InvalidIdentifier!",
                    kind="button",
                    framework="pyqt",
                    screen="main",
                    file=str(self.root / "main.py"),
                    line=10,
                    source_hash="abc",
                )
            ]
        )
        violations = evaluate_static_rules(self.root, manifest, cfg)
        codes = [v[2] for v in violations]
        self.assertIn(46, codes)

    def test_rule_48_test_bypass_detection(self) -> None:
        cfg = UiConfig(ui_globs=["tests/ui/**"])
        test_dir = self.root / "tests" / "ui"
        test_dir.mkdir(parents=True)
        bad_test = test_dir / "test_screen.py"
        bad_test.write_text("def test_click():\n    btn.click()\n", encoding="utf-8")

        manifest = UiManifest()
        violations = evaluate_static_rules(self.root, manifest, cfg, files=[bad_test])
        codes = [v[2] for v in violations]
        self.assertIn(48, codes)

    def test_rule_49_test_assertion_requirement(self) -> None:
        cfg = UiConfig(ui_globs=["tests/ui/**"])
        test_dir = self.root / "tests" / "ui"
        test_dir.mkdir(parents=True)
        no_assert_test = test_dir / "test_no_assert.py"
        no_assert_test.write_text("def test_ui():\n    real_click(btn)\n    assert True\n", encoding="utf-8")

        manifest = UiManifest()
        violations = evaluate_static_rules(self.root, manifest, cfg, files=[no_assert_test])
        codes = [v[2] for v in violations]
        self.assertIn(49, codes)

    def test_rule_52_tooltip_registry_hygiene(self) -> None:
        cfg = UiConfig(tooltips_registry="tooltips.py")
        reg_file = self.root / "tooltips.py"
        reg_file.write_text('TOOLTIPS = {"orphan.button": "Save changes."}\n', encoding="utf-8")

        manifest = UiManifest()
        violations = evaluate_static_rules(self.root, manifest, cfg)
        codes = [v[2] for v in violations]
        self.assertIn(52, codes)

    def test_rule_54_layout_hazards(self) -> None:
        src_file = self.root / "window.py"
        src_file.write_text("from PyQt6.QtWidgets import QPushButton\nbtn.setFixedSize(100, 30)\n", encoding="utf-8")  # noqa: 54

        manifest = UiManifest()
        cfg = UiConfig()
        violations = evaluate_static_rules(self.root, manifest, cfg, files=[src_file])
        codes = [v[2] for v in violations]
        self.assertIn(54, codes)

    def test_rule_61_raw_exception(self) -> None:
        src_file = self.root / "err.py"
        src_file.write_text("from PyQt6.QtWidgets import QMessageBox\nQMessageBox.critical(self, 'Error', str(e))\n", encoding="utf-8")

        manifest = UiManifest()
        cfg = UiConfig()
        violations = evaluate_static_rules(self.root, manifest, cfg, files=[src_file])
        codes = [v[2] for v in violations]
        self.assertIn(61, codes)

    def test_rule_62_blocking_call_in_slot(self) -> None:
        src_file = self.root / "slot.py"
        src_file.write_text("from PyQt6.QtCore import pyqtSlot\ndef on_button_clicked():\n    time.sleep(1)\n", encoding="utf-8")

        manifest = UiManifest()
        cfg = UiConfig()
        violations = evaluate_static_rules(self.root, manifest, cfg, files=[src_file])
        codes = [v[2] for v in violations]
        self.assertIn(62, codes)

    def test_rule_67_destructive_action_unconfirmed(self) -> None:
        src_file = self.root / "action.py"
        src_file.write_text("from PyQt6.QtWidgets import QPushButton\ndelete_button = QPushButton('Delete Record')\n", encoding="utf-8")

        manifest = UiManifest()
        cfg = UiConfig()
        violations = evaluate_static_rules(self.root, manifest, cfg, files=[src_file])
        codes = [v[2] for v in violations]
        self.assertIn(67, codes)

    def test_rule_47_control_never_pressed(self) -> None:
        manifest = UiManifest(
            controls=[
                ControlRecord(
                    id="main.btn_save",
                    kind="button",
                    framework="pyqt",
                    screen="main",
                    file=str(self.root / "main.py"),
                    line=1,
                    source_hash="hash1",
                )
            ]
        )
        cfg = UiConfig()
        evidence = UiEvidence(run_id="run1", framework="pyqt", commit="c1", interactions=[])
        violations = evaluate_evidence_rules(self.root, manifest, evidence, cfg)
        codes = [v[2] for v in violations]
        self.assertIn(47, codes)

    def test_rule_47_missing_evidence_file(self) -> None:
        manifest = UiManifest(
            controls=[
                ControlRecord(
                    id="main.btn",
                    kind="button",
                    framework="web",
                    screen="main",
                    file=str(self.root / "app.js"),
                    line=1,
                    source_hash="h",
                )
            ]
        )
        cfg = UiConfig()
        violations = evaluate_evidence_rules(self.root, manifest, None, cfg)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0][2], 47)

    def test_rule_50_enabled_and_disabled_states(self) -> None:
        manifest = UiManifest(
            controls=[
                ControlRecord(
                    id="main.btn_toggle",
                    kind="button",
                    framework="pyqt",
                    screen="main",
                    file=str(self.root / "main.py"),
                    line=1,
                    source_hash="h1",
                    can_disable=True,
                )
            ]
        )
        cfg = UiConfig()
        # Only exercised enabled state
        evidence = UiEvidence(
            run_id="r1",
            framework="pyqt",
            commit="c1",
            interactions=[
                InteractionRecord(
                    control_id="main.btn_toggle",
                    input_kind="mouse",
                    trusted=True,
                    control_state="enabled",
                    test_node_id="test1",
                    sequence_number=1,
                )
            ],
        )
        violations = evaluate_evidence_rules(self.root, manifest, evidence, cfg)
        codes = [v[2] for v in violations]
        self.assertIn(50, codes)

    def test_rule_51_combinations(self) -> None:
        screen = ScreenRecord(id="main", kind="window", file="main.py", line=1)
        controls = [
            ControlRecord(id="btn1", kind="button", framework="pyqt", screen="main", file="main.py", line=1, source_hash="1"),
            ControlRecord(id="btn2", kind="button", framework="pyqt", screen="main", file="main.py", line=2, source_hash="2"),
        ]
        cases = generate_required_cases(screen, controls)
        # 2 buttons give 4 ordered pairs (A,A), (A,B), (B,A), (B,B) plus triples
        pair_cases = [c for c in cases if c["case_kind"] == "ordered_pair"]
        self.assertEqual(len(pair_cases), 4)

        # Incomplete evidence should flag Rule 51
        evidence = UiEvidence(run_id="r", framework="pyqt", commit="c", cases=[])
        manifest = UiManifest(controls=controls, screens=[screen])
        violations = evaluate_evidence_rules(self.root, manifest, evidence, UiConfig())
        codes = [v[2] for v in violations]
        self.assertIn(51, codes)

    def test_rule_53_layout_overlap(self) -> None:
        elems = [
            {"id": "b1", "x": 10.0, "y": 10.0, "width": 50.0, "height": 30.0},
            {"id": "b2", "x": 20.0, "y": 15.0, "width": 50.0, "height": 30.0},
        ]
        findings = check_element_overlaps(elems, tolerance_px=1.0)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].type, "overlap")

    def test_rule_56_target_size(self) -> None:
        elems = [{"id": "tiny_btn", "width": 16.0, "height": 16.0}]
        violations = check_target_size(elems, min_width=24.0, min_height=24.0)
        self.assertEqual(len(violations), 1)
        self.assertIn("tiny_btn", violations[0])

    def test_evidence_staleness(self) -> None:
        manifest = UiManifest(
            controls=[
                ControlRecord(
                    id="btn.save",
                    kind="button",
                    framework="pyqt",
                    screen="main",
                    file=str(self.root / "app.py"),
                    line=1,
                    source_hash="new_source_hash",
                )
            ]
        )
        ev_file = self.root / "ui_evidence.json"
        ev_data = {
            "run_id": "r1",
            "framework": "pyqt",
            "commit": "c1",
            "interactions": [
                {
                    "control_id": "btn.save",
                    "input_kind": "mouse",
                    "trusted": True,
                    "control_state": "enabled",
                    "source_hash": "stale_hash",
                }
            ],
        }
        ev_file.write_text(json.dumps(ev_data), encoding="utf-8")
        evidence = load_ui_evidence(ev_file, manifest)
        self.assertIsNotNone(evidence)
        if evidence is not None:
            # Stale interaction is dropped
            self.assertEqual(len(evidence.interactions), 0)

    def test_web_adapter_raw_unicode_escape(self) -> None:
        adapter = WebAdapter()
        tsx_bad = "<div>{multiplier}\\u00D7</div>\n"
        sites = adapter.raw_unicode_escape_sites(self.root / "View.tsx", tsx_bad)
        self.assertEqual(len(sites), 1)
        self.assertEqual(sites[0].code, 80)

        tsx_good = "<div>{multiplier}×</div>\n"
        sites_good = adapter.raw_unicode_escape_sites(self.root / "View.tsx", tsx_good)
        self.assertEqual(len(sites_good), 0)

    def test_web_adapter_unguarded_mutations(self) -> None:
        adapter = WebAdapter()
        bad_view = '<div onClick={(): void => setIsEditingTitle(true)}><h1>Title</h1></div>\n'
        sites = adapter.unguarded_mutation_sites(self.root / "RecipeView.tsx", bad_view)
        self.assertEqual(len(sites), 1)
        self.assertEqual(sites[0].code, 81)

        good_view = '<div onClick={(): void => { if (isQuickEditMode) setIsEditingTitle(true); }}><h1>Title</h1></div>\n'
        sites_good = adapter.unguarded_mutation_sites(self.root / "RecipeView.tsx", good_view)
        self.assertEqual(len(sites_good), 0)

        wrapped_view = (
            "{isQuickEditMode && (\n"
            "  <div>\n"
            "    <button onClick={(): void => handleDeleteStep(0, 0)}>Delete</button>\n"
            "  </div>\n"
            ")}\n"
        )
        self.assertEqual(len(adapter.unguarded_mutation_sites(self.root / "RecipeView.tsx", wrapped_view)), 0)

        confirmed_view = (
            "const handleDeleteItem = (itemId: string): void => {\n"
            "  if (!window.confirm('Delete item?')) return;\n"
            "};\n"
            "<button onClick={(): void => handleDeleteItem('1')}>Delete</button>\n"
        )
        self.assertEqual(len(adapter.unguarded_mutation_sites(self.root / "ShoppingListView.tsx", confirmed_view)), 0)

    def test_web_adapter_unbounded_chips(self) -> None:
        adapter = WebAdapter()
        bad_chips = '{itemsList.map(item => <button key={item}>{item}</button>)}\n'
        sites = adapter.unbounded_collection_sites(self.root / "Modal.tsx", bad_chips)
        self.assertEqual(len(sites), 1)
        self.assertEqual(sites[0].code, 83)

    def test_silent_fallback_passthrough(self) -> None:
        target = self.root / "domain" / "scaling" / "scale.ts"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            'if (!item.quantity || !item.unit) {\n  return { formattedText: item.raw };\n}\n',
            encoding="utf-8"
        )
        violations: list[tuple[Path, int, int]] = []
        scan_file(target, violations)
        v_codes = [v[2] for v in violations]
        self.assertIn(82, v_codes)

    def test_rules_84_to_90_and_helpers(self) -> None:
        adapter = WebAdapter()
        css_bad = self.root / "index.css"
        css_bad.write_text("body { background: #020617; color: #f8fafc; }\n", encoding="utf-8")
        self.assertEqual([s.code for s in adapter.unreset_control_sites(css_bad, css_bad.read_text(encoding="utf-8"))], [84])

        css_good = self.root / "app.css"
        css_good.write_text("html { color-scheme: dark; } body { background: #020617; } button { background-color: transparent; }\n", encoding="utf-8")
        self.assertEqual(adapter.unreset_control_sites(css_good, css_good.read_text(encoding="utf-8")), [])

        micro_tsx = self.root / "Chart.tsx"
        micro_tsx.write_text('<svg>{pts.map(p => <text key={p.id}>{p.name}</text>)}</svg><span className="text-[9px]">x</span>\n', encoding="utf-8")
        src = micro_tsx.read_text(encoding="utf-8")
        self.assertEqual([s.code for s in adapter.micro_typography_sites(micro_tsx, src)], [85])
        self.assertEqual([s.code for s in adapter.svg_chart_sites(micro_tsx, src)], [86])

        tons_tsx = self.root / "Tons.tsx"
        tons_tsx.write_text('<span>Min LEO (18.5 t)</span><span>30 tons</span><span>{"kg/t"}</span>\n', encoding="utf-8")
        self.assertGreaterEqual(len(adapter.ambiguous_unit_sites(tons_tsx, tons_tsx.read_text(encoding="utf-8"))), 1)

        iso_tsx = self.root / "Dates.tsx"
        iso_tsx.write_text('const today = new Date().toISOString().split("T")[0];\n', encoding="utf-8")
        self.assertEqual(adapter.ambiguous_unit_sites(iso_tsx, iso_tsx.read_text(encoding="utf-8")), [])

        # Rule 87: stale bundle vs src/src
        (self.root / "src" / "dist").mkdir(parents=True)
        (self.root / "src" / "src").mkdir(parents=True)
        (self.root / "src-tauri" / "src").mkdir(parents=True)
        dist_js = self.root / "src" / "dist" / "app.js"
        src_tsx = self.root / "src" / "src" / "App.tsx"
        dist_js.write_text("// built\n", encoding="utf-8")
        src_tsx.write_text("export const App = () => null;\n", encoding="utf-8")
        os.utime(dist_js, (1000.0, 1000.0))
        os.utime(src_tsx, (2000.0, 2000.0))
        main_rs = self.root / "src-tauri" / "src" / "main.rs"
        main_rs.write_text('const JS: &str = include_str!("../../src/dist/app.js");\nfn main() { TcpListener::bind("127.0.0.1:1420"); "--app="; }\n', encoding="utf-8")
        (self.root / "src-tauri" / "Cargo.toml").write_text('[package]\nname = "app"\n', encoding="utf-8")
        (self.root / "package.json").write_text('{"dependencies":{"react":"18.0.0"}}', encoding="utf-8")
        tauri_ad = TauriAdapter()
        self.assertEqual([s.code for s in tauri_ad.stale_bundle_sites(self.root)], [87])
        self.assertEqual([s.code for s in tauri_ad.desktop_lifecycle_sites(self.root)], [88])
        detected_names = [a.name for a in detect_adapters(self.root)]
        self.assertIn("tauri", detected_names)
        self.assertNotIn("web", detected_names)

        # Rule 89: tag-only release workflow
        wf_dir = self.root / ".github" / "workflows"
        wf_dir.mkdir(parents=True)
        (wf_dir / "release.yml").write_text("on:\n  push:\n    tags:\n      - 'v*'\n", encoding="utf-8")
        hygiene_v: list[tuple[Path, int, int]] = []
        detect_repo_hygiene_issues(self.root, hygiene_v)
        self.assertEqual([v[2] for v in hygiene_v], [89])

        # Rule 89: static 'latest' release tag overwrites in-place
        (wf_dir / "release.yml").write_text(
            "on:\n  push:\n    branches: [main]\n  pull_request:\n    branches: [main]\n"
            "uses: softprops/action-gh-release@v2\nwith:\n"
            "  tag_name: ${{ startsWith(github.ref, 'refs/tags/v') && github.ref_name || 'latest' }}\n",
            encoding="utf-8",
        )
        static_latest_v: list[tuple[Path, int, int]] = []
        detect_repo_hygiene_issues(self.root, static_latest_v)
        self.assertEqual([v[2] for v in static_latest_v], [89])
        self.assertEqual(static_latest_v[0][1], 8)

        # Rule 89 clean when dynamic semantic version tag is used
        (wf_dir / "release.yml").write_text(
            "on:\n  push:\n    branches: [main]\n  pull_request:\n    branches: [main]\n"
            "uses: softprops/action-gh-release@v2\nwith:\n  tag_name: ${{ steps.version.outputs.tag }}\n",
            encoding="utf-8",
        )
        clean_hygiene_v: list[tuple[Path, int, int]] = []
        detect_repo_hygiene_issues(self.root, clean_hygiene_v)
        self.assertEqual(clean_hygiene_v, [])

        # Rule 89: Android debug signing in release buildType + cleartext traffic
        android_app = self.root / "android" / "app"
        manifest_dir = android_app / "src" / "main"
        manifest_dir.mkdir(parents=True)
        gradle_file = android_app / "build.gradle"
        manifest_file = manifest_dir / "AndroidManifest.xml"
        gradle_file.write_text(
            "android {\n  buildTypes {\n    release {\n      signingConfig signingConfigs.debug\n    }\n"
            "    debug {\n      signingConfig signingConfigs.debug\n    }\n  }\n}\n",
            encoding="utf-8",
        )
        manifest_file.write_text(
            '<manifest><application android:usesCleartextTraffic="true" /></manifest>\n',
            encoding="utf-8",
        )
        android_v: list[tuple[Path, int, int]] = []
        detect_repo_hygiene_issues(self.root, android_v)
        self.assertEqual([(p.name, ln, code) for p, ln, code in android_v], [("build.gradle", 4, 89), ("AndroidManifest.xml", 1, 89)])

        gradle_file.write_text(
            "android {\n  buildTypes {\n    release {\n      signingConfig signingConfigs.release\n    }\n"
            "    debug {\n      signingConfig signingConfigs.debug\n    }\n  }\n}\n",
            encoding="utf-8",
        )
        manifest_file.write_text(
            '<manifest><application android:usesCleartextTraffic="false" /></manifest>\n',
            encoding="utf-8",
        )
        clean_android_v: list[tuple[Path, int, int]] = []
        detect_repo_hygiene_issues(self.root, clean_android_v)
        self.assertEqual(clean_android_v, [])

        # Layout parent clipping check
        clip_findings = check_parent_clipping([{"id": "child", "x": 10.0, "y": 10.0, "width": 120.0, "height": 20.0, "parent_rect": {"x": 10.0, "y": 10.0, "width": 80.0, "height": 40.0}}])
        self.assertEqual(len(clip_findings), 1)
        self.assertEqual(clip_findings[0].type, "clipping")

        # Viewport overflow check
        vp_findings = check_viewport_overflow(
            [
                {"id": "fits", "x": 10.0, "y": 10.0, "width": 100.0, "height": 40.0},
                {"id": "too_wide", "x": 1200.0, "y": 20.0, "width": 200.0, "height": 40.0},
                {"id": "too_tall", "x": 20.0, "y": 760.0, "width": 100.0, "height": 60.0},
                {"id": "hidden_wide", "x": 2000.0, "y": 0.0, "width": 100.0, "height": 40.0, "visible": False},
            ],
            viewport_width=1280.0,
            viewport_height=800.0,
        )
        self.assertEqual(len(vp_findings), 2)
        self.assertEqual([item.type for item in vp_findings], ["viewport_overflow", "viewport_overflow"])
        self.assertEqual([item.element_ids[0] for item in vp_findings], ["too_wide", "too_tall"])

        # Untracked dir expansion in collect_git_diff_files
        subprocess.run(["git", "init"], cwd=str(self.root), capture_output=True, check=True)
        untracked_sub = self.root / "new_pkg"
        untracked_sub.mkdir()
        sub_py = untracked_sub / "mod.py"
        sub_py.write_text("x: int = 1\n", encoding="utf-8")
        diff_files = collect_git_diff_files(str(self.root))
        self.assertIn(sub_py.resolve(), [f.resolve() for f in diff_files])


if __name__ == "__main__":
    unittest.main()
