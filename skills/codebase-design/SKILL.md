---
name: codebase-design
description: >-
  Evaluate module depth, interface simplicity, dependency categories, seams,
  and change locality using deep-module design vocabulary. Use when refactoring
  shallow wrappers, designing new module interfaces, reducing coupling, or
  comparing alternative designs.
---

# Codebase design

Apply John Ousterhout's deep-module philosophy: give modules small, simple interfaces that conceal substantial complexity behind clear seams.

Load [DEEPENING.md](DEEPENING.md) when planning how to collapse shallow wrappers or classify dependencies. Load [DESIGN-IT-TWICE.md](DESIGN-IT-TWICE.md) before committing to a major interface design.

## Core vocabulary

| Term | Definition |
| :--- | :--- |
| **Module** | Any self-contained unit (function, class, package, or service) presenting an interface to callers |
| **Interface** | Everything a caller must know to use the module (signatures, types, invariants, ordering, errors) |
| **Depth** | Ratio of functionality hidden inside the module to the cognitive size of its interface |
| **Shallow module** | A thin pass-through wrapper whose interface is nearly as complex as its implementation |
| **Seam** | The explicit boundary between caller and implementation where tests or adapters attach |
| **Adapter** | A concrete implementation behind a seam (production HTTP adapter vs in-memory test adapter) |
| **Leverage** | One interface improvement simplifying many call sites at once |
| **Locality** | Related assumptions change together in one place instead of scattering across files |
| **Deletion test** | Ask whether deleting a layer and inline-calling the underlying helper simplifies the caller; if yes, the layer is shallow |

## Combining with static metrics

Before redesigning a module in a Python codebase, measure coupling and complexity concretely:

```bash
aitools repo-map .
aitools imports .
aitools complexity .
```

Look for pass-through chains (`A -> B -> C` sharing almost identical parameters), high fan-in helper files, and tiny wrappers tested with heavy internal mocking.
