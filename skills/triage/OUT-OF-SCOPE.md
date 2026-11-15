# Out-of-scope knowledge base rules

Store durable project boundaries in `.out-of-scope/<kebab-case-rule>.md` so repeated feature drift gets closed consistently in seconds.

## When to record a file

Create a short rule file in `.out-of-scope/` only when closing a recurring class of request rooted in a deliberate architectural principle (skip one-off bugs or duplicate typos).

## Format

```md
# Rule title (short, affirmative boundary)

State the architectural constraint cleanly in two to three sentences, naming what the project intentionally supports and what stays excluded.
```
