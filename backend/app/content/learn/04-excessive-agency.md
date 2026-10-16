---
title: Excessive agency
summary: What happens when an agent can do more than its job needs — explored with the Reservation agent.
---

**Excessive agency** (OWASP LLM06) means an LLM system has more functionality, permissions
or autonomy than it needs, so a manipulated or confused model can cause real damage.

## The Reservation agent

The cinema assistant can list movies and add bookings to a calendar — and it also has a
`read_from_disc` tool that can “read any file”. That last tool has nothing to do with booking
tickets. Try asking the agent for stored data or configuration files and watch the tool
panel: the agent happily returns customer records and a `.env` file with an API key
(fake, in this sandbox).

## Three kinds of “too much”

- **Excessive functionality** — tools the task does not need (`read_from_disc`).
- **Excessive permissions** — a needed tool with too broad access (reading *any* file instead
  of one specific folder).
- **Excessive autonomy** — high-impact actions without confirmation.

## How to fix it

1. Remove tools that are not essential to the use case.
2. Narrow the remaining ones: fixed directories, read-only database users, scoped API tokens.
3. Run tools with the **user's** permissions, not a powerful service account.
4. Require approval for high-impact actions and log everything.

> Ask of every tool: *if an attacker controlled this agent's next action, what is the worst
> this tool could do?*
