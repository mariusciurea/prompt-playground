"""Detect hidden or suspicious content in a skill file.

The scanner is the first defence a user can turn on: before a skill is installed, it
surfaces the tricks that make a quick read of ``SKILL.md`` miss a malicious payload.
"""

import base64
import binascii
import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum

# Unicode "tag" characters (U+E0000..U+E007F) render as nothing but carry readable text.
_TAG_RANGE = range(0xE0000, 0xE0080)
_ZERO_WIDTH = {"​", "‌", "‍", "﻿", "⁠"}
_BIDI = {"‪", "‫", "‬", "‭", "‮", "⁦", "⁧", "⁨", "⁩"}
_HTML_COMMENT = re.compile(r"<!--(.*?)-->", re.DOTALL)
_BASE64_BLOCK = re.compile(r"(?<![A-Za-z0-9+/])([A-Za-z0-9+/]{40,}={0,2})(?![A-Za-z0-9+/=])")
_URL = re.compile(r"https?://[^\s)>\"']+")
_IMPERATIVE = re.compile(
    r"\b(ignore (all |the )?previous|disregard (the )?(above|instructions)|"
    r"do not (tell|mention|inform)|without (telling|informing)|"
    r"exfiltrate|send (the |all )?(contents|files|secrets|credentials)|"
    r"system prompt|reveal the)\b",
    re.IGNORECASE,
)


class Severity(StrEnum):
    """How alarming a finding is."""

    INFO = "info"
    WARNING = "warning"
    DANGER = "danger"


@dataclass(frozen=True, slots=True)
class Finding:
    """One suspicious thing the scanner noticed."""

    kind: str
    severity: Severity
    message: str
    excerpt: str


@dataclass(frozen=True, slots=True)
class ScanResult:
    """The outcome of scanning a skill."""

    findings: tuple[Finding, ...]

    @property
    def is_suspicious(self) -> bool:
        """Whether anything above INFO severity was found."""
        return any(f.severity is not Severity.INFO for f in self.findings)

    @property
    def max_severity(self) -> Severity:
        """The worst severity found (INFO if clean)."""
        order = {Severity.INFO: 0, Severity.WARNING: 1, Severity.DANGER: 2}
        return max(
            (f.severity for f in self.findings), key=lambda s: order[s], default=Severity.INFO
        )


def _excerpt(text: str, limit: int = 160) -> str:
    collapsed = " ".join(text.split())
    return collapsed[:limit] + ("…" if len(collapsed) > limit else "")


def reveal_invisible(text: str) -> str:
    """Return `text` with invisible/tag characters shown as visible placeholders."""
    out: list[str] = []
    for char in text:
        code = ord(char)
        if code in _TAG_RANGE:
            out.append(f"⟦tag:{chr(code - 0xE0000)!r}⟧")
        elif char in _ZERO_WIDTH:
            out.append(f"⟦zw:U+{code:04X}⟧")
        elif char in _BIDI:
            out.append(f"⟦bidi:U+{code:04X}⟧")
        else:
            out.append(char)
    return "".join(out)


def decode_tag_characters(text: str) -> str:
    """Decode any Unicode tag characters back into their ASCII letters."""
    return "".join(chr(ord(c) - 0xE0000) for c in text if ord(c) in _TAG_RANGE)


def _scan_invisible(text: str, findings: list[Finding]) -> None:
    tag_text = decode_tag_characters(text)
    if tag_text:
        findings.append(
            Finding(
                "unicode_tags",
                Severity.DANGER,
                "Hidden instructions written with invisible Unicode tag characters.",
                _excerpt(tag_text),
            )
        )
    zero_width = sum(text.count(c) for c in _ZERO_WIDTH)
    if zero_width:
        findings.append(
            Finding(
                "zero_width",
                Severity.WARNING,
                f"{zero_width} zero-width character(s) that hide text from a casual read.",
                "",
            )
        )
    if any(c in text for c in _BIDI):
        findings.append(
            Finding(
                "bidi",
                Severity.WARNING,
                "Bidirectional control characters that can reorder how text appears.",
                "",
            )
        )


def _scan_html_comments(text: str, findings: list[Finding]) -> None:
    for match in _HTML_COMMENT.finditer(text):
        body = match.group(1).strip()
        severity = Severity.DANGER if _IMPERATIVE.search(body) else Severity.WARNING
        findings.append(
            Finding(
                "html_comment",
                severity,
                "Instructions hidden in an HTML comment (invisible when rendered).",
                _excerpt(body),
            )
        )


def _scan_base64(text: str, findings: list[Finding]) -> None:
    for match in _BASE64_BLOCK.finditer(text):
        block = match.group(1)
        try:
            decoded = base64.b64decode(block, validate=True).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError, ValueError):
            continue
        if not decoded.isprintable() and "\n" not in decoded:
            continue
        severity = Severity.DANGER if _IMPERATIVE.search(decoded) else Severity.WARNING
        findings.append(
            Finding(
                "base64",
                severity,
                "A Base64 block that decodes to readable text — a common way to smuggle orders.",
                _excerpt(decoded),
            )
        )


def _scan_plain(text: str, findings: list[Finding]) -> None:
    visible = "".join(c for c in text if ord(c) not in _TAG_RANGE and c not in _ZERO_WIDTH)
    stripped = _HTML_COMMENT.sub(" ", visible)
    match = _IMPERATIVE.search(stripped)
    if match is not None:
        findings.append(
            Finding(
                "imperative",
                Severity.WARNING,
                "Phrasing typical of prompt-injection ('ignore previous', 'do not tell'…).",
                _excerpt(stripped[max(0, match.start() - 40) : match.end() + 60]),
            )
        )
    for url in {m.group(0) for m in _URL.finditer(stripped)}:
        findings.append(
            Finding("external_url", Severity.INFO, "References an external URL.", url[:160])
        )


def scan_skill(text: str) -> ScanResult:
    """Scan a skill's full text (frontmatter + body) for hidden or suspicious content."""
    findings: list[Finding] = []
    _scan_invisible(text, findings)
    _scan_html_comments(text, findings)
    _scan_base64(text, findings)
    _scan_plain(text, findings)
    order = {Severity.DANGER: 0, Severity.WARNING: 1, Severity.INFO: 2}
    findings.sort(key=lambda f: order[f.severity])
    return ScanResult(findings=tuple(findings))


def normalize_whitespace_report(text: str) -> dict[str, str]:
    """Return human/model views of the text for the 'Inspect skill' panel."""
    human = "".join(c for c in text if unicodedata.category(c) != "Cf" and ord(c) not in _TAG_RANGE)
    return {"as_human_reads": human.strip(), "as_model_reads": reveal_invisible(text).strip()}
