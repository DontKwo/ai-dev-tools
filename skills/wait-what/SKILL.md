---
name: wait-what
disable-model-invocation: true
description: Re-pitch a dense technical explanation in ASD-STE100 Simplified Technical English using project Glossary terms.
---

# Plain-English re-explanation

Re-write the prior technical explanation so every step makes immediate sense without losing factual accuracy.

## Rules (ASD-STE100 style)

- Keep sentences under 20 words and convey one concrete idea per sentence.
- Use active voice (`A calls B`, avoiding passive constructions like `B is invoked by A`).
- Use exact terms from `GLOSSARY.md` when present, omitting synonyms listed under `_Avoid:_`.
- Replace stacked noun phrases or unexplained acronyms with concrete examples showing inputs, state changes, and outputs.
- Keep it concise: start directly with a two-sentence overview, then three to five numbered steps showing what actually happens at runtime.
