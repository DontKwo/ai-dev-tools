---
name: improve-codebase-architecture
disable-model-invocation: true
description: Audit coupling hotspots, generate a self-contained HTML architecture report, and propose deep-module refactor candidates.
---

# Improve codebase architecture

Surface architectural friction across the codebase and pinpoint shallow modules worth collapsing behind deep seams.

Assumes the vocabulary in [codebase-design](../codebase-design/SKILL.md) and [DEEPENING.md](../codebase-design/DEEPENING.md).

## Step 1: Collect structural signals

Run static architecture tools and git churn history together:

```bash
aitools complexity .
aitools imports .
aitools repo-map .
git log -n 100 --name-only --pretty=format:
```

Scan results for four high-leverage symptoms:

- **Pass-through clusters**: Two to five small modules passing identical parameters down a chain without adding domain behavior.
- **High-churn seams**: Files appearing together frequently in git commits that could hide behind one coherent module interface.
- **God orchestrators**: Functions or classes with high cyclomatic complexity mixing I/O, policy, and formatting.
- **Mock-heavy test files**: Suites stubbing multiple internal collaborators because no clean seam sits at the boundary.

## Step 2: Generate a visual HTML report

Write a self-contained single-file HTML report to the OS temporary directory (for example `tempfile.gettempdir()`) with inline styles (or Tailwind CDN) and inline Mermaid diagrams comparing **Before** (scattered shallow modules) and **After** (proposed deep module + seam + test boundary) for the top two to four candidates.

Open or print the path to the generated HTML file for the user.

## Step 3: Grill before refactoring

Hand control to [grill-user](../grill-user/SKILL.md) to settle which candidate to tackle first, which dependency category applies (In-process, Local-substitutable, Remote adapter, or External mock), and whether to sketch competing interfaces via [DESIGN-IT-TWICE.md](../codebase-design/DESIGN-IT-TWICE.md).
