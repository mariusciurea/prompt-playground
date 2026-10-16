---
title: Before you install a skill
summary: A checklist for vetting agent skills, plugins and MCP servers from the internet.
---

## Why skills are risky

A *skill* (or plugin, custom GPT instruction pack, MCP server, prompt template) is text and
sometimes code that you hand to an agent **with the agent's full permissions**. Installing
one is closer to running someone's script than to reading their blog post: the agent will
treat its contents as trusted instructions.

Malicious skills often look perfectly normal. Popular tricks:

- **HTML comments** (`<!-- … -->`) that Markdown viewers hide but the model reads.
- **Invisible Unicode** — zero-width characters or “tag” characters that render as nothing.
- **Encoded payloads** — a Base64 “config block” the skill asks the agent to decode and follow.
- **Remote instructions** — “fetch the latest rules from https://…”, which can change after
  you reviewed the skill.
- **Sleeper behaviour** — harmless until a trigger word or a later update.

## Checklist

- [ ] **Source.** Who wrote it? Is the repository/publisher established? Are reviews and
      download counts real?
- [ ] **Read every file**, not just the description — including referenced resources and
      scripts.
- [ ] **Reveal hidden content.** View the raw file; search for `<!--`, long Base64 strings,
      URLs, and invisible characters (a hex view or a scanner helps).
- [ ] **Permissions.** Which tools does it want? Does a “PDF summarizer” really need to make
      HTTP requests or send e-mail?
- [ ] **Secrets.** Make sure credentials (`.env`, API keys, SSH keys) are outside anything
      the agent can read.
- [ ] **Pin a version** (commit hash or checksum) so it cannot change silently after review.
- [ ] **Try it in a sandbox** with fake data first and watch which tools it calls.
- [ ] **Keep approvals on** for actions that send data out or can't be undone.

## If you suspect a bad skill

Uninstall it, rotate any credential the agent could read, and review the agent's tool-call
logs to see what was sent where.
