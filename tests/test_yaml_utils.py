"""Unit tests for yaml_utils parser and serializer."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from yaml_utils import _parse_scalar, dump_yaml, parse_yaml


class TestYamlUtils(unittest.TestCase):
    """Validates pure-Python YAML parser and dumper functionality."""

    def test_parse_scalars(self) -> None:
        self.assertEqual(_parse_scalar("true"), True)
        self.assertEqual(_parse_scalar("False"), False)
        self.assertEqual(_parse_scalar("123"), 123)
        self.assertEqual(_parse_scalar("3.14"), 3.14)
        self.assertIsNone(_parse_scalar("null"))
        self.assertEqual(_parse_scalar('"hello world"'), "hello world")
        self.assertEqual(_parse_scalar("[a, b, c]"), ["a", "b", "c"])

    def test_parse_simple_mapping(self) -> None:
        yaml_text = """
        tools:
          claude: true
          cursor: false
        scope: workspace
        write_mode: append
        """
        data = parse_yaml(yaml_text)
        self.assertEqual(data.get("scope"), "workspace")
        self.assertEqual(data.get("write_mode"), "append")
        tools = data.get("tools", {})
        self.assertEqual(tools.get("claude"), True)
        self.assertEqual(tools.get("cursor"), False)

    def test_parse_nested_lists(self) -> None:
        yaml_text = """
        profile:
          level: strict
          skip_rules: [1, 5, 17]
        items:
          - apple
          - banana
        """
        data = parse_yaml(yaml_text)
        self.assertEqual(data["profile"]["level"], "strict")
        self.assertEqual(data["profile"]["skip_rules"], [1, 5, 17])
        self.assertEqual(data["items"], ["apple", "banana"])

    def test_dump_and_roundtrip(self) -> None:
        sample_dict = {
            "version": 1,
            "scope": "workspace",
            "write_mode": "append",
            "profile": {
                "level": "strict",
                "skip": [1, 5],
            },
            "tools": {
                "claude": True,
                "cursor": False,
            },
        }
        dumped = dump_yaml(sample_dict)
        self.assertIn("version: 1", dumped)
        self.assertIn("scope: workspace", dumped)
        self.assertIn("claude: true", dumped)
        reparsed = parse_yaml(dumped)
        self.assertEqual(reparsed["version"], 1)
        self.assertEqual(reparsed["scope"], "workspace")
        self.assertEqual(reparsed["tools"]["claude"], True)
        self.assertEqual(reparsed["profile"]["level"], "strict")


if __name__ == "__main__":
    unittest.main()
