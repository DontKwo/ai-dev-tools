# Code Review Graph Specification

## Overview
Parses source repositories into an AST-aware code graph stored in a local SQLite database to compute change impact and blast radius.

## Graph Schema
- `symbols`: Functions, classes, interfaces, and variables with file locations and signature hashes.
- `calls`: Directed edges representing function calls and method invocations.
- `imports`: Dotted module dependencies and import edges between files.
- `tests`: Mappings between production symbols and test suite assertions.

## Blast Radius & Risk Scoring
- Calculates transitive callers affected by a modified file or function.
- Discovers precisely which unit tests need execution for a given git diff.
- Computes a change risk score based on caller fan-in and dependency depth.
