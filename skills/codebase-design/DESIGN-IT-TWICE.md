# Design it twice

Explore radically different interfaces in parallel before locking in a major API or deepening refactor: your first interface draft is rarely the deepest one. Assumes the vocabulary in [SKILL.md](SKILL.md) and [DEEPENING.md](DEEPENING.md).

## Process

### 1. Frame the problem space

Write a concise user-facing brief naming:

- Hard constraints and invariants the interface must guarantee.
- Dependencies behind the seam and their categories (see [DEEPENING.md](DEEPENING.md)).
- One rough caller sketch showing the problem concretely.

### 2. Spawn parallel design subagents

Launch three fresh-context subagents simultaneously with identical problem context plus one distinct architectural constraint per agent:

- **Agent 1**: Minimize interface surface (1 to 3 entry points maximum; maximize leverage per call).
- **Agent 2**: Maximize flexibility (extension hooks, composable options, streaming/batch symmetry).
- **Agent 3**: Optimize the default caller (zero boilerplate for 90 percent of usages; explicit escape hatches).

Include canonical terms from `GLOSSARY.md` if present. Require each subagent to output:

1. Exact interface signatures, error modes, and ordering invariants.
2. Concrete caller usage snippet.
3. Implementation complexity hidden behind the seam.
4. Adapter and test strategy.
5. Honest weaknesses and thin spots.

### 3. Compare and recommend

Present each option concisely, contrast them on **depth**, **locality**, and **seam placement**, and commit to one opinionated recommendation (or hybrid) with concrete rationale.
