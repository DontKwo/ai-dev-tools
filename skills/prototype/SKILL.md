---
name: prototype
description: >-
  Build fast throwaway single-file HTML logic simulators or multi-variant UI
  explorations to validate ideas before writing production code. Use when the
  user wants to explore UI layouts, test state transitions visually, or spike
  an interaction flow.
---

# Prototype fast and throw away

Validate ambiguous UI layouts or stateful logic visually in minutes before investing in production wiring.

## Two prototype modes

### Mode 1: Single-file domain logic simulator

Generate one self-contained HTML file (vanilla JS or inline module script, zero build step) in the OS temporary directory simulating edge cases, pricing/math schedules, state machines, or workflow pipelines with interactive sliders, presets, and live readouts.

### Mode 2: Multi-variant UI exploration

Render two or three sharply distinct layout or interaction concepts behind lightweight client-side toggles (keyboard shortcuts `1`, `2`, `3` switching variants cleanly with sample realistic data, responsive from 360px to desktop, and theme-token colors).

## Archiving and clean handoff

- Treat prototypes strictly as learning artifacts; inspect what worked cleanly, run `/to-spec` to freeze settled requirements, then delete throwaway prototype clutter from the main branch (or commit to an archival `prototype/<name>` branch if requested).
- Keep prototype exploration out of production `main` source directories so `aitools prune` and `aitools lint` stay green.
