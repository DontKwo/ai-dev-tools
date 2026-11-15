# Skill invocation model

Every skill in `skills/` uses one of two invocation modes defined in both `SKILL.md` frontmatter and `agents/openai.yaml`.

## User-invoked workflow skills

User-invoked skills run only when a human types their name (for example `/implement` or `/to-spec`):

- `SKILL.md` sets `disable-model-invocation: true`.
- `agents/openai.yaml` sets `policy.allow_implicit_invocation: false`.
- `description` stays a concise one-line summary for slash-command menus without autonomous trigger lists.
- Keeps permanent baseline prompt overhead low when idle.

## Model-invoked autonomous skills

Model-invoked skills remain reachable by both the model and the user:

- Omit `disable-model-invocation` from `SKILL.md` and omit `policy` from `agents/openai.yaml`.
- Write a model-facing `description` stating what the skill does and the exact situations when an agent should load it.
- Reserve model-invoked skills for capabilities the agent can reach for on its own during diagnosis, testing, linting, domain modeling, design, research, or review.
