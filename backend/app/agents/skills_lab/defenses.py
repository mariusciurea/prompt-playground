"""Defences the student can toggle, enforced as an ADK before-tool-call hook.

Each defence is a control from the Learn material made real: a tool allowlist, an egress
allowlist, and human approval for outward-facing tools. Turn them on, rerun the attack, and
watch which one stops it.
"""

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from google.adk.tools import BaseTool, ToolContext

from app.agents.skills_lab.workspace import EGRESS_TOOLS

DEFENSES_KEY = "defenses"
BLOCKED_KEY = "blocked_actions"
_ALLOWED_EGRESS_DOMAINS = frozenset({"api.company.example", "intranet.company.example"})


@dataclass(frozen=True, slots=True)
class DefenseConfig:
    """Which defences are active for a run."""

    scanner: bool = False
    tool_allowlist: bool = False
    egress_allowlist: bool = False
    human_approval: bool = False

    def to_state(self) -> dict[str, bool]:
        """Serialize for the session state."""
        return {
            "scanner": self.scanner,
            "tool_allowlist": self.tool_allowlist,
            "egress_allowlist": self.egress_allowlist,
            "human_approval": self.human_approval,
        }

    @classmethod
    def from_state(cls, data: dict[str, Any] | None) -> "DefenseConfig":
        """Read from the session state."""
        data = data or {}
        return cls(
            scanner=bool(data.get("scanner")),
            tool_allowlist=bool(data.get("tool_allowlist")),
            egress_allowlist=bool(data.get("egress_allowlist")),
            human_approval=bool(data.get("human_approval")),
        )


@dataclass(frozen=True, slots=True)
class Blocked:
    """A tool call a defence refused."""

    tool: str
    defense: str
    reason: str


def _deny(tool_context: ToolContext, blocked: Blocked) -> dict[str, Any]:
    records = list(tool_context.state.get(BLOCKED_KEY) or [])
    records.append({"tool": blocked.tool, "defense": blocked.defense, "reason": blocked.reason})
    tool_context.state[BLOCKED_KEY] = records
    return {"status": "blocked", "reason": blocked.reason}


def _allowed_tools(tool_context: ToolContext) -> set[str] | None:
    allowed = tool_context.state.get("skill_allowed_tools")
    return set(allowed) if allowed else None


def enforce_defenses(
    tool: BaseTool, args: dict[str, Any], tool_context: ToolContext
) -> dict[str, Any] | None:
    """Block a tool call that an active defence forbids; otherwise let it run."""
    config = DefenseConfig.from_state(tool_context.state.get(DEFENSES_KEY))
    name = tool.name

    if config.tool_allowlist:
        allowed = _allowed_tools(tool_context)
        if allowed is not None and name not in allowed:
            return _deny(
                tool_context,
                Blocked(name, "tool_allowlist", f"The skill is not allowed to use '{name}'."),
            )

    if name in EGRESS_TOOLS:
        if config.egress_allowlist and name == "http_request":
            host = urlparse(str(args.get("url", ""))).hostname or ""
            if host not in _ALLOWED_EGRESS_DOMAINS:
                return _deny(
                    tool_context,
                    Blocked(
                        name, "egress_allowlist", f"Outbound request to '{host}' is not allowed."
                    ),
                )
        if config.human_approval:
            # A teaching sandbox: rather than pausing the run, we refuse the outward-facing
            # action and tell the model it needs the user's approval. A production system would
            # pause here and resume only after an explicit yes.
            return _deny(
                tool_context,
                Blocked(name, "human_approval", f"'{name}' needs the user's approval first."),
            )
    return None
