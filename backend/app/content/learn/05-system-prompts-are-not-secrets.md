---
title: System prompts are not secrets
summary: Why hiding data or rules in a system prompt fails, and what to do instead.
---

The Engage game hides a password in the system prompt and asks the model to keep it. Every
level can be beaten, because **anything in the context window can end up in the output**.

## What doesn't work

- **Stronger wording** (“never, under any circumstances”) — raises the effort, not the
  ceiling.
- **Blocking specific tricks** (“don't spell it”, “don't translate it”) — there is always
  another transformation.
- **String filters on the output** — defeated by encodings, hints and paraphrases.

## What to do instead

- **Don't put secrets in prompts.** API keys, passwords and internal URLs belong in code and
  configuration the model never sees.
- **Enforce rules outside the model.** If a user may not see a record, don't fetch it into the
  context in the first place; check permissions in code.
- **Assume the system prompt will leak** and write it so that leaking it is harmless.
- **Layer defences:** input and output classifiers, rate limits, monitoring — each one makes
  attacks harder, none makes them impossible.

## Good prompt engineering still matters

Clear roles, explicit formats and well-chosen examples make models more reliable and harder to
derail by accident. Use the **Playground** to practise them — just don't rely on prompts for
security.
