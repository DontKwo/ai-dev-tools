# High-signal behavior tests

Design tests around observable contracts so suites catch real regressions without breaking during valid internal refactoring.

## What makes a strong test

- **Behavioral focus**: Asserts return values, persisted state changes, raised exceptions, or emitted user-visible messages for realistic inputs.
- **Parametric / table-driven coverage**: Tests multiple valid, boundary, empty, and malformed inputs through one structured test matrix.
- **Independent setup**: Builds fresh temp directories, databases, or state fixtures per test case with zero execution-order coupling.
- **Clear failure diagnostics**: Failure output identifies the exact case input, expected outcome, and observed outcome.

## Anti-patterns to avoid

| Anti-pattern | Symptom | Fix |
| :--- | :--- | :--- |
| Implementation lock | Asserts private method call order or internal field layouts | Assert output or state observed at the public interface seam |
| Tautological assertion | Mirrors production formula line-for-line in the test | Assert independently known domain invariants and concrete fixtures |
| Weakened assertion | Loosens checks (`is not None`, partial match) after failure | Fix the code bug or align test strictly with the spec |
| Horizontal slicing | Writes 20 failing tests before writing any production code | Alternate one red test and one minimal green step per behavior slice |
| UI test bypass | Calls internal signal handlers directly under test | Drive real rendered widgets or CLI commands (`aiui` rules 46 to 49) |
