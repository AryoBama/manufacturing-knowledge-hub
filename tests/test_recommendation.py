import pytest
from src.pipeline import ManufacturingKnowledgeHub


@pytest.fixture(scope="module")
def hub():
    return ManufacturingKnowledgeHub()


def test_factual_query_has_no_unsolicited_recommendations(hub):
    ans = hub.ask("What is GA-1201A and what is its rated flow?")
    # Factual query should not produce unsolicited operational recommendations
    assert len(ans.recommendations) == 0


def test_protection_query_has_grounded_recommendations(hub):
    ans = hub.ask("What conditions can trip GA-1201A?")
    assert len(ans.recommendations) >= 1
    for rec in ans.recommendations:
        assert rec.action is not None
        assert rec.basis is not None
        assert rec.priority in ("CRITICAL", "HIGH", "MEDIUM", "LOW")
        if rec.evidence_id:
            assert rec.evidence_id.startswith(("EV-DOC-", "EV-REL-", "EV-TR-", "EV-MNT-"))


def test_troubleshooting_query_has_diagnostic_recommendations(hub):
    ans = hub.ask("What should I check when GA-1201A has high vibration?")
    assert len(ans.recommendations) >= 1
    assert any("vibration" in rec.action.lower() for rec in ans.recommendations)


def test_clarification_query_has_no_recommendations(hub):
    ans = hub.ask("What should I check if there is abnormal noise and vibration?")
    assert len(ans.recommendations) == 0
