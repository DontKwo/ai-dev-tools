# Context Mode Specification

## Overview
Cuts context window consumption through isolated local execution sandboxes and SQLite FTS5 documentation search.

## Core Mechanisms
1. **Sandboxed Command Execution (`ctx_execute`)**: Executes subcommands and heavy data queries in a local subprocess, returning distilled output summaries instead of raw dumps.
2. **SQLite FTS5 Local Search**: Indexes documentation and large files locally using SQLite Full-Text Search with BM25 ranking. Queries return precise snippets.
3. **Compaction Recovery**: Tracks session actions, commits, and edited files. Re-injects concise continuity summaries when `/compact` occurs.
