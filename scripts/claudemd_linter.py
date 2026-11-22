"""Lint Python, Web, Systems code, and Markdown files for AI-writing signs and code standards.
Includes git diff-scoped linting, incremental caching, parallel processing, and 300+ AI guards.
"""

import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.custom_linter import (  # noqa: 12
    CUSTOM_CONFIG_FILENAME,
    CUSTOM_EXAMPLE_FILENAME,
    CustomLinterConfig,
    filter_overridden_violations,
    is_ignored_by_custom_config,
    load_custom_linter_config,
    scan_custom_rules_for_file,
)
from scripts.repo_standards_rules import detect_repo_standard_issues  # noqa: 12
from scripts.tools_config import load_tools_config  # noqa: 12
from scripts.ui_adapters import get_all_adapters  # noqa: 12
from scripts.ui_config import load_ui_config  # noqa: 12
from scripts.ui_engine import build_manifest, evaluate_evidence_rules, evaluate_static_rules  # noqa: 12
from scripts.ui_evidence import load_ui_evidence  # noqa: 12
from scripts.utils import detect_android_release_issues  # noqa: 12

REPORT_PATH = Path(__file__).parent / "lint_report.txt"
CACHE_PATH = Path(__file__).parent / ".lint_cache.json"

# Reason codes and legend
LEGEND = {
    1: "Em dash present. Rewrite the sentence fully; do not just swap punctuation.",
    2: "Non-standard unicode character (curly quote, ellipsis, en dash, nbsp, etc). Replace with plain ASCII.",
    3: "Emoji present. Remove entirely.",
    4: "AI-style filler/transition/hype phrase. Delete or rewrite plainly.",
    5: "Negative-parallelism construction ('not X, it's Y' / 'not just X but Y'). Rewrite as a direct statement.",
    6: "Vague/unsupported attribution ('some argue', 'studies show'). Replace with a specific, sourced statement or delete.",
    7: "Reasoning/history comment (explains why or references old behavior). Rewrite to state only what the code does now.",
    8: "Backwards-compatibility / legacy / deprecated construct. Delete the shim; there is only one version.",
    9: "Bare except clause. Specify the exception type(s).",
    10: "Bare 'pass' as the entire body of a function/except block. Implement it or raise NotImplementedError.",
    11: "Missing type hint(s) on function signature. Add parameter and return annotations.",
    12: "Import not at top of file. Move it to the top-level import block.",
    13: "Import performed inside a function body. Move to top unless justified with # noqa.",
    14: "Mutable default argument. Use None as the sentinel and assign inside the function.",
    15: "Uses '== None' / '!= None'. Use 'is None' / 'is not None'.",
    16: "String formatting via .format() or % where an f-string would work. Convert to an f-string.",
    17: "Comment block longer than 2 lines without a long-comment marker. Condense to <= 2 lines.",
    18: "Docstring excessively long. Shorten while keeping it clear.",
    19: "Excessive boldface/title-case heading pattern typical of AI-generated docs. Rewrite plainly.",
    20: "Duplicate/near-duplicate code block. Consolidate into a single reusable function.",
    21: "Unused function, method, or import. Remove it or suppress with # noqa: 21.",
    22: "Import performed inside try/except block. All dependencies should exist via uv; move import to top level.",
    23: "Tooltip text passed as a literal string. Import it from a master tooltip list (or per-tool sub-list) instead of writing the string inline.",
    24: "TODO/FIXME/HACK/XXX comment left in code. Resolve it or file a tracked issue and remove the comment.",  # noqa: 91
    25: "Leftover print() call. Use logging or remove the debug statement.",
    26: "Hardcoded absolute filesystem path. Use a relative path or a configured constant.",
    27: "Exception caught and replaced with a different, unrelated exception without 'raise ... from'. Chain it or preserve the original.",
    28: "Hardcoded hex color literal outside the theme module. Use the theme palette instead.",
    29: "Dead file: nothing in the scanned tree imports it. Delete it or suppress with # noqa: 29 (whole-folder scan only).",
    30: "Circular import: this file participates in an import cycle. Break the cycle (whole-folder scan only).",
    31: "Raw QSpinBox/QDoubleSpinBox usage. Use a no-scroll, no-arrows wrapper widget instead (accidental wheel-scroll changes the value).",
    32: "OS-specific API/command used in a function not scoped to one platform by name. Add the other platforms' equivalent nearby, rename the function to flag it as platform-exclusive (e.g. _thing_windows), or suppress with # noqa: 32.",
    33: "Word-wrapped QLabel inside a dialog/wizard shows instructional/status text but has no setTextInteractionFlags call anywhere in that class. Make it selectable (TextSelectableByMouse) or suppress with # noqa: 33.",
    34: "setDecimals() called with a low literal on a spin box. This hardcodes precision and silently truncates whatever the user types. Remove the call (NoScrollDoubleSpinBox already defaults to its MAX_DECIMALS) or suppress with # noqa: 34 if the field is genuinely fixed-precision (e.g. currency).",
    35: "Button/box widget (QPushButton, QToolButton, QCheckBox, QRadioButton, QComboBox, QAction, spin box) has no setToolTip call anywhere in its class. Add one (via get_tooltip_for) or suppress with # noqa: 35.",
    36: "LLM internal metadata bug or citation artifact (oaicite, [cite: X], 【X】, turn0search0, utm_source=chatgpt). Remove artifact entirely.",
    37: "Conversational AI filler or salutation ('certainly!', 'here is the updated', 'hope this helps'). Remove conversational filler.",
    38: "Non-descriptive or generic variable name (single-letter or vague identifier). Use a descriptive identifier.",
    39: "Collapsed complex equation (un-decomposed multi-operation formula) or developer typo/misspelling.",
    40: "AI docstring bloat on simple function (Args/Returns on short helpers) or standard linter violation (ruff).",
    41: "Heavy AI divider banners (######, ======). Remove or replace with simple comment.",
    42: "Cryptic micro-optimization in loop or comprehension (nested walrus / multi-conditional generator).",
    43: "Duplicate string or integer keys in dictionary literals.",
    44: "Artificial equation line break (splitting expression across lines unnecessarily when under 140 chars).",
    45: "Over-engineered OOP in numerical code (unnecessary ABC/metaclass for simple mathematical POD).",
    46: "Control without stable ID matching id_pattern. Assign a unique stable ID (screen.action format).",
    47: "Control never pressed with real input in evidence (or missing ui_evidence.json for project with UI).",
    48: "Test bypasses the UI under ui_globs (calling handler directly, emitting signal, force: true).",
    49: "No assertion after interaction in UI test function. Require at least one non-trivial assertion.",
    50: "Enabled and disabled states not both exercised for control marked can_disable in manifest.",
    51: "Combination gap. Missing required ordered pairs, ordered triples, or state vectors in ui_evidence.json.",
    52: "Tooltip registry hygiene: orphan entry, duplicate text, or style violation.",
    53: "Layout failure in evidence: element overlap, clipping, truncation, occlusion, or off-screen bounds.",
    54: "Layout hazard in source: fixed geometry, position: absolute, or overflow clip without scroll container.",
    55: "Missing accessible name: icon-only control or input lacking accessible label or contentDescription.",
    56: "Target below minimum touch size (24x24 px web, 44x44 pt iOS, 48x48 dp Android).",
    57: "Contrast failure in theme tokens: foreground/background pair fails WCAG minimum ratio.",
    58: "Design token literal: hardcoded pixel, dp, sp, or dimension literal outside theme module.",
    59: "User-visible string literal: label, title, or message hardcoded inline outside strings module.",
    60: "Sentence built by string concatenation or f-string assembly. Use translation templates.",
    61: "Raw exception text or traceback shown directly to user in dialog or alert.",
    62: "Blocking call in UI handler: time.sleep, synchronous HTTP, or subprocess execution on UI thread.",
    63: "Missing global exception hook or visible error surface (sys.excepthook, qInstallMessageHandler).",
    64: "Keyboard operability failure: positive tabindex, NoFocus on interactive control, or unhandled click.",
    65: "Shortcut conflict: duplicate keyboard shortcut bound in same scope or system shortcut shadowed.",
    66: "Dialog defaults: dialog missing default button, enter submission, or escape cancellation.",
    67: "Destructive action without confirmation or undo capability.",
    68: "Double submit: submit-like control lacks debouncing or in-flight disabled state.",
    69: "Elided or truncated text lacks full-text tooltip in registry.",
    70: "Window bounds hazard: top-level window missing minimum size or unrestricted multi-monitor restore.",
    71: "Latency budget exceeded: interaction response time exceeds 100 ms frame threshold.",
    72: "Memory leak detected: live widget/node count fails to return to baseline after open/close cycles.",
    73: "Startup flash or missing skeleton during delayed application initialization.",
    74: "Missing state matrix: view with asynchronous data loading lacks registered state variants.",
    75: "Reduced motion preference ignored: animations lack toggle or prefers-reduced-motion media query.",
    76: "Disabled control lacks visible or accessible explanation in tooltip registry.",
    77: "Locale and scale matrix not run: missing pseudo-locale, right-to-left, or font scale test cells.",
    78: "Bridge mismatch: exposed backend method uncalled or frontend calls undefined bridge channel.",
    79: "Label style inconsistency: mixed casing, trailing periods, or inconsistent action verbs.",
    80: "Literal Unicode escape sequence (e.g. \\u00D7) rendered literally in JSX/HTML text. Use the actual UTF-8 character (×) or a JS string expression.",
    81: "Unguarded mutating click handler in view-only component. Gate with an explicit edit mode state or confirmation.",
    82: "Silent fallback pass-through in domain transformer. Fallback to parsing raw text rather than returning unparsed strings silently.",
    83: "Unbounded option chip collection. Map over dynamic collections using <select>, pagination, or search instead of raw buttons.",
    84: "Unreset browser control styling or missing dark color-scheme in root CSS. Declare color-scheme: dark and button background reset.",
    85: "Sub-legible micro-typography (< 11px) in UI or SVG. Use >= 12px (text-xs) for readable UI text.",
    86: "Unchecked SVG text map collision. Guard mapped <text> nodes inside <svg> against bounding-box overlap.",
    87: "Stale embedded frontend bundle or release binary. Rebuild dist/ assets and executable after source edits.",
    88: "Desktop local-server entrypoint missing lifecycle handlers (shutdown/heartbeat, console close, or --self-test).",
    89: "Release workflow triggers only on tags without push/pull_request coverage, uses a static 'latest' tag_name, signs Android release with debug key or allows cleartext traffic, or leaves superseded root scripts.",
    90: "Ambiguous mass unit ('tons', 'ton', or bare 't') in UI display. Use explicit 'lbs' or 'kg'.",
    91: "Custom user linter rule violation (banned term/pattern in linter_custom.yaml). Remove or replace the flagged pattern.",
    92: "Unsafe dynamic code execution (eval, exec, or shell=True with formatted string). Use safe AST evaluation or shlex quoting.",
    93: "Insecure deserialization or YAML loading (yaml.load without SafeLoader or pickle.loads). Use yaml.safe_load or safe formats.",
    94: "SQL injection hazard (raw string interpolation or f-string in SQL query). Use parameterized query execution.",
    95: "Hardcoded secret or credential token (API key, token, or private key). Load credentials from environment variables.",
    96: "Phantom or tautological test assertion (assert True, assert 1 == 1, or empty test body). Write verifiable assertions.",
    97: "AI hallucinated placeholder token (your_api_key_here, todo_insert_key, fake_token). Replace with genuine config.",
    98: "Accessibility or UI structure hazard in web component (img without alt, button without type, map without key).",
    99: "AI deferred stub in production code (TODO: implement, AI placeholder, or incomplete implementation).",
    100: "Hallucinated or invalid standard library import (non-existent module or incorrect type import).",
    101: "Missing required repo standard file (README.md, LICENSE, SECURITY.md, THIRD_PARTY_NOTICES.md, AGENTS.md, docs/USER_GUIDE.md, docs/DEVELOPMENT.md, ci.yml) or banned root clutter present.",
    102: "README.md violates canonical user-first layout (<=120 lines, assets/logo.png, ## Download, ## Screenshots with real local images, ## Safety & Disclaimers, bottom ## Documentation ordered User -> Developer -> Legal).",
    103: "README.md leaks internal engineering details (checksums/SHA256SUMS, CI/CD workflow prose, git clone, test runners, or build commands).",
    104: "Markdown file uses unlinked backticked doc filename or docs/*.md lacks a '## Related Documentation' footer linking back to ../README.md.",
    105: "README.md ## Download table duplicates platforms or offers multiple assets per single platform without compatibility waiver.",
    106: "Missing conditional companion guide (docs/APK_INSTALLATION.md, docs/INSTALLATION.md, docs/UV_INSTALLATION.md, or docs/OPENFOAM_INSTALLATION.md).",
    107: "Dual branding missing or identical: assets/logo.png and cropped text-free assets/icon.png (plus .ico for Windows) must both exist and differ.",
    108: "CI/CD parity violation: require single .github/workflows/ci.yml with push+PR triggers, no paths-ignore on docs, strict linter + link checker, and semantic vX.Y.Z release (prerelease: false, make_latest: true).",
    109: "License or security policy inconsistency: LICENSE must be MIT (Copyright (c) 2026 DontKwo) and SECURITY.md must cover main-only releases and fork warnings.",
    110: "Installation or developer guide missing explicit per-platform headings (### Windows, ### macOS, ### Linux).",
    111: "Disallowed desktop GUI toolkit import (tkinter, PyQt5/6, PySide2/6, wx). Use the unified WebView architecture.",
    112: "Desktop binary build missing --self-test verification flag in CI or entrypoint.",
}

