"""Custom YAML linter rule loader, matcher, and auto-fix helpers."""

from __future__ import annotations

import ast
import fnmatch
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Callable

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.utils import get_user_home  # noqa: 12

CUSTOM_CONFIG_FILENAME = "linter_custom.yaml"
CUSTOM_EXAMPLE_FILENAME = "linter_custom.example.yaml"

_KNOWN_DICT_FIELDS = {
    "pattern",
    "word",
    "phrase",
    "match",
    "text",
    "replacement",
    "case-sensitive",
    "case_sensitive",
    "word-boundary",
    "word_boundary",
    "regex",
    "include-tests",
    "include_tests",
    "auto-fix",
    "auto_fix",
    "reason",
    "module",
    "glob",
    "must-contain",
    "must_contain",
    "must-not-contain",
    "must_not_contain",
    "skip",
}


@dataclass
class RemoveRule:
    pattern: str
    case_sensitive: bool = False
    word_boundary: bool = True
    regex: bool = False
    include_tests: bool = True
    reason: str = ""


@dataclass
class ReplaceRule:
    pattern: str
    replacement: str
    case_sensitive: bool = False
    word_boundary: bool = True
    regex: bool = False
    auto_fix: bool = True
    include_tests: bool = True
    reason: str = ""


@dataclass
class BannedImportRule:
    module: str
    reason: str = ""


@dataclass
class FileGuardRule:
    glob: str
    must_contain: list[str] = field(default_factory=list)
    must_not_contain: list[str] = field(default_factory=list)
    case_sensitive: bool = False


@dataclass
class RuleOverride:
    glob: str
    skip: set[int] = field(default_factory=set)


@dataclass
class CustomLinterConfig:
    remove: list[RemoveRule] = field(default_factory=list)
    replace: list[ReplaceRule] = field(default_factory=list)
    allowed_vars: set[str] = field(default_factory=set)
    banned_vars: set[str] = field(default_factory=set)
    banned_imports: list[BannedImportRule] = field(default_factory=list)
    file_guards: list[FileGuardRule] = field(default_factory=list)
    ignore_paths: list[str] = field(default_factory=list)
    rule_overrides: list[RuleOverride] = field(default_factory=list)
    loaded_files: list[Path] = field(default_factory=list)


def _strip_yaml_comment(line: str) -> str:
    in_single = False
    in_double = False
    escaped = False
    idx = 0
    while idx < len(line):
        char = line[idx]
        if in_double:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_double = False
        elif in_single:
            if char == "'":
                if idx + 1 < len(line) and line[idx + 1] == "'":
                    idx += 1
                else:
                    in_single = False
        else:
            if char == '"':
                in_double = True
            elif char == "'":
                in_single = True
            elif char == "#" and (idx == 0 or line[idx - 1].isspace()):
                return line[:idx].rstrip()
        idx += 1
    return line.rstrip()


def _split_outside_quotes(text: str, sep: str = ",") -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    in_single = False
    in_double = False
    escaped = False
    bracket_depth = 0
    brace_depth = 0
    idx = 0

    while idx < len(text):
        char = text[idx]
        if in_double:
            current.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_double = False
        elif in_single:
            current.append(char)
            if char == "'":
                if idx + 1 < len(text) and text[idx + 1] == "'":
                    current.append(text[idx + 1])
                    idx += 1
                else:
                    in_single = False
        else:
            if char == '"':
                in_double = True
                current.append(char)
            elif char == "'":
                in_single = True
                current.append(char)
            elif char == "[":
                bracket_depth += 1
                current.append(char)
            elif char == "]" and bracket_depth > 0:
                bracket_depth -= 1
                current.append(char)
            elif char == "{":
                brace_depth += 1
                current.append(char)
            elif char == "}" and brace_depth > 0:
                brace_depth -= 1
                current.append(char)
            elif char == sep and bracket_depth == 0 and brace_depth == 0:
                parts.append("".join(current).strip())
                current = []
                idx += 1
                continue
            else:
                current.append(char)
        idx += 1

    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return parts


