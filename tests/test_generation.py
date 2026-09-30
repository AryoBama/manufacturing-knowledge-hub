import pytest
from src.pipeline import ManufacturingKnowledgeHub
from src.generation.models import ConfidenceLevel, SourceCitation, ActionRecommendation
from src.generation.formatter import AnswerFormatter


@pytest.fixture(scope="module")
def hub():
    return ManufacturingKnowledgeHub()


def test_generation_equipment_info(hub):
    ans = hub.ask("What is GA-1201A and what is its rated flow?")
    assert ans.equipment_tag == "GA-1201A"
    assert ans.intent == "equipment_information"
    assert ans.confidence == ConfidenceLevel.HIGH
    assert not ans.requires_clarification
    assert len(ans.citations) > 0
    assert any(c.document_type == "DATASHEET" for c in ans.citations)
    assert any("flow" in p.lower() for p in ans.detailed_points) or "flow" in ans.summary_answer.lower()


def test_generation_protection(hub):
    ans = hub.ask("What conditions can trip GA-1201A?")
    assert ans.equipment_tag == "GA-1201A"
    assert ans.intent == "protection"
    assert ans.confidence == ConfidenceLevel.HIGH
    assert not ans.requires_clarification
    assert len(ans.citations) > 0
    assert any(c.document_type in ("INTERLOCK", "PID") for c in ans.citations)
    assert len(ans.detailed_points) > 0
    assert len(ans.recommended_actions) > 0


def test_generation_troubleshooting(hub):
    ans = hub.ask("What should I check when GA-1201A has high vibration?")
    assert ans.equipment_tag == "GA-1201A"
    assert ans.intent == "troubleshooting"
    assert ans.confidence == ConfidenceLevel.HIGH
    assert not ans.requires_clarification
    assert len(ans.recommended_actions) >= 1
    assert any("vibration" in act.description.lower() for act in ans.recommended_actions)


def test_generation_clarification_refusal(hub):
    ans = hub.ask("What should I check if there is abnormal noise and vibration?")
    assert ans.requires_clarification is True
    assert ans.confidence in (ConfidenceLevel.LOW, ConfidenceLevel.UNVERIFIED)
    assert len(ans.citations) == 0  # No false citations on ambiguous query
    assert ans.clarification_prompt is not None


def test_generation_multi_asset_failure_history(hub):
    ans = hub.ask("What is the maintenance history of YD-2301?")
    assert ans.equipment_tag == "YD-2301"
    assert ans.intent == "failure_history"
    assert ans.confidence == ConfidenceLevel.HIGH
    assert any(c.document_type == "MAINTENANCE" for c in ans.citations)
    assert len(ans.detailed_points) > 0


def test_formatter_markdown_and_terminal(hub):
    ans = hub.ask("What is GA-1201A and what is its rated flow?")
    md = AnswerFormatter.to_markdown(ans)
    term = AnswerFormatter.to_terminal_text(ans)

    assert "### Knowledge Hub Response" in md
    assert "Verified Engineering Sources" in md
    assert "[CHANDRA ASRI MANUFACTURING KNOWLEDGE HUB]" in term
    assert "PROVENANCE & SOURCE CITATIONS" in term