TOOLTIP_TARGET_CLASSES = {
    "QPushButton", "QToolButton", "QCheckBox", "QRadioButton",
    "QComboBox", "QAction", "NoScrollSpinBox", "NoScrollDoubleSpinBox",
    "ClickableImagePreview",
}

DIALOG_BASE_NAMES = {"QDialog", "QWizard", "QWizardPage"}
SPINBOX_EXEMPT_FILES = {"spinbox.py"}
SPINBOX_MAX_DECIMALS = 10
PLATFORM_NAME_KEYWORDS = ("windows", "win32", "linux", "macos", "darwin", "posix")

OS_SPECIFIC_RE = re.compile(
    r"winreg|ctypes\.windll|os\.startfile|win32com|win32api|win32con|pywintypes|"
    r"HKEY_CURRENT_USER|HKEY_LOCAL_MACHINE|SHOpenWithDialog|"
    r"AppKit|NSWorkspace|CoreFoundation|LaunchServices|"
    r"xdg-mime|xdg-open|osascript|duti|launchctl|defaults write|reg\.exe",
    re.IGNORECASE,
)

# Supported file extensions and excluded paths
SUPPORTED_EXTENSIONS = {
    ".py", ".md", ".txt", ".rst",
    ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs",
    ".html", ".htm", ".css", ".scss", ".vue", ".svelte",
    ".rs", ".go", ".c", ".cpp", ".cc", ".cxx", ".h", ".hpp",
    ".sh", ".bash", ".zsh",
    ".ui", ".qml", ".xml", ".kt", ".dart", ".swift", ".kv", ".tcss", ".xaml", ".axaml",
}

EXCLUDED_DIRS = {
    ".venv", "venv", ".toolchain", "node_modules", ".git", "__pycache__",
    ".pytest_cache", ".mypy_cache", "dist", "build", ".next", ".nuxt",
    ".cache", "target", "vendor", ".ai_checkpoints",
}

# Section 1: AI-writing signatures
UNICODE_BAD = {
    "\u2014": 1,  # em dash
    "\u2013": 2,  # en dash
    "\u2018": 2, "\u2019": 2,  # curly single quotes
    "\u201c": 2, "\u201d": 2,  # curly double quotes
    "\u2026": 2,  # ellipsis
    "\u00a0": 2,  # nbsp
    "\u200b": 2,  # zero-width space
    "\ufeff": 2,  # BOM
    "\u2022": 2,  # bullet
    "\u2032": 2, "\u2033": 2,  # prime marks
    "\u00ad": 2,  # soft hyphen
}

EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0001F1E6-\U0001F1FF"
    "\U00002190-\U000021FF"
    "\U00002B00-\U00002BFF"
    "]"
)

# Comprehensive guards against AI writing (Over 300 specific phrases derived from
# Wikipedia:Signs_of_AI_writing and academic LLM vocabulary studies)
AI_PHRASES = [
    # --- Copulative Avoidance & Fake Linking ---
    "serves as a", "serves as an", "serves as the", "stands as a", "stands as an",
    "stands as the", "functions as a", "functions as an", "operates as a", "operates as an",
    "marks a pivotal", "marks a significant", "marks the beginning", "marks the transition",
    "represents a pivotal", "represents a significant", "represents a major",
    "acts as a cornerstone", "acts as a beacon", "acts as a testament", "acts as a catalyst",
    "serves to highlight", "serves to underscore", "serves to illustrate", "serves to demonstrate",
    "boasts a wide", "boasts an impressive", "boasts a diverse", "boasts a rich",
    "boasts features", "boasts state-of-the-art", "boasts a", "boasts an", "boasts the",
    "aligns with the", "align with the", "resonates with", "resonate with",
    "cultivating a", "cultivating an", "cultivating the", "fostering a", "fostering an",
    "symbolizing its ongoing", "symbolizing its enduring", "symbolizing its lasting",
    "reflects the ongoing", "underscores the enduring", "bolstered by", "bolstering the",

    # --- Significance, Legacy & Historical Inflation ---
    "pivotal moment", "pivotal role", "pivotal turning point", "pivotal milestone",
    "enduring legacy", "lasting legacy", "indelible mark", "indelible impression",
    "transformative power", "transformative impact", "transformative era",
    "rich tapestry", "intricate tapestry", "cultural tapestry", "historical tapestry",
    "testament to the", "stands as a testament", "serves as a testament", "living testament",
    "solidify its role", "solidified its role", "solidify its place", "solidified its status",
    "cementing its status", "cemented its place", "cementing its reputation",
    "carved out a niche", "carving out a niche", "beacon of hope", "beacon of innovation",
    "cornerstone of modern", "cornerstone of the", "linchpin of the", "bedrock of modern",
    "watershed moment", "heralded a new", "ushered in a new", "ushering in an era",
    "left an indelible", "resonant legacy", "defining chapter", "golden age of",

    # --- Broader Movement, Debates & Vague Connections ---
    "part of a broader movement", "part of a larger trend", "reflects a broader shift",
    "contributes to the broader", "contribute to the broader", "broader reflection on",
    "prompts broader reflection", "prompted broader reflection", "generated debate about",
    "generated considerable debate", "sparked discussion on", "sparked intense debate",
    "raising philosophical questions", "raises important questions", "shaped emerging policy",
    "shaping the discourse", "participated in public discussions", "intertwined with the",
    "inextricably linked", "deeply intertwined", "closely tied to the broader",
    "situated at the intersection", "at the crossroads of", "at the nexus of",
    "a delicate balance between", "striking a balance between", "a dynamic interplay",
    "intricate dynamics", "intricacies of", "symbiotic relationship", "symbiotic interplay",

    # --- Hype, Puffery & Promotional Clichés ---
    "groundbreaking", "cutting-edge", "game-changer", "game changer", "revolutionary",
    "state-of-the-art", "world-class", "unparalleled", "unrivaled", "second to none",
    "unwavering commitment", "unwavering dedication", "unwavering support",
    "meticulously crafted", "meticulously designed", "meticulously planned", "meticulous attention to",
    "robust solution", "robust framework", "robust architecture", "robust ecosystem",
    "holistic approach", "holistic view", "holistic perspective", "paradigm shift",
    "synergy", "synergies", "synergistic", "unlock the potential", "unlocking the potential",
    "unleash the power", "unleashing the potential", "harness the power", "harnessing the power",
    "empower users", "empowering individuals", "spearheaded the", "spearheading the",
    "trailblazing", "visionary leadership", "seamless integration", "seamlessly integrated",
    "seamlessly blends", "seamlessly connects", "seamlessly navigates", "bespoke solution",
    "breathtaking", "awe-inspiring", "tour de force", "redefining the landscape",
    "supercharge your", "elevate your workflow", "quantum leap", "poised to revolutionize",
    "poised to", "poised for",

    # --- Filler Transitions & Structural Clichés ---
    "in summary,", "in conclusion,", "to summarize,", "to sum up,", "overall,",
    "all in all,", "at its core,", "in essence,", "needless to say,", "it goes without saying",
    "with that said,", "with that being said,", "that being said,", "all things considered,",
    "at the end of the day,", "first and foremost,", "last but not least,", "in light of these",
    "shed light on", "sheds light on", "shedding light on", "delve into", "delving into",
    "dive into", "dive deep into", "deep dive into", "let's dive in", "without further ado",
    "navigate the complexities", "navigating the complexities", "navigate the landscape",
    "navigating the turbulent", "multifaceted nature", "multifaceted approach",
    "myriad of", "a plethora of", "invaluable asset", "far-reaching implications",
    "far-reaching consequences", "bustling hub", "vibrant community", "nestled in the",
    "in today's world", "in today's fast-paced", "in today's digital age", "in an ever-changing",
    "in an ever-evolving", "fast-paced world", "digital landscape", "the landscape of",
    "in the realm of", "in the world of", "when it comes to", "it remains to be seen",
    "only time will tell", "cannot be overstated", "cannot be overlooked",
    "stands out as a", "serves as a reminder", "a stark reminder",
    "furthermore,", "moreover,", "additionally,", "notably,", "crucially,",
    "future prospects", "looking ahead,", "challenges and opportunities",
    "as of my last update", "as of my knowledge cutoff",

    # --- Hedging & Attribution Inflation ---
    "it's important to note", "it is important to note", "it's worth noting", "it is worth noting",
    "it is crucial to remember", "it is vital to understand", "it should be noted that",
    "one must consider", "plays a crucial role", "plays a vital role", "plays a pivotal role",
    "plays a key role", "plays an essential role", "plays a fundamental role",
    "underscores the importance", "underscoring the importance", "highlights the importance",
    "highlighting the need", "emphasizes the importance", "emphasizing the need",
    "widely regarded as", "critically acclaimed", "received widespread acclaim",
    "garnered significant attention", "garnered widespread praise", "heralded as a",
    "lauded for its", "celebrated for its", "renowned for its",
]