def _find_unquoted_colon(text: str, allow_compact: bool = False) -> int:
    in_single = False
    in_double = False
    escaped = False
    bracket_depth = 0
    brace_depth = 0
    idx = 0

    while idx < len(text):
        char = text[idx]
        if in_double:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_double = False
        elif in_single:
            if char == "'":
                if idx + 1 < len(text) and text[idx + 1] == "'":
                    idx += 1
                else:
                    in_single = False
        else:
            if char == '"':
                in_double = True
            elif char == "'":
                in_single = True
            elif char == "[":
                bracket_depth += 1
            elif char == "]" and bracket_depth > 0:
                bracket_depth -= 1
            elif char == "{":
                brace_depth += 1
            elif char == "}" and brace_depth > 0:
                brace_depth -= 1
            elif char == ":" and bracket_depth == 0 and brace_depth == 0:
                next_char = text[idx + 1] if idx + 1 < len(text) else ""
                if allow_compact or not next_char or next_char.isspace() or next_char in ("{", "["):
                    return idx
        idx += 1
    return -1


def _unquote_scalar(raw: str) -> str:
    stripped = raw.strip()
    if len(stripped) >= 2 and stripped[0] == '"' and stripped[-1] == '"':
        inner = stripped[1:-1]
        out: list[str] = []
        idx = 0
        while idx < len(inner):
            char = inner[idx]
            if char == "\\" and idx + 1 < len(inner):
                nxt = inner[idx + 1]
                escapes = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", '"': '"'}
                out.append(escapes.get(nxt, "\\" + nxt))
                idx += 2
                continue
            out.append(char)
            idx += 1
        return "".join(out)
    if len(stripped) >= 2 and stripped[0] == "'" and stripped[-1] == "'":
        return stripped[1:-1].replace("''", "'")
    return stripped


