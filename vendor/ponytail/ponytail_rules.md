# Ponytail: Minimalist Senior Developer Decision Ladder

## Philosophy
"The best code is the code you never wrote." Before writing code, AI agents must evaluate solutions against a strict minimalist hierarchy:

1. **YAGNI (You Aren't Gonna Need It)**: Does this requirement genuinely need to exist? Delete unnecessary features before writing code.
2. **Reuse**: Does an existing function, class, or module in the codebase already provide this behavior?
3. **Standard Library**: Can Python or standard platform libraries solve this directly without installing third-party packages?
4. **Platform Native**: Does the operating system or browser platform provide native capabilities (e.g. CSS flexbox/grid over complex layout JS, native HTML `<dialog>`)?
5. **One-Liner / Simple Expression**: Can the solution be expressed plainly without creating new classes, wrappers, or indirections?
6. **Minimal Code**: Write only the exact lines necessary to satisfy current requirements.