# Rule 5: Negative Parallelism ("Not just X, but Y", "Y rather than X")
NEGATIVE_PARALLELISM_RE = re.compile(
    r"\b(?:not\s+(?:only\s+|just\s+)?[a-z0-9 ]{2,40},?\s*(?:but\s+(?:also\s+)?|it'?s\s+|it\s+is\s+)|[a-z0-9 ]{2,30}\s+rather\s+than\s+[a-z0-9 ]{2,30})\b",
    re.IGNORECASE,
)

# Rule 36: LLM Internal Metadata & Citation Bugs
AI_METADATA_RE = re.compile(
    r":contentReference\[oaicite:\d+\]|"
    r"\[oai_citation:\d+[^\]]*\]|"
    r"\[cite:\s*\d+\]|"
    r"\[span_\d+\]\(start_span\)|"
    r"\bturn0search0\b|"
    r"\battributableIndex\b|"
    r"\bgrok_card\b|"
    r"\bgrok_render_citation_card\b|"
    r"\bppl-ai-file-upload\b|"
    r"【\d+†source】|【\d+】|"
    r":::writing\b|"
    r"utm_source=(?:chatgpt\.com|openai)|"
    r"https?://(?:www\.)?google\.com/search\?q=",
    re.IGNORECASE,
)

# Rule 37: Conversational AI Salutations & Assistant Boilerplate
CONVERSATIONAL_AI_PHRASES = [
    "certainly! here", "certainly, here", "sure thing!", "hope this helps!", "hope this helps.",
    "feel free to ask", "feel free to reach out", "let me know if you have", "let me know if you need",
    "as an ai language model", "as a large language model", "as an ai,", "as an artificial intelligence",
    "as requested, here", "here is the updated code", "here is the complete code",
    "let's explore", "let's take a closer look", "let's examine", "in the following sections,",
    "in this article, we will", "in this guide, we will", "in this section, we will delve",
]

VAGUE_ATTRIBUTION = [
    "some argue", "some believe", "many believe", "it is often said",
    "critics say", "experts say", "studies show", "research suggests",
    "some critics", "many experts", "widely believed that",
    "scholars agree", "observers note",
]

REASONING_COMMENT_PHRASES = [
    "this was changed", "previously,", "used to ", "now we ",
    "originally,", "in the past,", "we changed", "we used to",
    "old behavior", "old version", "no longer ", "this used to",
    "this is because", "the reason", "this fixes", "this was because",
]

COMPAT_PHRASES = [
    "backwards compatible", "backward compatible", "backwards compatibility",
    "backward compatibility", "legacy", "deprecated", "for compatibility",
    "still support", "keep for now", "old version", "maintain compatibility",
    "shim", "fallback for old", "support old", "legacy support",
    "compat layer", "compatibility layer",
]

# Rule 38: Non-descriptive / generic variable names and domain shorthand
VAGUE_VAR_NAMES = {
    "temp", "tmp", "val", "ret", "foo", "bar", "baz", "dummy", "stuff", "thing",
}
ALLOWED_SHORT_VARS = {
    "_", "i", "j", "k", "x", "y", "z", "e", "f", "m", "n", "p", "t", "v", "w",
    "a", "b", "c", "d", "g", "h", "q", "r", "s", "u",
    "T", "P", "A", "F", "V", "Q", "W", "H", "S", "U", "K", "L", "D",
    "gam", "cp", "Cp", "R", "M", "T04", "T03", "T0a", "Ta", "P05_P04", "p0_px",
    "p_rat", "PR", "TSFC", "ISP", "GLOW", "TW0", "dV", "m_prop", "m_inert",
    "m0", "v_i", "v_h", "mu", "nt", "Tmax", "c4", "s4", "s2_c2", "exp", "sqr",
    "num", "denom", "term1", "term2", "term3", "term_axial", "term_coupling",
    "term_transverse", "expansion_term",
}

# Rule 39: Common spelling mistakes and typos
TYPO_PATTERNS = {
    "recieve": "receive", "recieved": "received", "seperate": "separate",
    "seperated": "separated", "definately": "definitely", "occured": "occurred",
    "occurance": "occurrence", "dependancy": "dependency", "compatability": "compatibility",
    "paramater": "parameter", "arguement": "argument", "neccessary": "necessary",
    "untill": "until", "wierd": "weird", "truely": "truly", "maintainance": "maintenance",
    "modifed": "modified", "calback": "callback", "synchornize": "synchronize",
    "insteuctions": "instructions", "evrry": "every", "autoamtically": "automatically",
    "ahrdcoded": "hardcoded",
}

# Rules 41 & 43 Engineering checks
AI_BANNER_RE = re.compile(r"^(?:#|//|\*)\s*([#=]{5,})\s*$|^([#=]{5,})\s*$")
CALC_NAME_KEYWORDS = (
    "thrust", "isp", "tsfc", "delta_v", "glow", "mach", "enthalpy",
    "entropy", "reynolds", "trajectory", "orbit", "stage_mass", "prop_mass",
)
PHYSICAL_CONST_NAMES = {
    "PRESSURE", "TEMP", "TEMPERATURE", "THRUST", "MASS", "WEIGHT",
    "LENGTH", "VELOCITY", "SPEED", "DENSITY", "ALTITUDE", "RADIUS", "DIAMETER",
}
UNIT_SUFFIXES = (
    "_M", "_MM", "_CM", "_IN", "_FT", "_MI", "_KM",
    "_KG", "_G", "_LB", "_LBF",
    "_S", "_MIN", "_HR", "_HZ",
    "_DEG", "_RAD",
    "_PA", "_KPA", "_PSI", "_BAR",
    "_J", "_W", "_KW", "_WH", "_HP",
    "_MPH", "_KTS", "_RPM", "_LBIN", "_LBFT",
)
UNIT_COMMENT_RE = re.compile(
    r"#\s*(?:[A-Za-z0-9_\^/·\-°]+|ft/s\^2|J/kg|K|Pa|psi|bar|kg|lb|m|s|deg|rad)\b",
    re.IGNORECASE,
)

# Configurable verification levels
LEVEL_RULES: dict[str, set[int]] = {
    "standard": {
        1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
        14, 15, 16, 17, 18, 19, 22, 24, 27,
        36, 37, 40, 41, 44, 80, 91,
        92, 93, 94, 95, 96, 97, 99, 100,
    },
    "strict": {
        1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
        14, 15, 16, 17, 18, 19, 22, 24, 26, 27,
        36, 37, 38, 39, 40, 41, 42, 43, 44, 45,
        46, 47, 48, 49, 54, 80, 81, 82, 83,
        84, 85, 86, 87, 88, 89, 90, 91,
        92, 93, 94, 95, 96, 97, 98, 99, 100,
        101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112,
    },
    "full": set(range(1, 113)),
}

HEADING_RE = re.compile(r"^#{1,6}\s+(.+)$")
NOQA_RE = re.compile(
    r"#\s*noqa(?::\s*([\d,\s]+))?|"
    r"//\s*noqa(?::\s*([\d,\s]+))?|"
    r"<!--\s*noqa(?::\s*([\d,\s]+))?\s*-->",
    re.IGNORECASE,
)
LONG_OK_RE = re.compile(r"(?:#|//)\s*long-comment-ok", re.IGNORECASE)
TODO_RE = re.compile(r"(?:#|//|/\*)\s*(TODO|FIXME|HACK|XXX)\b", re.IGNORECASE)  # noqa: 91
HARDCODED_PATH_RE = re.compile(r"^[A-Za-z]:[\\/]|^/(home|Users)/")
HEX_COLOR_RE = re.compile(r"^#(?:[0-9A-Fa-f]{3}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})$")

# Multilingual debug prints / console output
DEBUG_PATTERNS = [
    re.compile(r"\bconsole\.(?:log|debug|info)\s*\("),      # JS/TS
    re.compile(r"\bfmt\.Print(?:ln|f)?\s*\("),              # Go
    re.compile(r"\b(?:println!|eprintln!|dbg!)\s*\("),       # Rust
    re.compile(r"\bstd::cout\s*<<"),                        # C++
]

# Security credential patterns (Code 95)
SECRET_PATTERNS = [
    re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}\b"),
    re.compile(r"\bsk-(?:proj-|live-)?[a-zA-Z0-9_-]{24,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"-----BEGIN\s+(?:RSA|DSA|EC|OPENSSH)?\s*PRIVATE\s+KEY-----"),
]

# AI placeholder and stub patterns (Codes 97 & 99)
AI_PLACEHOLDER_RE = re.compile(
    r"\b(?:your[_-]api[_-]key[_-]here|insert[_-]api[_-]key|todo[_-]insert|"
    r"your[_-]token[_-]here|fake[_-]token|sk-placeholder)\b",
    re.IGNORECASE,
)
AI_STUB_RE = re.compile(
    r"(?:#|//)\s*(?:ai(?:\s+generated)?\s+placeholder|will\s+implement\s+later|"
    r"todo:?\s*implement\s+(?:this|later)|placeholder\s+for\s+future)\b",
    re.IGNORECASE,
)

# Web and JSX accessibility patterns (Code 98)
IMG_MISSING_ALT_RE = re.compile(r"<img\b(?![^>]*\balt=)[^>]*>", re.IGNORECASE)
BUTTON_MISSING_TYPE_RE = re.compile(r"<button\b(?![^>]*\btype=)[^>]*>", re.IGNORECASE)

# Known hallucinated or invalid stdlib imports (Code 100)
HALLUCINATED_IMPORTS: dict[str, set[str]] = {
    "typing": {"String", "Integer", "Boolean", "Float", "Array", "Map", "Number"},
    "asyncio": {"coroutine"},
    "urllib": {"request_handler"},
}


def noqa_codes(line: str) -> set[int] | str | None:
    m = NOQA_RE.search(line)
    if not m:
        return None
    codes_str = m.group(1) or m.group(2) or m.group(3)
    if not codes_str:
        return "ALL"
    return {int(code_num) for code_num in re.findall(r"\d+", codes_str)}


