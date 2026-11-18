# RTK (Rust Token Killer) Compression Specification

## Overview
RTK intercepts terminal commands executed by coding agents and strips non-essential output, cutting token consumption by 60% to 90%.

## Output Reduction Strategies
- `git status`: Collapses clean files, groups untracked directories, displays branch status and changed files only.
- `pytest` / `unittest`: Strips passing test logs and noisy progress bars; preserves test summary line and failure tracebacks.
- `cargo test`: Preserves failing asserts and compiler errors; condenses passing unit benchmarks.
- `npm test` / `vitest`: Collapses ANSI color escape codes and repeated headers; isolates failure assertions.
- Compiler warnings: Groups duplicate warnings across files and prints deduplicated counts.

## Implementation in ai-dev-tools
- Pure Python native compressor: `scripts/token_compressor.py`.
- CLI integration: `aitools compress <command>` or automated output filtering inside `scripts/cli.py`.