def _parse_inline_dict(inner: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for pair in _split_outside_quotes(inner, ","):
        colon_idx = _find_unquoted_colon(pair, allow_compact=True)
        if colon_idx == -1:
            continue
        key = _unquote_scalar(pair[:colon_idx].strip())
        val_raw = pair[colon_idx + 1 :].strip()
        result[key] = _parse_yaml_scalar(val_raw)
    return result


def _parse_yaml_scalar(raw: str) -> Any:
    stripped = raw.strip()
    if not stripped:
        return ""
    if (stripped[0] == '"' and stripped[-1] == '"') or (stripped[0] == "'" and stripped[-1] == "'"):
        return _unquote_scalar(stripped)
    low = stripped.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    if re.fullmatch(r"-?\d+", stripped):
        return int(stripped)
    if stripped.startswith("[") and stripped.endswith("]"):
        inner = stripped[1:-1].strip()
        if not inner:
            return []
        return [_parse_yaml_scalar(item) for item in _split_outside_quotes(inner, ",")]
    if stripped.startswith("{") and stripped.endswith("}"):
        return _parse_inline_dict(stripped[1:-1])
    return stripped


def _split_inline_kv_pairs(text: str) -> list[str]:
    candidates = _split_outside_quotes(text, ",")
    if len(candidates) <= 1:
        return candidates
    if all(_find_unquoted_colon(part, allow_compact=True) != -1 for part in candidates):
        return candidates
    return [text]


def _extract_quoted_prefix(text: str) -> tuple[str, str] | None:
    stripped = text.strip()
    if not stripped or stripped[0] not in ('"', "'"):
        return None
    quote = stripped[0]
    escaped = False
    idx = 1
    while idx < len(stripped):
        char = stripped[idx]
        if quote == '"':
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                return stripped[: idx + 1], stripped[idx + 1 :].strip()
        else:
            if char == "'":
                if idx + 1 < len(stripped) and stripped[idx + 1] == "'":
                    idx += 1
                else:
                    return stripped[: idx + 1], stripped[idx + 1 :].strip()
        idx += 1
    return None


def _parse_item_head(rest: str, has_children: bool) -> tuple[Any, bool]:
    stripped = rest.strip()
    if not stripped:
        return {}, True
    if stripped.startswith("{") and stripped.endswith("}"):
        return _parse_inline_dict(stripped[1:-1]), True

    quoted = _extract_quoted_prefix(stripped)
    if quoted is not None:
        q_part, tail = quoted
        if not tail:
            return _unquote_scalar(q_part), False
        if tail.startswith(":"):
            after_colon = tail[1:].strip()
            item_dict: dict[str, Any] = {"pattern": _unquote_scalar(q_part)}
            if after_colon.startswith("{") and after_colon.endswith("}"):
                item_dict.update(_parse_inline_dict(after_colon[1:-1]))
            elif after_colon:
                for pair in _split_inline_kv_pairs(after_colon):
                    colon_idx = _find_unquoted_colon(pair, allow_compact=True)
                    if colon_idx != -1:
                        key = _unquote_scalar(pair[:colon_idx].strip())
                        item_dict[key] = _parse_yaml_scalar(pair[colon_idx + 1 :].strip())
            return item_dict, True

    colon_idx = _find_unquoted_colon(stripped)
    if colon_idx == -1:
        return _parse_yaml_scalar(stripped), False

    key_name = _unquote_scalar(stripped[:colon_idx].strip())
    val_part = stripped[colon_idx + 1 :].strip()
    if not val_part and not has_children and key_name not in _KNOWN_DICT_FIELDS:
        return stripped, False

    item_dict = {}
    for pair in _split_inline_kv_pairs(stripped):
        pair_colon = _find_unquoted_colon(pair, allow_compact=True)
        if pair_colon == -1:
            continue
        p_key = _unquote_scalar(pair[:pair_colon].strip())
        p_val = pair[pair_colon + 1 :].strip()
        item_dict[p_key] = _parse_yaml_scalar(p_val) if p_val else ""
    return item_dict, True


def _consume_nested_list(tokens: list[tuple[int, str]], start_idx: int, min_indent: int) -> tuple[list[Any], int]:
    nested: list[Any] = []
    idx = start_idx
    while idx < len(tokens) and tokens[idx][0] >= min_indent:
        _, text = tokens[idx]
        if not (text == "-" or text.startswith("- ")):
            break
        nested.append(_parse_yaml_scalar(text[1:].strip()))
        idx += 1
    return nested, idx


def parse_custom_yaml(content: str) -> dict[str, Any]:
    """Parse subset of YAML used for custom linter rules without external deps."""
    tokens: list[tuple[int, str]] = []
    for raw_line in content.replace("\r\n", "\n").splitlines():
        cleaned = _strip_yaml_comment(raw_line)
        stripped = cleaned.lstrip()
        if not stripped:
            continue
        indent = len(cleaned) - len(stripped)
        tokens.append((indent, stripped))

    data: dict[str, Any] = {}
    idx = 0
    total = len(tokens)

    while idx < total:
        indent, text = tokens[idx]
        colon_idx = _find_unquoted_colon(text)
        if indent != 0 or colon_idx == -1:
            idx += 1
            continue

        sec_key = _unquote_scalar(text[:colon_idx].strip())
        rest = text[colon_idx + 1 :].strip()
        idx += 1
        if rest:
            data[sec_key] = _parse_yaml_scalar(rest)
            continue

        items: list[Any] = []
        while idx < total and tokens[idx][0] > indent:
            item_indent, item_text = tokens[idx]
            if not (item_text == "-" or item_text.startswith("- ")):
                idx += 1
                continue
            after_dash = item_text[1:].strip()
            has_children = idx + 1 < total and tokens[idx + 1][0] > item_indent
            parsed_item, is_dict = _parse_item_head(after_dash, has_children)
            idx += 1

            if is_dict:
                while idx < total and tokens[idx][0] > item_indent:
                    sub_indent, sub_text = tokens[idx]
                    if sub_text == "-" or sub_text.startswith("- "):
                        break
                    sub_colon = _find_unquoted_colon(sub_text)
                    idx += 1
                    if sub_colon == -1:
                        continue
                    sub_key = _unquote_scalar(sub_text[:sub_colon].strip())
                    sub_val = sub_text[sub_colon + 1 :].strip()
                    if not sub_val and idx < total and tokens[idx][0] > sub_indent and (
                        tokens[idx][1] == "-" or tokens[idx][1].startswith("- ")
                    ):
                        nested_items, idx = _consume_nested_list(tokens, idx, tokens[idx][0])
                        parsed_item[sub_key] = nested_items
                    else:
                        parsed_item[sub_key] = _parse_yaml_scalar(sub_val)
            items.append(parsed_item)

        data[sec_key] = items

    return data


def _get_bool(mapping: dict[str, Any], hyphen_key: str, snake_key: str, default: bool) -> bool:
    if hyphen_key in mapping:
        raw_val = mapping[hyphen_key]
    elif snake_key in mapping:
        raw_val = mapping[snake_key]
    else:
        return default
    if isinstance(raw_val, bool):
        return raw_val
    return str(raw_val).strip().lower() in ("true", "1", "yes")


def _extract_pattern_str(mapping: dict[str, Any]) -> str:
    for key in ("pattern", "word", "phrase", "match", "text"):
        value = mapping.get(key)
        if value is not None and str(value) != "":
            return str(value)
    return ""


def _to_str_list(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(elem) for elem in raw if str(elem) != ""]
    if raw is not None and str(raw) != "":
        return [str(raw)]
    return []


def _merge_yaml_dict(cfg: CustomLinterConfig, data: dict[str, Any]) -> None:
    for entry in _as_list(data.get("remove")):
        if isinstance(entry, str) and entry:
            cfg.remove.append(RemoveRule(pattern=entry))
        elif isinstance(entry, dict):
            pat = _extract_pattern_str(entry)
            if pat:
                cfg.remove.append(
                    RemoveRule(
                        pattern=pat,
                        case_sensitive=_get_bool(entry, "case-sensitive", "case_sensitive", False),
                        word_boundary=_get_bool(entry, "word-boundary", "word_boundary", True),
                        regex=_get_bool(entry, "regex", "regex", False),
                        include_tests=_get_bool(entry, "include-tests", "include_tests", True),
                        reason=str(entry.get("reason", "")),
                    )
                )

    for entry in _as_list(data.get("replace")):
        if not isinstance(entry, dict):
            continue
        pat = _extract_pattern_str(entry)
        if not pat:
            continue
        cfg.replace.append(
            ReplaceRule(
                pattern=pat,
                replacement=str(entry.get("replacement", "")),
                case_sensitive=_get_bool(entry, "case-sensitive", "case_sensitive", False),
                word_boundary=_get_bool(entry, "word-boundary", "word_boundary", True),
                regex=_get_bool(entry, "regex", "regex", False),
                auto_fix=_get_bool(entry, "auto-fix", "auto_fix", True),
                include_tests=_get_bool(entry, "include-tests", "include_tests", True),
                reason=str(entry.get("reason", "")),
            )
        )

    cfg.allowed_vars.update(str(item) for item in _as_list(data.get("allowed_vars")) if str(item))
    cfg.banned_vars.update(str(item).lower() for item in _as_list(data.get("banned_vars")) if str(item))

    for entry in _as_list(data.get("banned_imports")):
        if isinstance(entry, str) and entry:
            cfg.banned_imports.append(BannedImportRule(module=entry))
        elif isinstance(entry, dict):
            mod = str(entry.get("module") or entry.get("name") or "")
            if mod:
                cfg.banned_imports.append(BannedImportRule(module=mod, reason=str(entry.get("reason", ""))))

    for entry in _as_list(data.get("file_guards")):
        if not isinstance(entry, dict):
            continue
        glob_pat = str(entry.get("glob", ""))
        if not glob_pat:
            continue
        must_contain = _to_str_list(entry.get("must-contain") or entry.get("must_contain"))
        must_not = _to_str_list(entry.get("must-not-contain") or entry.get("must_not_contain"))
        cfg.file_guards.append(
            FileGuardRule(
                glob=glob_pat,
                must_contain=must_contain,
                must_not_contain=must_not,
                case_sensitive=_get_bool(entry, "case-sensitive", "case_sensitive", False),
            )
        )

    cfg.ignore_paths.extend(str(item) for item in _as_list(data.get("ignore_paths")) if str(item))

    for entry in _as_list(data.get("rule_overrides")):
        if not isinstance(entry, dict):
            continue
        glob_pat = str(entry.get("glob", ""))
        if not glob_pat:
            continue
        skip_codes = {int(code) for code in _as_list(entry.get("skip")) if str(code).isdigit()}
        if skip_codes:
            cfg.rule_overrides.append(RuleOverride(glob=glob_pat, skip=skip_codes))


def _as_list(raw: Any) -> list[Any]:
    return raw if isinstance(raw, list) else []


def _candidate_config_paths(target_root: Path | None = None, file_path: Path | None = None) -> list[Path]:
    if "AI_DEV_TOOLS_CUSTOM_CONFIG" in os.environ:
        raw_env = os.environ.get("AI_DEV_TOOLS_CUSTOM_CONFIG", "").strip()
        if not raw_env or raw_env.upper() == "NONE":
            return []
        return [Path(part.strip()) for part in raw_env.split(os.pathsep) if part.strip()]

    candidates: list[Path] = [
        _REPO_ROOT / CUSTOM_CONFIG_FILENAME,
        get_user_home() / ".config" / "ai-dev-tools" / CUSTOM_CONFIG_FILENAME,
    ]
    env_target = os.environ.get("AI_DEV_TOOLS_TARGET_ROOT", "").strip()
    if env_target:
        candidates.append(Path(env_target) / CUSTOM_CONFIG_FILENAME)
    if target_root is not None:
        base_dir = target_root if target_root.is_dir() else target_root.parent
        candidates.append(base_dir / CUSTOM_CONFIG_FILENAME)
    if file_path is not None:
        cursor = file_path.parent.resolve()
        while True:
            candidates.append(cursor / CUSTOM_CONFIG_FILENAME)
            if (cursor / ".git").exists() or cursor.parent == cursor:
                break
            cursor = cursor.parent
    return candidates


def load_custom_linter_config(
    target_root: Path | None = None,
    file_path: Path | None = None,
) -> CustomLinterConfig:
    """Discover and merge custom linter YAML configs from repo, user, and target paths."""
    cfg = CustomLinterConfig()
    seen: set[Path] = set()
    for cand in _candidate_config_paths(target_root=target_root, file_path=file_path):
        try:
            resolved = cand.resolve()
        except OSError:
            continue
        if resolved in seen or not resolved.is_file():
            continue
        seen.add(resolved)
        try:
            content = resolved.read_text(encoding="utf-8")
        except OSError:
            continue
        parsed = parse_custom_yaml(content)
        _merge_yaml_dict(cfg, parsed)
        cfg.loaded_files.append(resolved)
    return cfg


def compile_pattern_regex(
    pattern: str,
    case_sensitive: bool = False,
    word_boundary: bool = True,
    regex: bool = False,
) -> re.Pattern[str] | None:
    """Compile a custom rule pattern with optional case sensitivity and smart word boundaries."""
    if not pattern:
        return None
    flags = 0 if case_sensitive else re.IGNORECASE
    if regex:
        try:
            return re.compile(pattern, flags)
        except re.error:
            return None

    escaped = re.escape(pattern)
    if word_boundary:
        prefix = r"(?<![A-Za-z0-9])" if pattern[0].isalnum() else ""
        if len(pattern) == 2 and pattern[0].isalpha() and pattern[1] == ":":
            suffix = r"(?=[\\/])"
        elif pattern[-1].isalnum():
            suffix = r"(?![A-Za-z0-9])"
        else:
            suffix = ""
        expr = f"{prefix}{escaped}{suffix}"
    else:
        expr = escaped
    return re.compile(expr, flags)


def _glob_to_regex(clean_pat: str) -> re.Pattern[str]:
    parts: list[str] = ["^"]
    idx = 0
    total = len(clean_pat)
    while idx < total:
        if clean_pat.startswith("**/", idx):
            parts.append("(?:.+/)?")
            idx += 3
        elif clean_pat.startswith("**", idx):
            parts.append(".*")
            idx += 2
        elif clean_pat[idx] == "*":
            parts.append("[^/]*")
            idx += 1
        elif clean_pat[idx] == "?":
            parts.append("[^/]")
            idx += 1
        else:
            parts.append(re.escape(clean_pat[idx]))
            idx += 1
    parts.append("$")
    return re.compile("".join(parts))


def matches_glob(path: Path, pattern: str, root: Path | None = None) -> bool:
    """Check whether a file path matches a configured glob or path pattern."""
    clean_pat = pattern.replace("\\", "/").strip()
    if not clean_pat:
        return False

    if clean_pat.endswith("/"):
        clean_pat = f"{clean_pat}**"

    if root is not None:
        base_root = root.resolve()
    else:
        env_root = os.environ.get("AI_DEV_TOOLS_TARGET_ROOT", "").strip()
        base_root = Path(env_root).resolve() if env_root else _REPO_ROOT.resolve()
    resolved_path = path.resolve()
    try:
        rel_str = resolved_path.relative_to(base_root).as_posix()
    except ValueError:
        rel_str = resolved_path.as_posix()

    if "/" not in clean_pat:
        if fnmatch.fnmatch(path.name, clean_pat) or clean_pat in path.parts:
            return True
    if _glob_to_regex(clean_pat).match(rel_str):
        return True
    return fnmatch.fnmatch(rel_str, clean_pat) or PurePosixPath(rel_str).match(clean_pat)


def is_ignored_by_custom_config(path: Path, cfg: CustomLinterConfig, root: Path | None = None) -> bool:
    if path.name in (CUSTOM_CONFIG_FILENAME, CUSTOM_EXAMPLE_FILENAME):
        return True
    return any(matches_glob(path, pat, root=root) for pat in cfg.ignore_paths)


def get_skipped_codes_for_path(path: Path, cfg: CustomLinterConfig, root: Path | None = None) -> set[int]:
    skipped: set[int] = set()
    for override in cfg.rule_overrides:
        if matches_glob(path, override.glob, root=root):
            skipped.update(override.skip)
    return skipped


def filter_overridden_violations(
    violations: list[tuple[Path, int, int]],
    cfg: CustomLinterConfig,
    root: Path | None = None,
) -> list[tuple[Path, int, int]]:
    if not cfg.rule_overrides:
        return violations
    cache: dict[Path, set[int]] = {}
    filtered: list[tuple[Path, int, int]] = []
    for path, lineno, code in violations:
        if path not in cache:
            cache[path] = get_skipped_codes_for_path(path, cfg, root=root)
        if code not in cache[path]:
            filtered.append((path, lineno, code))
    return filtered


def _scan_banned_imports(
    path: Path,
    source: str,
    lines: list[str],
    banned: list[BannedImportRule],
    suppressed_fn: Callable[[str, int | None], bool],
    violations: list[tuple[Path, int, int]],
) -> None:
    if path.suffix != ".py" or not banned:
        return
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return
    banned_mods = [rule.module.strip() for rule in banned if rule.module.strip()]
    if not banned_mods:
        return

    for node in ast.walk(tree):
        matched = False
        if isinstance(node, ast.Import):
            for alias in node.names:
                if any(alias.name == mod or alias.name.startswith(mod + ".") for mod in banned_mods):
                    matched = True
                    break
        elif isinstance(node, ast.ImportFrom) and node.module:
            if any(node.module == mod or node.module.startswith(mod + ".") for mod in banned_mods):
                matched = True
        if matched:
            lineno = getattr(node, "lineno", 1)
            line_text = lines[lineno - 1] if 0 < lineno <= len(lines) else ""
            if not suppressed_fn(line_text, 91):
                violations.append((path, lineno, 91))


def _scan_file_guards(
    path: Path,
    source: str,
    lines: list[str],
    guards: list[FileGuardRule],
    suppressed_fn: Callable[[str, int | None], bool],
    violations: list[tuple[Path, int, int]],
    root: Path | None = None,
) -> None:
    if not guards:
        return
    for guard in guards:
        if not matches_glob(path, guard.glob, root=root):
            continue
        if lines and suppressed_fn(lines[0], 91):
            continue
        haystack = source if guard.case_sensitive else source.lower()
        for required in guard.must_contain:
            needle = required if guard.case_sensitive else required.lower()
            if needle not in haystack:
                violations.append((path, 1, 91))
                break
        for forbidden in guard.must_not_contain:
            needle = forbidden if guard.case_sensitive else forbidden.lower()
            for lineno, line in enumerate(lines, 1):
                line_hay = line if guard.case_sensitive else line.lower()
                if needle in line_hay and not suppressed_fn(line, 91):
                    violations.append((path, lineno, 91))


def scan_custom_rules_for_file(
    path: Path,
    source: str,
    lines: list[str],
    cfg: CustomLinterConfig,
    suppressed_fn: Callable[[str, int | None], bool],
    root: Path | None = None,
) -> list[tuple[Path, int, int]]:
    """Run all custom YAML rules against a single file and return Rule 91 violations."""
    violations: list[tuple[Path, int, int]] = []
    if path.name in (CUSTOM_CONFIG_FILENAME, CUSTOM_EXAMPLE_FILENAME):
        return violations

    is_test = "tests" in path.parts or path.name.startswith("test_")
    compiled_patterns: list[re.Pattern[str]] = []

    for rule in cfg.remove:
        if not rule.include_tests and is_test:
            continue
        compiled = compile_pattern_regex(rule.pattern, rule.case_sensitive, rule.word_boundary, rule.regex)
        if compiled is not None:
            compiled_patterns.append(compiled)

    for rule in cfg.replace:
        if not rule.include_tests and is_test:
            continue
        compiled = compile_pattern_regex(rule.pattern, rule.case_sensitive, rule.word_boundary, rule.regex)
        if compiled is not None:
            compiled_patterns.append(compiled)

    if compiled_patterns:
        for lineno, line in enumerate(lines, 1):
            if suppressed_fn(line, 91):
                continue
            if any(pat.search(line) for pat in compiled_patterns):
                violations.append((path, lineno, 91))

    _scan_banned_imports(path, source, lines, cfg.banned_imports, suppressed_fn, violations)
    _scan_file_guards(path, source, lines, cfg.file_guards, suppressed_fn, violations, root=root)
    return filter_overridden_violations(violations, cfg, root=root)


def apply_custom_replacements(line: str, path: Path, cfg: CustomLinterConfig) -> tuple[str, list[str]]:
    """Apply deterministic custom replace rules marked auto_fix=True to one line."""
    changes: list[str] = []
    new_line = line
    is_test = "tests" in path.parts or path.name.startswith("test_")

    for rule in cfg.replace:
        if not rule.auto_fix:
            continue
        if not rule.include_tests and is_test:
            continue
        compiled = compile_pattern_regex(rule.pattern, rule.case_sensitive, rule.word_boundary, rule.regex)
        if compiled is None:
            continue
        updated, count = compiled.subn(lambda _match, repl=rule.replacement: repl, new_line)
        if count > 0:
            new_line = updated
            changes.append(f"Rule 91 (replaced '{rule.pattern}' -> '{rule.replacement}')")

    return new_line, changes