def suppressed(line: str, code: int | None) -> bool:
    codes = noqa_codes(line)
    if codes is None:
        return False
    return codes == "ALL" or (code is not None and code in codes)


def scan_text_line(path: Path, lineno: int, line: str, violations: list[tuple[Path, int, int]]) -> None:
    if suppressed(line, None):
        return

    # Linter self-hosting: do not flag the linter's own pattern definitions
    if path.name == "claudemd_linter.py" and lineno <= 500:
        return

    # Spell checker dictionary definitions legitimately define typo mappings
    if path.name == "spell_checker.py" and lineno <= 80:
        return

    # Unit test fixtures legitimately contain prohibited sample patterns
    if "tests" in path.parts or path.name.startswith("test_"):
        return

    scan_line = line
    if path.suffix == ".md":
        scan_line = re.sub(r"`[^`]*`", "", line)

    for ch, code in UNICODE_BAD.items():
        if ch in scan_line and not suppressed(line, code):
            violations.append((path, lineno, code))
    if EMOJI_RE.search(scan_line) and not suppressed(line, 3):
        violations.append((path, lineno, 3))
    low = scan_line.lower()
    for phrase in AI_PHRASES:
        if phrase in low and not suppressed(line, 4):
            violations.append((path, lineno, 4))
            break
    if NEGATIVE_PARALLELISM_RE.search(scan_line) and not suppressed(line, 5):
        violations.append((path, lineno, 5))
    for phrase in VAGUE_ATTRIBUTION:
        if phrase in low and not suppressed(line, 6):
            violations.append((path, lineno, 6))
            break
    for phrase in REASONING_COMMENT_PHRASES:
        if phrase in low and not suppressed(line, 7):
            violations.append((path, lineno, 7))
            break
    for phrase in COMPAT_PHRASES:
        if phrase in low and not suppressed(line, 8):
            violations.append((path, lineno, 8))
            break
    if AI_METADATA_RE.search(scan_line) and not suppressed(line, 36):
        violations.append((path, lineno, 36))
    for phrase in CONVERSATIONAL_AI_PHRASES:
        if phrase in low and not suppressed(line, 37):
            violations.append((path, lineno, 37))
            break
    if TODO_RE.search(line) and not suppressed(line, 24):
        violations.append((path, lineno, 24))
    for typo in TYPO_PATTERNS:
        if re.search(r"\b" + typo + r"\b", low) and not suppressed(line, 39):
            violations.append((path, lineno, 39))
            break

    # Rule 41: Heavy AI divider banners
    if path.suffix not in (".md", ".txt", ".rst"):
        if AI_BANNER_RE.search(line) and not suppressed(line, 41):
            violations.append((path, lineno, 41))

    # Multi-language leftover debug print check (Code 25)
    if path.suffix not in (".py", ".md", ".txt"):
        for pattern in DEBUG_PATTERNS:
            if pattern.search(line) and not suppressed(line, 25):
                violations.append((path, lineno, 25))
                break

    # Rule 95: Hardcoded credentials or tokens
    if path.suffix not in (".md", ".txt", ".rst") and "example" not in path.name.lower():
        for pattern in SECRET_PATTERNS:
            if pattern.search(line) and not suppressed(line, 95):
                violations.append((path, lineno, 95))
                break

    # Rule 97: AI hallucinated placeholders
    if "example" not in path.name.lower() and path.suffix not in (".md", ".txt", ".rst"):
        if AI_PLACEHOLDER_RE.search(line) and not suppressed(line, 97):
            violations.append((path, lineno, 97))

    # Rule 98: Web / JSX accessibility
    if path.suffix in (".jsx", ".tsx", ".html", ".vue", ".svelte"):
        if IMG_MISSING_ALT_RE.search(line) and not suppressed(line, 98):
            violations.append((path, lineno, 98))
        if BUTTON_MISSING_TYPE_RE.search(line) and not suppressed(line, 98):
            violations.append((path, lineno, 98))

    # Rule 99: AI deferred stubs in production code
    if path.suffix not in (".md", ".txt", ".rst") and "tests" not in path.parts and not path.name.startswith("test_"):
        if AI_STUB_RE.search(line) and not suppressed(line, 99):
            violations.append((path, lineno, 99))


def scan_markdown_headings(path: Path, lines: list[str], violations: list[tuple[Path, int, int]]) -> None:
    if _check_noqa_in_file(path, 1, 19):
        return
    bold_or_title_count = 0
    prev_level = 0
    in_code_block = False

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        m = HEADING_RE.match(stripped)
        if m:
            text = m.group(1)
            level = len(line) - len(line.lstrip("#"))
            if prev_level > 0 and level > prev_level + 1:
                if not suppressed(line, 19):
                    violations.append((path, i, 19))
            prev_level = level

            words = text.replace("*", "").split()
            if "**" in text or ("#" in text):
                bold_or_title_count += 1
            elif len(words) >= 4 and sum(1 for w in words if w[:1].isupper()) / len(words) > 0.8:
                bold_or_title_count += 1

    if bold_or_title_count >= 5 and not _check_noqa_in_file(path, 1, 19):
        violations.append((path, 0, 19))


def scan_comment_blocks(path: Path, lines: list[str], violations: list[tuple[Path, int, int]]) -> None:
    i = 0
    n = len(lines)
    comment_prefixes = ("#", "//") if path.suffix != ".py" else ("#",)

    while i < n:
        line = lines[i]
        stripped = line.strip()
        is_comment = any(stripped.startswith(p) for p in comment_prefixes) and not stripped.startswith("#!")
        if is_comment:
            block_start = i
            skip = LONG_OK_RE.search(line) is not None
            j = i
            while j < n and any(lines[j].strip().startswith(p) for p in comment_prefixes):
                if LONG_OK_RE.search(lines[j]):
                    skip = True
                j += 1
            block_len = j - block_start
            if block_len > 2 and not skip and not suppressed(lines[block_start], 17):
                violations.append((path, block_start + 1, 17))
            i = j
        else:
            i += 1


# Section 2: Duplicate code detection
def extract_function_bodies(source: str) -> dict:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}

    functions = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            body_lines = ast.get_source_segment(source, node)
            if body_lines:
                func_hash = hashlib.md5(body_lines.encode()).hexdigest()
                functions[func_hash] = (node.name, node.lineno, body_lines)
    return functions


def detect_duplicate_code(all_files_funcs: dict[Path, dict], violations: list[tuple[Path, int, int]]) -> None:
    hash_to_occurrences = defaultdict(list)
    for fpath, funcs in all_files_funcs.items():
        for func_hash, (fname, lineno, body) in funcs.items():
            hash_to_occurrences[func_hash].append((fpath, fname, lineno, body))

    for func_hash, occurrences in hash_to_occurrences.items():
        if len(occurrences) >= 2:
            for fpath, fname, lineno, body in occurrences:
                if not _has_noqa(body, 20):
                    violations.append((fpath, lineno, 20))


def _has_noqa(text: str, code: int) -> bool:
    match = NOQA_RE.search(text)
    if not match:
        return False
    codes_str = match.group(1) or match.group(2)
    if not codes_str:
        return True
    return code in {int(code_val) for code_val in re.findall(r"\d+", codes_str)}


# Section 3: Unused code detection
def detect_unused_code(files: list[Path], violations: list[tuple[Path, int, int]]) -> None:
    try:
        import vulture  # noqa: 22
    except ImportError:
        return

    py_files = [str(f) for f in files if f.suffix == ".py"]
    if not py_files:
        return

    try:
        v = vulture.Vulture()
        v.scavenge(py_files)
        for item in v.get_unused_code():
            fpath = Path(item.filename)
            lineno = item.first_lineno
            if not _check_noqa_in_file(fpath, lineno, 21):
                violations.append((fpath, lineno, 21))
    except Exception:
        return


def _check_noqa_in_file(fpath: Path, lineno: int, code: int) -> bool:
    try:
        lines = fpath.read_text(encoding="utf-8").splitlines()
        if not lines:
            return False
        if suppressed(lines[0], code):
            return True
        if 0 < lineno <= len(lines):
            return suppressed(lines[lineno - 1], code)
    except Exception:
        return False
    return False


# Section 4: Whole-repo import-graph checks (dead files, circular imports)
def _module_dotted_path(fpath: Path, root: Path) -> str:
    try:
        rel = fpath.relative_to(root)
    except ValueError:
        rel = Path(fpath.name)
    parts = list(rel.with_suffix("").parts)
    if parts and parts[0] == "src":
        parts = parts[1:]
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _is_type_checking_test(test: ast.AST) -> bool:
    if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
        return True
    return isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"


def _type_checking_guarded_ids(tree: ast.AST) -> set[int]:
    guarded = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and _is_type_checking_test(node.test):
            for sub in node.body:
                for inner in ast.walk(sub):
                    guarded.add(id(inner))
    return guarded


