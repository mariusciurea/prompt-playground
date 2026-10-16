---
title: Least privilege for AI agents
summary: Practical controls that limit the damage when an agent is manipulated.
---

Assume the agent **will** eventually be tricked. The question is how much harm it can do
when that happens. Each control below shrinks the blast radius.

## Tool allowlists

Give each agent — and ideally each skill — only the tools its task requires. A summarizer
needs `read_file`; it does not need `http_request` or `send_email`. Enforce the list in
code (for example in a *before tool call* hook), not in the prompt.

## Egress control

Most damaging attacks need to send data **out**. Restrict outbound requests to an allowlist
of domains, and block everything else at the tool or network level.

## Human in the loop

Require explicit approval for actions that are outward-facing or irreversible: sending
messages, making payments, deleting data, changing permissions. Show the user exactly
*what* will be sent *where* — a vague “Allow?” prompt trains people to click yes.

## Keep secrets out of reach

Credentials should never be readable by the model. Tools that need a key should load it
themselves, server-side, and never return it in a result.

## Separate trust levels

Content from the user, from your system, and from third parties (web pages, files, skills)
deserves different trust. Label it, keep it apart, and never let third-party text silently
gain the authority of your system prompt.

## Log and review

Record every tool call with its arguments and results. Logs turn a silent compromise into
something you can detect, investigate and learn from.
