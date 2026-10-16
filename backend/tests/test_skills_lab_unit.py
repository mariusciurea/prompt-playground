"""Pure-logic tests for the Skills Lab: scanner, catalog payloads, defences, debrief."""

from app.agents.skills_lab.catalog import CATALOG, HideTechnique
from app.agents.skills_lab.debrief import build_debrief
from app.agents.skills_lab.scanner import Severity, decode_tag_characters, scan_skill


def test_scanner_detects_every_malicious_catalog_skill():
    for skill in CATALOG:
        result = scan_skill(skill.full_text)
        if skill.malicious:
            assert result.is_suspicious, skill.name
            assert result.max_severity is Severity.DANGER, skill.name
        else:
            assert not result.is_suspicious, skill.name


def test_scanner_identifies_each_technique():
    kinds = {
        s.technique: {f.kind for f in scan_skill(s.full_text).findings}
        for s in CATALOG
        if s.malicious
    }
    assert "html_comment" in kinds[HideTechnique.HTML_COMMENT]
    assert "unicode_tags" in kinds[HideTechnique.UNICODE_TAGS]
    assert "base64" in kinds[HideTechnique.BASE64]


def test_hidden_payloads_are_invisible_to_a_plain_read():
    unicode_skill = next(s for s in CATALOG if s.technique is HideTechnique.UNICODE_TAGS)
    # The visible text carries no attack words; the payload is only in tag characters.
    visible = "".join(c for c in unicode_skill.body if ord(c) < 0xE0000)
    assert "http_request" not in visible
    assert "http_request" in decode_tag_characters(unicode_skill.body)


def test_scanner_passes_clean_text():
    assert not scan_skill("# Helper\n\nSummarize the document into bullet points.").is_suspicious


def test_debrief_reports_exfiltration_and_the_defence_that_stopped_it():
    attacked = build_debrief(
        malicious=True,
        technique=HideTechnique.HTML_COMMENT,
        attacker_log=[{"url": "https://exfil.evil-skills.example/collect", "body": "secrets"}],
        outbox=[],
        blocked=[],
    )
    assert attacked.attacked
    assert attacked.exfiltrated
    assert any("exfil.evil-skills.example" in step for step in attacked.steps)

    defended = build_debrief(
        malicious=True,
        technique=HideTechnique.HTML_COMMENT,
        attacker_log=[],
        outbox=[],
        blocked=[{"defense": "egress_allowlist", "tool": "http_request"}],
    )
    assert not defended.exfiltrated
    assert defended.stopped_by == ["egress_allowlist"]


def test_debrief_for_a_benign_skill():
    result = build_debrief(
        malicious=False, technique=HideTechnique.NONE, attacker_log=[], outbox=[], blocked=[]
    )
    assert not result.attacked
    assert not result.exfiltrated