def detect_module_graph_issues(files: list[Path], root: Path, violations: list[tuple[Path, int, int]]) -> None:
    py_files = [f for f in files if f.suffix == ".py"]
    if len(py_files) < 2:
        return

    module_paths = {f: _module_dotted_path(f, root) for f in py_files}
    path_by_dotted = {dotted: f for f, dotted in module_paths.items()}
    imports_by_file = {}
    all_imported_names = set()

    for f in py_files:
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError, OSError):
            imports_by_file[f] = set()
            continue
        names = set()
        guarded_ids = _type_checking_guarded_ids(tree)
        for node in ast.walk(tree):
            if id(node) in guarded_ids:
                continue
            if isinstance(node, ast.Import):
                for alias in node.names:
                    names.add(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.add(node.module)
                for alias in node.names:
                    names.add(f"{node.module}.{alias.name}")
        imports_by_file[f] = names
        all_imported_names.update(names)

    graph = defaultdict(set)
    for f, names in imports_by_file.items():
        for mod in names:
            target = path_by_dotted.get(mod)
            if target is None:
                best_dotted = None
                for dotted, cand in path_by_dotted.items():
                    if cand is f:
                        continue
                    if mod.startswith(dotted + ".") or dotted.startswith(mod + "."):
                        if best_dotted is None or len(dotted) > len(best_dotted):
                            best_dotted = dotted
                            target = cand
            if target is not None and target is not f:
                graph[f].add(target)

    for f, dotted in module_paths.items():
        if f.name in ("__init__.py", "__main__.py", "main.py"):
            continue
        if f.name.startswith("test_") or f.name.endswith("_test.py"):
            continue
        if f.parent.name == "scripts":
            continue
        used = any(dotted == mod or mod.startswith(dotted + ".") or dotted.startswith(mod + ".") for mod in all_imported_names)
        if not used and not _check_noqa_in_file(f, 1, 29):
            violations.append((f, 1, 29))

    cyclic_files = set()
    visited = set()

    def dfs(node: Path, path_stack: list, on_stack: set) -> None:
        visited.add(node)
        path_stack.append(node)
        on_stack.add(node)
        for neighbor in graph.get(node, ()):
            if neighbor not in visited:
                dfs(neighbor, path_stack, on_stack)
            elif neighbor in on_stack:
                idx = path_stack.index(neighbor)
                cyclic_files.update(path_stack[idx:])
        path_stack.pop()
        on_stack.discard(node)

    for start in graph:
        if start not in visited:
            dfs(start, [], set())

    for f in cyclic_files:
        if not _check_noqa_in_file(f, 1, 30):
            violations.append((f, 1, 30))



def _check_ast_import_from(node: ast.ImportFrom, path: Path, line: str, lines: list[str], violations: list[tuple[Path, int, int]]) -> None:
    if path.name not in SPINBOX_EXEMPT_FILES:
        if any(alias.name in ("QSpinBox", "QDoubleSpinBox") for alias in node.names):
            if not suppressed(line, 31):
                violations.append((path, node.lineno, 31))
    if node.module in HALLUCINATED_IMPORTS:
        for alias in node.names:
            if alias.name in HALLUCINATED_IMPORTS[node.module]:
                if not suppressed(line, 100):
                    violations.append((path, node.lineno, 100))

def _check_ast_except_handler(node: ast.ExceptHandler, path: Path, line: str, lines: list[str], violations: list[tuple[Path, int, int]]) -> None:
    if node.type is None and not suppressed(line, 9):
        violations.append((path, node.lineno, 9))
    pass_line = lines[node.body[0].lineno - 1] if node.body and node.body[0].lineno - 1 < len(lines) else ""
    if len(node.body) == 1 and isinstance(node.body[0], ast.Pass) and not suppressed(line, 10) and not suppressed(pass_line, 10):
        violations.append((path, node.lineno, 10))
    caught_name = node.type.id if isinstance(node.type, ast.Name) else None
    for stmt in node.body:
        if isinstance(stmt, ast.Raise) and stmt.exc is not None and stmt.cause is None:
            raised_name = stmt.exc.func.id if isinstance(stmt.exc, ast.Call) and isinstance(stmt.exc.func, ast.Name) else None
            if raised_name and raised_name != caught_name:
                raise_line = lines[stmt.lineno - 1] if stmt.lineno - 1 < len(lines) else ""
                if not suppressed(raise_line, 27):
                    violations.append((path, stmt.lineno, 27))

def _check_ast_function_def(node: ast.FunctionDef, path: Path, line: str, lines: list[str], violations: list[tuple[Path, int, int]]) -> None:
    pass_line = lines[node.body[0].lineno - 1] if node.body and node.body[0].lineno - 1 < len(lines) else ""
    if len(node.body) == 1 and isinstance(node.body[0], ast.Pass) and not suppressed(line, 10) and not suppressed(pass_line, 10):
        violations.append((path, node.lineno, 10))
    if node.name.startswith("test_") and ("test" in path.name.lower() or "tests" in path.parts):
        if len(node.body) == 1 and isinstance(node.body[0], ast.Pass) and not suppressed(line, 96):
            violations.append((path, node.lineno, 96))
    missing = any(param_arg.annotation is None for param_arg in node.args.args if param_arg.arg != "self")
    if node.returns is None:
        missing = True
    if missing and not suppressed(line, 11):
        violations.append((path, node.lineno, 11))
    for default in node.args.defaults:
        if isinstance(default, (ast.List, ast.Dict, ast.Set)) and not suppressed(line, 14):
            violations.append((path, node.lineno, 14))
    docstring = ast.get_docstring(node)
    if docstring and docstring.count("\n") > 6 and not suppressed(line, 18):
        violations.append((path, node.lineno, 18))
    if docstring and len(node.body) <= 5:
        if re.search(r"\b(Args|Parameters|Returns|Raises):\s*\n", docstring) and not suppressed(line, 40):
            violations.append((path, node.lineno, 40))
    if getattr(node, "col_offset", 0) > 0:
        for sub in ast.walk(node):
            if isinstance(sub, (ast.Import, ast.ImportFrom)):
                subline = lines[sub.lineno - 1] if sub.lineno - 1 < len(lines) else ""
                if not suppressed(subline, 13):
                    violations.append((path, sub.lineno, 13))

def _check_ast_return(node: ast.Return, path: Path, line: str, lines: list[str], violations: list[tuple[Path, int, int]]) -> None:
    if isinstance(node.value, ast.BinOp):
        bin_ops = [sub for sub in ast.walk(node.value) if isinstance(sub, ast.BinOp)]
        is_path_join = any(
            isinstance(op.op, ast.Div) and isinstance(op.right, ast.Constant) and isinstance(op.right.value, str)
            for op in bin_ops
        )
        if not is_path_join and len(bin_ops) >= 4 and not suppressed(line, 39):
            violations.append((path, node.lineno, 39))

def _check_ast_comprehension(node: ast.AST, path: Path, line: str, lines: list[str], violations: list[tuple[Path, int, int]]) -> None:
    has_walrus = any(isinstance(sub, ast.NamedExpr) for sub in ast.walk(node))
    has_multi_if = any(len(gen.ifs) > 1 for gen in getattr(node, "generators", []))
    if (has_walrus or has_multi_if) and not suppressed(line, 42):
        violations.append((path, node.lineno, 42))

def _check_ast_assign(node: ast.Assign, path: Path, line: str, lines: list[str], violations: list[tuple[Path, int, int]]) -> None:
    if getattr(node, "end_lineno", node.lineno) > node.lineno:
        has_math = any(isinstance(sub, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)) for sub in ast.walk(node.value))
        if has_math:
            raw_chunk = " ".join(lines[node.lineno - 1 : node.end_lineno])
            compact_chunk = " ".join(raw_chunk.split())
            if len(compact_chunk) <= 140 and not suppressed(line, 44):
                violations.append((path, node.lineno, 44))

def _check_ast_class_def(node: ast.ClassDef, path: Path, line: str, tree: ast.AST, lines: list[str], violations: list[tuple[Path, int, int]]) -> None:
    has_abc = any(_base_name(base_node) in ("ABC", "ABCMeta") for base_node in node.bases)
    has_abc = has_abc or any(kw.arg == "metaclass" and _base_name(kw.value) in ("ABC", "ABCMeta") for kw in node.keywords)
    if has_abc:
        has_calc = any(
            isinstance(sub, ast.FunctionDef)
            and (sub.name.startswith("calc_") or any(kw in sub.name.lower() for kw in CALC_NAME_KEYWORDS))
            for sub in ast.iter_child_nodes(tree)
        )
        if has_calc and not suppressed(line, 45):
            violations.append((path, node.lineno, 45))

def _check_ast_compare(node: ast.Compare, path: Path, line: str, lines: list[str], violations: list[tuple[Path, int, int]]) -> None:
    for op, comparator in zip(node.ops, node.comparators):
        if isinstance(op, (ast.Eq, ast.NotEq)) and isinstance(comparator, ast.Constant) and comparator.value is None:
            if not suppressed(line, 15):
                violations.append((path, node.lineno, 15))

def _check_ast_name(
    node: ast.Name,
    path: Path,
    line: str,
    lines: list[str],
    violations: list[tuple[Path, int, int]],
    custom_cfg: CustomLinterConfig | None = None,
) -> None:
    if isinstance(node.ctx, ast.Store):
        var_name = node.id
        allowed_extra = custom_cfg.allowed_vars if custom_cfg else set()
        banned_extra = custom_cfg.banned_vars if custom_cfg else set()
        if var_name.lower() in banned_extra:
            if not suppressed(line, 38):
                violations.append((path, node.lineno, 38))
        elif (
            not (var_name.startswith("__") and var_name.endswith("__"))
            and var_name not in ALLOWED_SHORT_VARS
            and var_name not in allowed_extra
        ):
            if len(var_name) == 1 or var_name.lower() in VAGUE_VAR_NAMES:
                if not suppressed(line, 38):
                    violations.append((path, node.lineno, 38))

def _check_ast_call(node: ast.Call, path: Path, line: str, lines: list[str], violations: list[tuple[Path, int, int]]) -> None:
    if isinstance(node.func, ast.Attribute) and node.func.attr == "format":
        if not suppressed(line, 16):
            violations.append((path, node.lineno, 16))
    if isinstance(node.func, ast.Attribute) and node.func.attr == "setToolTip":
        if node.args and _is_string_literal(node.args[0]) and not suppressed(line, 23):
            violations.append((path, node.lineno, 23))
    if isinstance(node.func, ast.Name) and node.func.id == "print" and not suppressed(line, 25):
        violations.append((path, node.lineno, 25))
    if (isinstance(node.func, ast.Attribute) and node.func.attr == "setDecimals"
            and path.name not in SPINBOX_EXEMPT_FILES and not suppressed(line, 34)):
        if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, int):
            if node.args[0].value < SPINBOX_MAX_DECIMALS:
                violations.append((path, node.lineno, 34))
    is_test_file = "tests" in path.parts or path.name.startswith("test_")
    if not is_test_file:
        if isinstance(node.func, ast.Name) and node.func.id in ("eval", "exec") and not suppressed(line, 92):
            violations.append((path, node.lineno, 92))
        elif isinstance(node.func, ast.Attribute) and node.func.attr == "system" and getattr(node.func.value, "id", None) == "os":
            if not suppressed(line, 92):
                violations.append((path, node.lineno, 92))
        elif isinstance(node.func, ast.Attribute) and getattr(node.func.value, "id", None) == "subprocess":
            for kw in node.keywords:
                if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    if node.args and not isinstance(node.args[0], ast.Constant):
                        if not suppressed(line, 92):
                            violations.append((path, node.lineno, 92))
        if isinstance(node.func, ast.Attribute) and node.func.attr == "load" and getattr(node.func.value, "id", None) == "yaml":
            has_safe = any(
                kw.arg == "Loader" and (
                    (isinstance(kw.value, ast.Attribute) and kw.value.attr in ("SafeLoader", "CSafeLoader"))
                    or (isinstance(kw.value, ast.Name) and kw.value.id in ("SafeLoader", "CSafeLoader"))
                ) for kw in node.keywords
            )
            if not has_safe and not suppressed(line, 93):
                violations.append((path, node.lineno, 93))
        elif isinstance(node.func, ast.Attribute) and node.func.attr in ("loads", "load") and getattr(node.func.value, "id", None) in ("pickle", "_pickle", "marshal"):
            if not suppressed(line, 93):
                violations.append((path, node.lineno, 93))
        if isinstance(node.func, ast.Attribute) and node.func.attr in ("execute", "executemany"):
            if node.args:
                first = node.args[0]
                is_sql_target = (
                    "sql" in path.name.lower() or "db" in path.name.lower()
                    or getattr(node.func.value, "id", None) in ("cursor", "cur", "db", "conn", "session")
                )
                if is_sql_target and isinstance(first, (ast.JoinedStr, ast.BinOp)):
                    if not suppressed(line, 94):
                        violations.append((path, node.lineno, 94))

