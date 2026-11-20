"""Pure-Python YAML parser and serializer with PyYAML fallback support."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore # noqa: 22
except ModuleNotFoundError:
    yaml = None


def _parse_scalar(value_str: str) -> Any:
    raw_val = value_str.strip()
    if not raw_val:
        return None
    if (raw_val.startswith('"') and raw_val.endswith('"')) or (raw_val.startswith("'") and raw_val.endswith("'")):
        return raw_val[1:-1]
    lowered = raw_val.lower()
    if lowered in ("true", "yes", "on"):
        return True
    if lowered in ("false", "no", "off"):
        return False
    if lowered in ("null", "none", "~"):
        return None
    if re.fullmatch(r"-?\d+", raw_val):
        return int(raw_val)
    if re.fullmatch(r"-?\d+\.\d+", raw_val):
        return float(raw_val)
    if raw_val.startswith("[") and raw_val.endswith("]"):
        inner = raw_val[1:-1].strip()
        if not inner:
            return []
        items = [elem.strip() for elem in inner.split(",")]
        return [_parse_scalar(elem) for elem in items if elem]
    return raw_val


def parse_yaml(text: str) -> dict[str, Any]:
    if yaml is not None:
        result = yaml.safe_load(text)
        return result if isinstance(result, dict) else {}

    lines = text.splitlines()
    cleaned: list[tuple[int, str]] = []
    for raw in lines:
        stripped = raw.split("#", 1)[0].rstrip()
        if stripped.strip():
            indent = len(stripped) - len(stripped.lstrip(" "))
            cleaned.append((indent, stripped.strip()))

    idx = 0

    def parse_block(current_indent: int) -> tuple[Any, int]:
        nonlocal idx
        if idx >= len(cleaned):
            return {}, idx

        first_indent, first_line = cleaned[idx]
        if first_line.startswith("- "):
            result_list: list[Any] = []
            while idx < len(cleaned):
                indent, line = cleaned[idx]
                if indent < current_indent:
                    break
                if line.startswith("- "):
                    item_text = line[2:].strip()
                    idx += 1
                    if not item_text:
                        if idx < len(cleaned) and cleaned[idx][0] > indent:
                            sub_val, idx = parse_block(cleaned[idx][0])
                            result_list.append(sub_val)
                        else:
                            result_list.append(None)
                    elif ":" in item_text and not (item_text.startswith('"') or item_text.startswith("'")):
                        item_k, item_v = item_text.split(":", 1)
                        entry_dict: dict[str, Any] = {}
                        entry_val = _parse_scalar(item_v)
                        entry_dict[item_k.strip()] = entry_val
                        while idx < len(cleaned) and cleaned[idx][0] > indent:
                            sub_indent, sub_line = cleaned[idx]
                            if ":" in sub_line and not sub_line.startswith("- "):
                                sub_k, sub_v = sub_line.split(":", 1)
                                idx += 1
                                entry_dict[sub_k.strip()] = _parse_scalar(sub_v)
                            else:
                                break
                        result_list.append(entry_dict)
                    else:
                        result_list.append(_parse_scalar(item_text))
                else:
                    break
            return result_list, idx

        result_dict: dict[str, Any] = {}
        while idx < len(cleaned):
            indent, line = cleaned[idx]
            if indent < current_indent:
                break
            if ":" not in line:
                idx += 1
                continue
            key_part, val_part = line.split(":", 1)
            key = key_part.strip()
            val_part = val_part.strip()
            idx += 1

            if not val_part:
                if idx < len(cleaned) and cleaned[idx][0] > indent:
                    child_val, idx = parse_block(cleaned[idx][0])
                    result_dict[key] = child_val
                else:
                    result_dict[key] = None
            else:
                result_dict[key] = _parse_scalar(val_part)
        return result_dict, idx

    parsed, _ = parse_block(0)
    return parsed if isinstance(parsed, dict) else {}


def dump_yaml(data: dict[str, Any] | list[Any], indent_level: int = 0) -> str:
    lines: list[str] = []
    prefix = "  " * indent_level

    if isinstance(data, dict):
        for dict_key, dict_val in data.items():
            if isinstance(dict_val, dict):
                lines.append(f"{prefix}{dict_key}:")
                lines.append(dump_yaml(dict_val, indent_level + 1))
            elif isinstance(dict_val, list):
                if not dict_val:
                    lines.append(f"{prefix}{dict_key}: []")
                elif all(isinstance(item, (str, int, float, bool)) for item in dict_val) and len(dict_val) <= 4:
                    formatted = ", ".join(_format_scalar(item) for item in dict_val)
                    lines.append(f"{prefix}{dict_key}: [{formatted}]")
                else:
                    lines.append(f"{prefix}{dict_key}:")
                    for item in dict_val:
                        if isinstance(item, dict):
                            lines.append(f"{prefix}  -")
                            lines.append(dump_yaml(item, indent_level + 2))
                        else:
                            lines.append(f"{prefix}  - {_format_scalar(item)}")
            else:
                lines.append(f"{prefix}{dict_key}: {_format_scalar(dict_val)}")
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                lines.append(f"{prefix}-")
                lines.append(dump_yaml(item, indent_level + 1))
            else:
                lines.append(f"{prefix}- {_format_scalar(item)}")
    return "\n".join(lines)


def _format_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text_val = str(value)
    if any(ch in text_val for ch in (":", "#", "[", "]", "{", "}", ",", "\n")) or text_val in ("true", "false", "null"):
        return f'"{text_val}"'
    return text_val


def load_yaml_file(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    return parse_yaml(text)


def dump_yaml_file(data: dict[str, Any], path: Path) -> None:
    text = dump_yaml(data) + "\n"
    path.write_text(text, encoding="utf-8")
