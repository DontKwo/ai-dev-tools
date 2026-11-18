---
name: rust-anything
description: Incrementally migrate Python, TypeScript, or C code to pure Rust with recorded behavior edge cases, front-door fallback proxies, and regression replay gates.
---

# Rust Anything Incremental Migration

Migrate software components piece-by-piece to pure Rust while guaranteeing zero breaking behavioral changes at every step.

## Migration Steps

1. **Behavior Recording**:
   - Run existing application workloads to capture inputs, outputs, and edge cases (Unicode, negative modulo, float extremes).
   - Exclude dynamic fields (timestamps, process IDs, randomized tokens).

2. **Front-Door Fallback Proxy**:
   - Place a Rust proxy in front of the application or module seam.
   - Route ported Rust functions to the new implementation.
   - Fall back to the original code for any path not yet migrated.

3. **Replay Validation Gates**:
   - Verify every ported Rust unit with Clippy and strict unit tests.
   - Replay all recorded behavior cases to prove zero regression.

4. **Hot-Loop Profiling**:
   - Profile runtime workloads to find computational bottlenecks.
   - Port performance-critical loops first to achieve 15x to 20x speedups before rewriting non-critical glue code.

5. **The Lift**:
   - Once 100% of paths are ported and verified, completely remove the fallback bindings and original code.