def _check_ast_assert(node: ast.Assert, path: Path, line: str, violations: list[tuple[Path, int, int]]) -> None:
    if isinstance(node.test, ast.Constant) and node.test.value is True:
        if not suppressed(line, 96):
            violations.append((path, node.lineno, 96))
    elif isinstance(node.test, ast.Compare):
        if (isinstance(node.test.left, ast.Constant) and len(node.test.comparators) == 1
                and isinstance(node.test.comparators[0], ast.Constant)):
            if node.test.left.value == node.test.comparators[0].value and not suppressed(line, 96):
                violations.append((path, node.lineno, 96))

def _check_ast_constant(node: ast.Constant, path: Path, line: str, lines: list[str], violations: list[tuple[Path, int, int]]) -> None:
    if isinstance(node.value, str):
        if HARDCODED_PATH_RE.match(node.value) and not suppressed(line, 26):
            violations.append((path, node.lineno, 26))
        if HEX_COLOR_RE.match(node.value) and "theme" not in path.name.lower() and not suppressed(line, 28):
            violations.append((path, node.lineno, 28))

def _check_ast_binop(node: ast.BinOp, path: Path, line: str, lines: list[str], violations: list[tuple[Path, int, int]]) -> None:
    if isinstance(node.op, ast.Mod) and isinstance(node.left, ast.Constant):
        if isinstance(node.left.value, str) and not suppressed(line, 16):
            violations.append((path, node.lineno, 16))

def _check_ast_try(node: ast.Try, path: Path, line: str, lines: list[str], violations: list[tuple[Path, int, int]]) -> None:
    for body_node in node.body:
        if isinstance(body_node, (ast.Import, ast.ImportFrom)):
            subline = lines[body_node.lineno - 1] if body_node.lineno - 1 < len(lines) else ""
            if not suppressed(subline, 22):
                violations.append((path, body_node.lineno, 22))
    for handler in node.handlers:
        for body_node in handler.body:
            if isinstance(body_node, (ast.Import, ast.ImportFrom)):
                subline = lines[body_node.lineno - 1] if body_node.lineno - 1 < len(lines) else ""
                if not suppressed(subline, 22):
                    violations.append((path, body_node.lineno, 22))

def _check_ast_dict(node: ast.Dict, path: Path, line: str, lines: list[str], violations: list[tuple[Path, int, int]]) -> None:
    seen_keys = set()
    for key in node.keys:
        if isinstance(key, ast.Constant) and isinstance(key.value, (str, int)):
            if key.value in seen_keys:
                key_line = lines[key.lineno - 1] if key.lineno - 1 < len(lines) else line
                if not suppressed(key_line, 43):
                    violations.append((path, key.lineno, 43))
            seen_keys.add(key.value)

# Section 5: Python AST checks
def scan_python_ast(
    path: Path,
    source: str,
    lines: list[str],
    violations: list[tuple[Path, int, int]],
    custom_cfg: CustomLinterConfig | None = None,
) -> None:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return

    seen_non_import_top_level = False

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if seen_non_import_top_level:
                line = lines[node.lineno - 1] if node.lineno - 1 < len(lines) else ""
                if not suppressed(line, 12):
                    violations.append((path, node.lineno, 12))
        elif isinstance(node, (ast.Expr, ast.Assign)) and _is_docstring_or_dunder(node):
            continue
        else:
            seen_non_import_top_level = True

    for node in ast.walk(tree):
        line = lines[node.lineno - 1] if getattr(node, "lineno", 0) and node.lineno - 1 < len(lines) else ""

        if isinstance(node, ast.ImportFrom):
            _check_ast_import_from(node, path, line, lines, violations)
        elif isinstance(node, ast.ExceptHandler):
            _check_ast_except_handler(node, path, line, lines, violations)
        elif isinstance(node, ast.FunctionDef):
            _check_ast_function_def(node, path, line, lines, violations)
        elif isinstance(node, ast.Return):
            _check_ast_return(node, path, line, lines, violations)
        elif isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            _check_ast_comprehension(node, path, line, lines, violations)
        elif isinstance(node, ast.Assign):
            _check_ast_assign(node, path, line, lines, violations)
        elif isinstance(node, ast.ClassDef):
            _check_ast_class_def(node, path, line, tree, lines, violations)
        elif isinstance(node, ast.Compare):
            _check_ast_compare(node, path, line, lines, violations)
        elif isinstance(node, ast.Name):
            _check_ast_name(node, path, line, lines, violations, custom_cfg=custom_cfg)
        elif isinstance(node, ast.arg) and custom_cfg is not None and custom_cfg.banned_vars:
            if node.arg.lower() in custom_cfg.banned_vars and not suppressed(line, 38):
                violations.append((path, node.lineno, 38))
        elif isinstance(node, ast.Call):
            _check_ast_call(node, path, line, lines, violations)
        elif isinstance(node, ast.Constant):
            _check_ast_constant(node, path, line, lines, violations)
        elif isinstance(node, ast.BinOp):
            _check_ast_binop(node, path, line, lines, violations)
        elif isinstance(node, ast.Try):
            _check_ast_try(node, path, line, lines, violations)
        elif isinstance(node, ast.Dict):
            _check_ast_dict(node, path, line, lines, violations)
        elif isinstance(node, ast.Assert):
            _check_ast_assert(node, path, line, violations)

def _base_name(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _call_target_name(func_attr: ast.Attribute) -> str | None:
    value = func_attr.value
    if isinstance(value, ast.Attribute):
        return value.attr
    if isinstance(value, ast.Name):
        return value.id
    return None


def scan_dialog_label_selectability(path: Path, source: str, lines: list[str], violations: list[tuple[Path, int, int]]) -> None:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if not any(_base_name(base) in DIALOG_BASE_NAMES for base in node.bases):
            continue
        wordwrap_targets = {}
        selectable_targets = set()
        for sub in ast.walk(node):
            if not (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute)):
                continue
            target = _call_target_name(sub.func)
            if target is None:
                continue
            if sub.func.attr == "setWordWrap" and sub.args and isinstance(sub.args[0], ast.Constant) and sub.args[0].value is True:
                wordwrap_targets.setdefault(target, sub.lineno)
            elif sub.func.attr == "setTextInteractionFlags":
                selectable_targets.add(target)
        for target, lineno in wordwrap_targets.items():
            if target in selectable_targets:
                continue
            line = lines[lineno - 1] if lineno - 1 < len(lines) else ""
            if not suppressed(line, 33):
                violations.append((path, lineno, 33))


def _assign_target_name(target: ast.AST) -> str | None:
    if isinstance(target, ast.Name):
        return target.id
    if isinstance(target, ast.Attribute):
        return target.attr
    return None


def scan_missing_tooltips(path: Path, source: str, lines: list[str], violations: list[tuple[Path, int, int]]) -> None:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        widget_targets = {}
        tooltipped_targets = set()
        for sub in ast.walk(node):
            if isinstance(sub, ast.Assign) and isinstance(sub.value, ast.Call):
                func = sub.value.func
                class_name = func.id if isinstance(func, ast.Name) else (func.attr if isinstance(func, ast.Attribute) else None)
                if class_name in TOOLTIP_TARGET_CLASSES:
                    for t in sub.targets:
                        name = _assign_target_name(t)
                        if name:
                            widget_targets.setdefault(name, sub.value.lineno)
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr == "setToolTip":
                target_name = _call_target_name(sub.func)
                if target_name:
                    tooltipped_targets.add(target_name)
        for name, lineno in widget_targets.items():
            if name in tooltipped_targets:
                continue
            line = lines[lineno - 1] if lineno - 1 < len(lines) else ""
            if not suppressed(line, 35):
                violations.append((path, lineno, 35))


def _function_is_platform_scoped(func: ast.FunctionDef) -> bool:
    if any(keyword in func.name.lower() for keyword in PLATFORM_NAME_KEYWORDS):
        return True
    return any(isinstance(sub, ast.Attribute) and sub.attr == "platform" for sub in ast.walk(func))


def scan_os_specific_code(path: Path, source: str, lines: list[str], violations: list[tuple[Path, int, int]]) -> None:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child.parent = node

    innermost = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            start, end = node.lineno, getattr(node, "end_lineno", node.lineno)
            size = end - start
            for lineno in range(start, min(end, len(lines)) + 1):
                current = innermost.get(lineno)
                if current is None or size < current[0]:
                    innermost[lineno] = (size, node)

    exempt_cache = {}
    for lineno, line in enumerate(lines, 1):
        if not OS_SPECIFIC_RE.search(line) or suppressed(line, 32):
            continue
        exempt = False
        cursor = innermost.get(lineno, (0, None))[1]
        while cursor is not None:
            if isinstance(cursor, ast.FunctionDef):
                if id(cursor) not in exempt_cache:
                    exempt_cache[id(cursor)] = _function_is_platform_scoped(cursor)
                if exempt_cache[id(cursor)]:
                    exempt = True
                    break
            cursor = getattr(cursor, "parent", None)
        if not exempt:
            violations.append((path, lineno, 32))


