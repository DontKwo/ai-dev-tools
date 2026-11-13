"""Comprehensive test suite for multi-framework UI quality rules and audit engine."""

import json
import tempfile
import unittest
from pathlib import Path

from scripts.claudemd_linter import scan_file
from scripts.ui_adapters import get_adapter
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
from scripts.ui_layout import Rect, check_element_overlaps, check_target_size
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


if __name__ == "__main__":
    unittest.main()
