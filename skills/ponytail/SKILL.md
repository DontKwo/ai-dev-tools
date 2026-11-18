---
name: ponytail
description: Enforce the minimalist senior developer decision ladder to prevent AI code bloat, avoid over-engineering, and prune unnecessary dependencies.
---

# Ponytail Minimalist Engineering

Enforce the senior developer hierarchy: "The best code is the code you never wrote."

## Decision Ladder

Before writing any new code, stepping through this ladder is mandatory:

1. **YAGNI (You Aren't Gonna Need It)**:
   - Does this requirement serve an immediate, active need?
   - Reject speculative abstractions and unused features.

2. **Codebase Reuse**:
   - Inspect existing helper modules and utility functions.
   - Do not write a duplicate implementation when the codebase already provides the logic.

3. **Standard Library**:
   - Can standard library modules solve the problem cleanly?
   - Avoid pulling in external packages for basic math, string manipulation, or file IO.

4. **Platform Native**:
   - Favor native HTML/CSS/browser capabilities over heavy JavaScript libraries.
   - Use native language constructs before creating custom wrapper classes.

5. **Direct & Minimal Implementation**:
   - Favor straightforward functions over multi-layered class hierarchies.
   - Write only the code required to satisfy tests and requirements.