def _is_string_literal(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return True
    return isinstance(node, ast.JoinedStr)


def _is_docstring_or_dunder(node: ast.AST) -> bool:
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
        return True
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id.startswith("__") and t.id.endswith("__"):
                return True
    return False


def scan_silent_fallback_passthrough(path: Path, lines: list[str], violations: list[tuple[Path, int, int]]) -> None:
    path_lower = str(path).lower()
    if not any(k in path_lower for k in ("domain", "service", "scaling", "transform", "convert")):
        return
    for idx, line in enumerate(lines, 1):
        clean = line.split("//")[0].split("#")[0].strip()
        if re.search(r"return\s*\{\s*formattedText:\s*\w+\.raw\s*\}|return\s+\w+\.raw\b", clean):
            prev_context = "\n".join(lines[max(0, idx - 12):idx])
            if re.search(r"!\w+\.quantity|!\w+\.unit", prev_context):
                if "parse" not in prev_context:
                    violations.append((path, idx, 82))


# Per-file scanner worker (used by both sequential and parallel runs)
def scan_single_file(path_str: str) -> tuple[str, list[tuple[str, int, int]], dict[str, tuple[str, int, str]]]:
    path = Path(path_str)
    violations = []
    funcs = {}

    try:
        source = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return path_str, violations, funcs

    lines = source.splitlines()
    custom_cfg = load_custom_linter_config(file_path=path)

    for i, line in enumerate(lines, 1):
        scan_text_line(path, i, line, violations)

    scan_silent_fallback_passthrough(path, lines, violations)
    violations.extend(scan_custom_rules_for_file(path, source, lines, custom_cfg, suppressed))

    if path.suffix == ".py":
        scan_comment_blocks(path, lines, violations)
        scan_python_ast(path, source, lines, violations, custom_cfg=custom_cfg)
        scan_os_specific_code(path, source, lines, violations)
        scan_dialog_label_selectability(path, source, lines, violations)
        scan_missing_tooltips(path, source, lines, violations)
        funcs = extract_function_bodies(source)
    elif path.suffix in (".md", ".txt", ".rst"):
        scan_markdown_headings(path, lines, violations)
    elif path.suffix in (".js", ".jsx", ".ts", ".tsx", ".rs", ".go", ".c", ".cpp", ".h", ".sh", ".kt", ".dart", ".swift", ".cs"):
        scan_comment_blocks(path, lines, violations)

    seen_sites: set[tuple[str, int, int]] = set()
    site_methods = (
        "tooltip_literal_sites",
        "layout_hazards",
        "raw_unicode_escape_sites",
        "unguarded_mutation_sites",
        "unbounded_collection_sites",
        "unreset_control_sites",
        "micro_typography_sites",
        "svg_chart_sites",
        "ambiguous_unit_sites",
    )
    for ad in get_all_adapters():
        if path.suffix in ad.extensions:
            for method_name in site_methods:
                fn = getattr(ad, method_name, None)
                if fn is None:
                    continue
                for site in fn(path, source):
                    key = (str(site.file), site.line, site.code)
                    if key in seen_sites:
                        continue
                    seen_sites.add(key)
                    line_text = lines[site.line - 1] if site.line - 1 < len(lines) else ""
                    if not suppressed(line_text, site.code):
                        violations.append((site.file, site.line, site.code))

    serializable_violations = [(str(v[0]), v[1], v[2]) for v in violations]
    return path_str, serializable_violations, funcs


def scan_file(path: Path, violations: list[tuple[Path, int, int]]) -> None:
    _, file_violations, _ = scan_single_file(str(path))
    for v in file_violations:
        violations.append((Path(v[0]), v[1], v[2]))


# Caching layer (.lint_cache.json)
def get_linter_hash() -> str:
    hasher = hashlib.md5()
    linter_file = Path(__file__).resolve()
    adapter_dir = linter_file.parent / "ui_adapters"
    source_files = [linter_file, linter_file.parent / "custom_linter.py", linter_file.parent / "repo_standards_rules.py"]
    if adapter_dir.is_dir():
        source_files.extend(sorted(adapter_dir.glob("*.py")))
    source_files.extend(load_custom_linter_config().loaded_files)
    for source_file in source_files:
        try:
            hasher.update(source_file.read_bytes())
        except OSError:
            continue
    return hasher.hexdigest()


def load_cache() -> dict:
    if CACHE_PATH.exists():
        try:
            data = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(data, dict) or data.get("_linter_hash") != get_linter_hash():
            return {}
        return data
    return {}


def save_cache(cache: dict) -> None:
    try:
        cache["_linter_hash"] = get_linter_hash()
        CACHE_PATH.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    except OSError:
        return


def get_file_hash(path: Path) -> str:
    try:
        return hashlib.md5(path.read_bytes()).hexdigest()
    except Exception:
        return ""


def is_scannable_file(fpath: Path) -> bool:
    if fpath.name.startswith("lint_report") and fpath.suffix == ".txt":
        return False
    if fpath.name in ("INSTRUCTIONS_TEMPLATE.md", "ENGINEERING_RULES.md", CUSTOM_CONFIG_FILENAME, CUSTOM_EXAMPLE_FILENAME):
        return False
    if not (fpath.suffix in SUPPORTED_EXTENSIONS and EXCLUDED_DIRS.isdisjoint(fpath.parts)):
        return False
    return not is_ignored_by_custom_config(fpath, load_custom_linter_config(file_path=fpath))


# File collection and Git Diff Scoping
def collect_git_diff_files(target: str, staged_only: bool = False) -> list[Path]:
    try:
        p = Path(target).resolve()
        cwd = str(p if p.is_dir() else p.parent)

        cmd = ["git", "diff", "--name-only", "--cached"] if staged_only else ["git", "diff", "--name-only", "HEAD"]
        res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
        changed_paths = {line.strip().strip('"') for line in res.stdout.splitlines() if line.strip()}

        if not staged_only:
            # Expand untracked directories so new source trees are not skipped
            status_res = subprocess.run(["git", "status", "--porcelain", "-uall"], cwd=cwd, capture_output=True, text=True, check=False)
            for raw_line in status_res.stdout.splitlines():
                if len(raw_line) > 3:
                    path_part = raw_line[3:].strip()
                    if " -> " in path_part:
                        path_part = path_part.split(" -> ", 1)[1].strip()
                    path_part = path_part.strip('"')
                    if path_part:
                        changed_paths.add(path_part)

        git_root_res = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=cwd, capture_output=True, text=True, check=False)
        git_root = Path(git_root_res.stdout.strip()) if git_root_res.returncode == 0 else p

        files: list[Path] = []
        seen_paths: set[Path] = set()
        for rel in changed_paths:
            fpath = git_root / rel
            if fpath.is_file() and is_scannable_file(fpath) and fpath not in seen_paths:
                files.append(fpath)
                seen_paths.add(fpath)
            elif fpath.is_dir():
                for child in collect_files(str(fpath)):
                    if child not in seen_paths:
                        files.append(child)
                        seen_paths.add(child)
        return files
    except Exception:
        return []


def detect_repo_hygiene_issues(root: Path, violations: list[tuple[Path, int, int]]) -> None:
    wf_dir = root / ".github" / "workflows"
    if wf_dir.is_dir():
        for wf_file in wf_dir.glob("*.yml"):
            try:
                content = wf_file.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if "release" in wf_file.name.lower() or "softprops/action-gh-release" in content or "gh release" in content:
                has_tags = "tags:" in content
                has_branch_or_pr = ("branches:" in content) or ("pull_request:" in content)
                if has_tags and not has_branch_or_pr and not _check_noqa_in_file(wf_file, 1, 89):
                    violations.append((wf_file, 1, 89))
                latest_match = re.search(r"tag_name:.*['\"]latest['\"]", content)
                if latest_match:
                    lineno = content[:latest_match.start()].count("\n") + 1
                    if not _check_noqa_in_file(wf_file, lineno, 89):
                        violations.append((wf_file, lineno, 89))
    if (root / "src-tauri" / "Cargo.toml").is_file():
        exempt_py = {"setup.py", "conftest.py", "manage.py"}
        for py_file in root.glob("*.py"):
            if py_file.name not in exempt_py and not _check_noqa_in_file(py_file, 1, 89):
                violations.append((py_file, 1, 89))
    for android_file, lineno, _ in detect_android_release_issues(root):
        if not _check_noqa_in_file(android_file, lineno, 89):
            violations.append((android_file, lineno, 89))


def collect_files(target: str) -> list[Path]:
    p = Path(target)
    if p.is_file():
        return [p] if is_scannable_file(p) else []
    return [
        f for f in p.rglob("*")
        if is_scannable_file(f)
    ]


# Suppression Audit
def audit_suppressions(target: str) -> str:
    files = collect_files(target)
    findings = defaultdict(list)
    suppression_markers = [
        ("noqa", NOQA_RE),
        ("type: ignore", re.compile(r"#\s*type:\s*ignore", re.IGNORECASE)),
        ("pragma: no cover", re.compile(r"#\s*pragma:\s*no\s*cover", re.IGNORECASE)),
        ("pylint: disable", re.compile(r"#\s*pylint:\s*disable", re.IGNORECASE)),
        ("nosec", re.compile(r"#\s*nosec\b", re.IGNORECASE)),
        ("TODO/FIXME/HACK/XXX", TODO_RE),  # noqa: 91
    ]

    for f in files:
        try:
            lines = f.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue
        for i, line in enumerate(lines, 1):
            for label, pattern in suppression_markers:
                if pattern.search(line):
                    findings[label].append((f, i, line.strip()))

    out_lines = ["SUPPRESSION AUDIT"]
    total = 0
    for label, _ in suppression_markers:
        entries = findings.get(label, [])
        if not entries:
            continue
        total += len(entries)
        out_lines.append("")
        out_lines.append(f"{label} ({len(entries)})")
        for fpath, lineno, text in entries:
            out_lines.append(f"  {fpath}:{lineno} | {text}")
    if total == 0:
        out_lines.append("")
        out_lines.append("None found.")
    return "\n".join(out_lines)


def run_standard_linter(target_dir: Path) -> list[tuple[Path, int, int]]:
    cmd: list[str] = []
    if shutil.which("uv"):
        cmd = ["uv", "tool", "run", "ruff", "check", "--select", "E9,F821,F822,F823,E722", "--no-fix", str(target_dir)]
    else:
        executable = shutil.which("ruff") or shutil.which("ruff.exe")
        if executable:
            cmd = [executable, "check", "--select", "E9,F821,F822,F823,E722", "--no-fix", str(target_dir)]

    if not cmd:
        return []

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        ruff_violations: list[tuple[Path, int, int]] = []
        for line in res.stdout.splitlines():
            m = re.match(r"^(.*?):(\d+):\d+:\s*(.+)$", line.strip())
            if m:
                filepath = Path(m.group(1)).resolve()
                lineno = int(m.group(2))
                ruff_violations.append((filepath, lineno, 40))
        return ruff_violations
    except Exception:
        return []


def is_git_repository(cwd: Path) -> bool:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
        )
        return res.returncode == 0
    except Exception:
        return False


def calc_report_path(root: Path, custom_path: Path | None = None) -> Path:
    if custom_path is not None:
        return custom_path
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", root.name) or "project"
    return Path(__file__).parent / f"lint_report_{safe_name}.txt"


def print_linter_usage() -> None:
    print("Usage: ailint [target] [options...]\n")
    print("79-rule AST, multi-framework UI, and code quality linter.\n")
    print("Options:")
    print("  --level LEVEL        Verification level: standard, strict (default), full")
    print("  --diff               Lint only modified and untracked git files (default in git repos)")
    print("  --staged             Lint only git staged files")
    print("  --full, --all        Lint all scannable files in target directory")
    print("  --skip CODES         Comma-separated rule codes to skip (e.g. 38,40)")
    print("  --only CODES         Comma-separated rule codes to enforce only")
    print("  --noqa               Audit and print existing noqa suppressions")
    print("  --no-cache           Bypass incremental caching")
    print("  --no-parallel        Disable parallel worker pool")
    print("  --no-ruff            Disable external ruff linter integration")
    print("  --report PATH        Custom output path for lint report text file")
    print("  --ui-evidence PATH   Custom path to ui_evidence.json")
    print("  -h, --help           Show this help message and exit")


