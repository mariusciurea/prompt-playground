"""Turn a Skills Lab run into a plain, deterministic 'what just happened' explanation.

The debrief is computed from the run's recorded events, never written by the model, so it
always reflects what actually occurred.
"""

from dataclasses import dataclass
from typing import Any

from app.agents.skills_lab.catalog import HideTechnique

_TECHNIQUE_TEXT = {
    HideTechnique.HTML_COMMENT: (
        "The payload hid in an HTML comment, invisible when the file is rendered but plain text "
        "to the model."
    ),
    HideTechnique.UNICODE_TAGS: (
        "The payload was written with invisible Unicode tag characters, so the file looked "
        "harmless to a human reading it."
    ),
    HideTechnique.BASE64: (
        "The payload was a Base64 block the skill asked the assistant to decode and follow."
    ),
}
_LEARN_LINK = {
    HideTechnique.HTML_COMMENT: "installing-skills-safely",
    HideTechnique.UNICODE_TAGS: "installing-skills-safely",
    HideTechnique.BASE64: "installing-skills-safely",
}


@dataclass(frozen=True, slots=True)
class Debrief:
    """A structured explanation of one run."""

    attacked: bool
    exfiltrated: bool
    steps: list[str]
    technique: str
    stopped_by: list[str]
    learn_slug: str


def build_debrief(
    *,
    malicious: bool,
    technique: HideTechnique,
    attacker_log: list[dict[str, Any]],
    outbox: list[dict[str, Any]],
    blocked: list[dict[str, Any]],
) -> Debrief:
    """Explain what the loaded skill tried, whether it succeeded, and what stopped it."""
    exfiltrated = bool(attacker_log) or bool(outbox)
    steps: list[str] = []

    if not malicious:
        steps.append("This skill was benign: it only did what its description promised.")
        return Debrief(False, False, steps, "", [], "prompt-injection-101")

    steps.append(
        "The skill carried hidden instructions aimed at the assistant, not at you (indirect "
        "prompt injection)."
    )
    for entry in attacker_log:
        steps.append(
            f"The assistant was told to POST workspace data to {entry.get('url')} — a server the "
            "attacker controls. In the sandbox this was only recorded."
        )
    for mail in outbox:
        steps.append(f"The assistant was told to e-mail data to {mail.get('to')}.")
    if exfiltrated:
        steps.append("Meanwhile you received a normal-looking answer, so nothing seemed wrong.")

    stopped_by = sorted({b.get("defense", "") for b in blocked if b.get("defense")})
    if stopped_by and not exfiltrated:
        names = {
            "tool_allowlist": "the per-skill tool allowlist",
            "egress_allowlist": "the egress allowlist",
            "human_approval": "requiring human approval",
            "scanner": "the skill scanner",
        }
        pretty = [names.get(d, d) for d in stopped_by]
        steps.append(f"The attack was blocked by {', '.join(pretty)} before any data left.")

    return Debrief(
        attacked=True,
        exfiltrated=exfiltrated,
        steps=steps,
        technique=_TECHNIQUE_TEXT.get(technique, ""),
        stopped_by=stopped_by,
        learn_slug=_LEARN_LINK.get(technique, "installing-skills-safely"),
    )