def parse_cli_args(raw_args: list[str]) -> tuple[str, str, set[int], set[int], dict]:
    if any(arg in ("-h", "--help", "help") for arg in raw_args):
        print_linter_usage()
        sys.exit(0)

    target = "."
    for item in raw_args:
        if not item.startswith("--"):
            target = item
            break

    cfg = load_tools_config(target)
    level = cfg.linter_level or "strict"
    skip_codes: set[int] = set(cfg.linter_skip)
    only_codes: set[int] = set(cfg.linter_only)
    evidence_override = Path(cfg.linter_ui_evidence) if cfg.linter_ui_evidence else None

    flags = {
        "noqa": False,
        "diff": False,
        "staged": False,
        "full": False,
        "no_cache": False,
        "no_parallel": False,
        "no_ruff": False,
        "report": None,
        "ui_evidence": evidence_override,
    }

    i = 0
    target_set = False
    while i < len(raw_args):
        arg = raw_args[i]
        if arg == "--level" and i + 1 < len(raw_args):
            level = raw_args[i + 1].lower()
            i += 2
        elif arg.startswith("--level="):
            level = arg.split("=", 1)[1].lower()
            i += 1
        elif arg == "--skip" and i + 1 < len(raw_args):
            skip_codes = {int(code_str.strip()) for code_str in raw_args[i + 1].split(",") if code_str.strip().isdigit()}
            i += 2
        elif arg.startswith("--skip="):
            skip_codes = {int(code_str.strip()) for code_str in arg.split("=", 1)[1].split(",") if code_str.strip().isdigit()}
            i += 1
        elif arg == "--only" and i + 1 < len(raw_args):
            only_codes = {int(code_str.strip()) for code_str in raw_args[i + 1].split(",") if code_str.strip().isdigit()}
            i += 2
        elif arg.startswith("--only="):
            only_codes = {int(code_str.strip()) for code_str in arg.split("=", 1)[1].split(",") if code_str.strip().isdigit()}
            i += 1
        elif arg == "--noqa":
            flags["noqa"] = True
            i += 1
        elif arg == "--diff":
            flags["diff"] = True
            i += 1
        elif arg == "--staged":
            flags["staged"] = True
            i += 1
        elif arg in ("--full", "--all"):
            flags["full"] = True
            i += 1
        elif arg == "--report" and i + 1 < len(raw_args):
            flags["report"] = Path(raw_args[i + 1])
            i += 2
        elif arg.startswith("--report="):
            flags["report"] = Path(arg.split("=", 1)[1])
            i += 1
        elif arg == "--no-cache":
            flags["no_cache"] = True
            i += 1
        elif arg == "--no-parallel":
            flags["no_parallel"] = True
            i += 1
        elif arg == "--no-ruff":
            flags["no_ruff"] = True
            i += 1
        elif arg == "--ui-evidence" and i + 1 < len(raw_args):
            flags["ui_evidence"] = Path(raw_args[i + 1])
            i += 2
        elif arg.startswith("--ui-evidence="):
            flags["ui_evidence"] = Path(arg.split("=", 1)[1])
            i += 1
        elif not arg.startswith("--"):
            if not target_set:
                target = arg
                target_set = True
            i += 1
        else:
            i += 1

    return target, level, skip_codes, only_codes, flags


# Driver and CLI
def main() -> int:
    raw_args = sys.argv[1:]
    target, level, skip_codes, only_codes, flags = parse_cli_args(raw_args)

    p = Path(target).resolve()
    root = p if p.is_dir() else p.parent
    report_file = calc_report_path(root, flags["report"])

    if flags["noqa"]:
        report = audit_suppressions(target)
        print(report)  # noqa: 25
        report_file.write_text(report, encoding="utf-8")
        return 0

    had_target_env = "AI_DEV_TOOLS_TARGET_ROOT" in os.environ
    prev_target_env = os.environ.get("AI_DEV_TOOLS_TARGET_ROOT")
    os.environ["AI_DEV_TOOLS_TARGET_ROOT"] = str(root)
    try:
        custom_cfg = load_custom_linter_config(target_root=root)

        active_codes = set(LEVEL_RULES.get(level, LEVEL_RULES["strict"]))
        if only_codes:
            active_codes = set(only_codes)
        if skip_codes:
            active_codes = active_codes - skip_codes

        if p.is_file():
            files = [p] if p.suffix in SUPPORTED_EXTENSIONS else []
        elif flags["full"]:
            files = collect_files(target)
        elif flags["diff"] or flags["staged"]:
            files = collect_git_diff_files(target, staged_only=flags["staged"])
            print(f"Git diff scoped: Scanning {len(files)} changed file(s).")  # noqa: 25
        else:
            # Default: git diff scoped if inside git repo; otherwise scan target
            if is_git_repository(root):
                files = collect_git_diff_files(target, staged_only=False)
                if files:
                    print(f"Git diff scoped: Scanning {len(files)} changed file(s).")  # noqa: 25
                else:
                    print("No uncommitted changes detected. Git diff clean (0 changed files). Pass --full for a whole-repo audit.")  # noqa: 25
            else:
                files = collect_files(target)

        if not files:
            if report_file.is_file():
                try:
                    report_file.unlink()
                except OSError:
                    return 0
            old_report = Path(__file__).parent / "lint_report.txt"
            if old_report.is_file():
                try:
                    old_report.unlink()
                except OSError:
                    return 0
            print("None. Lint clean.")  # noqa: 25
            return 0

        cache = {} if flags["no_cache"] else load_cache()
        files_to_scan = []
        violations = []
        all_files_funcs = {}

        for f in files:
            f_str = str(f)
            f_hash = get_file_hash(f)
            cached_entry = cache.get(f_str)
            if cached_entry and cached_entry.get("hash") == f_hash:
                for v in cached_entry.get("violations", []):
                    violations.append((Path(v[0]), v[1], v[2]))
                if f.suffix == ".py" and "funcs" in cached_entry:
                    all_files_funcs[f] = cached_entry["funcs"]
            else:
                files_to_scan.append((f, f_hash))

        if files_to_scan:
            paths_to_scan_str = [str(f[0]) for f in files_to_scan]

            safe_workers = min(os.cpu_count() or 1, 4)
            if len(paths_to_scan_str) > 15 and not flags["no_parallel"] and safe_workers > 1:
                with Pool(processes=safe_workers) as pool:
                    scan_results = pool.map(scan_single_file, paths_to_scan_str)
            else:
                scan_results = [scan_single_file(p_str) for p_str in paths_to_scan_str]

            hash_lookup = {str(f[0]): f[1] for f in files_to_scan}

            for path_str, file_violations, funcs in scan_results:
                fpath = Path(path_str)
                for v in file_violations:
                    violations.append((Path(v[0]), v[1], v[2]))
                if funcs:
                    all_files_funcs[fpath] = funcs

                cache[path_str] = {
                    "hash": hash_lookup.get(path_str, ""),
                    "violations": file_violations,
                    "funcs": funcs,
                }

            save_cache(cache)

        if 20 in active_codes:
            detect_duplicate_code(all_files_funcs, violations)
        if 21 in active_codes:
            detect_unused_code(files, violations)
        if p.is_dir() and not (flags["diff"] or flags["staged"]) and flags["full"] and any(rule_code in active_codes for rule_code in (29, 30)):
            detect_module_graph_issues(files, root, violations)
        if 40 in active_codes and not flags["no_ruff"]:
            ruff_violations = run_standard_linter(root)
            violations.extend(ruff_violations)

        ui_active_codes = {c for c in active_codes if c in range(46, 91)}
        if ui_active_codes:
            ui_cfg = load_ui_config(root)
            ui_manifest = build_manifest(root, ui_cfg, files=files)
            if ui_manifest.controls or ui_manifest.screens:
                ui_static = evaluate_static_rules(root, ui_manifest, ui_cfg, files=files)
                for sv in ui_static:
                    if sv[2] in active_codes:
                        violations.append(sv)
                ev_path = flags["ui_evidence"] if flags.get("ui_evidence") else (root / ui_cfg.evidence_path)
                ev_obj = load_ui_evidence(ev_path, ui_manifest)
                ui_ev = evaluate_evidence_rules(root, ui_manifest, ev_obj, ui_cfg)
                for ev in ui_ev:
                    if ev[2] in active_codes:
                        violations.append(ev)
            if 87 in active_codes or 88 in active_codes:
                for ad in get_all_adapters():
                    if 87 in active_codes and hasattr(ad, "stale_bundle_sites"):
                        for sv in getattr(ad, "stale_bundle_sites")(root):
                            if not _check_noqa_in_file(sv.file, sv.line, sv.code):
                                violations.append((sv.file, sv.line, sv.code))
                    if 88 in active_codes and hasattr(ad, "desktop_lifecycle_sites"):
                        for sv in getattr(ad, "desktop_lifecycle_sites")(root):
                            if not _check_noqa_in_file(sv.file, sv.line, sv.code):
                                violations.append((sv.file, sv.line, sv.code))
        if 89 in active_codes:
            detect_repo_hygiene_issues(root, violations)
        std_codes = active_codes & set(range(101, 113))
        should_check_standards = (
            p.is_dir()
            and (root / ".git").exists()
            and (
                flags["full"]
                or any(f.name in {"README.md", "LICENSE", "SECURITY.md", "ci.yml"} for f in files)
                or bool(only_codes & set(range(101, 113)))
            )
        )
        if std_codes and should_check_standards:
            detect_repo_standard_issues(root, files, std_codes, _check_noqa_in_file, violations)

        violations = filter_overridden_violations(violations, custom_cfg, root=root)
        violations = [v for v in violations if v[2] in active_codes]

        if not violations:
            if report_file.is_file():
                try:
                    report_file.unlink()
                except OSError:
                    return 0
            old_report = Path(__file__).parent / "lint_report.txt"
            if old_report.is_file():
                try:
                    old_report.unlink()
                except OSError:
                    return 0
            print("None. Lint clean.")  # noqa: 25
            return 0
        else:
            codes_present = sorted({v[2] for v in violations})
            out_lines = ["LEGEND"]
            for code in codes_present:
                out_lines.append(f"{code} = {LEGEND[code]}")
            out_lines.append("")
            out_lines.append("VIOLATIONS")
            for path, lineno, code in sorted(violations, key=lambda v: (str(v[0]), v[1])):
                out_lines.append(f"{path}:{lineno} | code={code}")

            report_file.write_text("\n".join(out_lines), encoding="utf-8")
            print(f"Report written to {report_file}")  # noqa: 25
            return 1
    finally:
        if not had_target_env:
            os.environ.pop("AI_DEV_TOOLS_TARGET_ROOT", None)
        elif prev_target_env is not None:
            os.environ["AI_DEV_TOOLS_TARGET_ROOT"] = prev_target_env


if __name__ == "__main__":
    sys.exit(main())
