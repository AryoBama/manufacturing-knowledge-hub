from src.query.models import QueryRequest, ResolutionSource, ResolutionConfidence, KnowledgeType
from src.query.parser import extract_equipment_tags, extract_instrument_tags
from src.query.entity_resolution import resolve_equipment_entity
from src.query.routing import (
    understand_query,
    get_knowledge_types_for_intent,
    route_knowledge_to_documents,
    KnowledgeRouter,
)
from src.query.intent import (
    classify_intent,
    classify_intent_deterministic,
    classify_intent_hybrid,
)
from src.query.llm_intent_classifier import VALID_INTENTS, LLMIntentClassifier


def test_intent_classification():
    assert classify_intent("What is GA-1201A?") == "equipment_information"
    assert classify_intent("What should I check when GA-1201A has high vibration?") == "troubleshooting"
    assert classify_intent("What conditions can trip GA-1201A?") == "protection"
    assert classify_intent("Has this pump failed before?") == "failure_history"
    assert classify_intent("Where is GA-1201A located in the plot plan?") == "location"


def test_hybrid_intent_classification_deterministic_and_llm_fallback():
    # 1. Deterministic confident query -> returns immediately with HIGH confidence
    det_res = classify_intent_deterministic("What is the trip condition for GA-1201A?")
    assert det_res.intent == "protection"
    assert det_res.confidence == "HIGH"
    assert det_res.reason_code == "explicit_protection_keyword"

    # 2. Conversational anomaly without rigid keyword 'troubleshoot' -> LOW in deterministic, HIGH in LLM fallback
    det_ambig = classify_intent_deterministic("Why does the pump stop?")
    assert det_ambig.confidence == "LOW"

    hybrid_res = classify_intent_hybrid("Why does the pump stop?")
    assert hybrid_res.intent == "troubleshooting"
    assert hybrid_res.confidence == "HIGH"
    assert hybrid_res.reason_code in ("abnormal_operation_symptom", "root_cause_analysis_sudden_stop") or "stop" in hybrid_res.reason_code or "symptom" in hybrid_res.reason_code
    assert hybrid_res.intent in VALID_INTENTS

    # 3. Conversational past failure inquiry without rigid keyword 'history/rca'
    hybrid_fh = classify_intent_hybrid("Tell me about previous problems with this pump")
    assert hybrid_fh.intent == "failure_history"
    assert hybrid_fh.confidence == "HIGH"
    assert hybrid_fh.intent in VALID_INTENTS

    # 4. Strict decoupling: Entity resolution remains independent
    tag, res, _, _ = resolve_equipment_entity("Why does GA-1201A stop suddenly?")
    intent_res = classify_intent_hybrid("Why does GA-1201A stop suddenly?")
    assert tag == "GA-1201A"
    assert intent_res.intent == "troubleshooting"



def test_tag_and_alias_extraction():
    tags = extract_equipment_tags("Check vibration on GA-1201A and FV-1201")
    assert "GA-1201A" in tags

    instruments = extract_instrument_tags("Check VSHH-1201 and PSLL-1201 on GA-1201A")
    assert "VSHH-1201" in instruments
    assert "PSLL-1201" in instruments
    assert "GA-1201A" not in instruments

    tags_alias = extract_equipment_tags("What is the design flow of the hexane feed pump?")
    assert tags_alias == ["GA-1201A"]

    dryer_alias = extract_equipment_tags("How to operate the polymer dryer?")
    assert dryer_alias == ["YD-2301"]


def test_entity_resolution_tier_order():
    tag, res, clarify, _ = resolve_equipment_entity("Tell me about GA-1201A")
    assert tag == "GA-1201A"
    assert res.source == ResolutionSource.EXPLICIT_QUERY
    assert res.confidence == ResolutionConfidence.HIGH
    assert not clarify

    tag, res, clarify, reason = resolve_equipment_entity("Compare GA-1201A and YD-2301")
    assert tag is None
    assert res.source == ResolutionSource.EXPLICIT_QUERY
    assert res.confidence == ResolutionConfidence.LOW
    assert clarify is True

    tag, res, clarify, _ = resolve_equipment_entity("What should I check?", session_context={"ui_selected_tag": "GA-1201A"})
    assert tag == "GA-1201A"
    assert res.source == ResolutionSource.UI_CONTEXT
    assert res.confidence == ResolutionConfidence.HIGH
    assert not clarify

    tag, res, clarify, _ = resolve_equipment_entity("What should I check?", session_context={"last_mentioned_tag": "GA-1201A"})
    assert tag == "GA-1201A"
    assert res.source == ResolutionSource.CONVERSATION_CONTEXT
    assert res.confidence == ResolutionConfidence.HIGH
    assert not clarify


def test_knowledge_router_dod():
    router = KnowledgeRouter()

    # 1. Troubleshooting -> OPL, INTERLOCK, MAINTENANCE, PID (OPL/Interlock prioritized)
    kt_tb, docs_tb = router.route_intent("troubleshooting")
    assert "operating_procedure" in kt_tb
    assert "protection_logic" in kt_tb
    assert "failure_history" in kt_tb
    assert "OPL" in docs_tb
    assert "INTERLOCK" in docs_tb
    assert "MAINTENANCE" in docs_tb
    assert "PID" in docs_tb
    # Priority check: OPL and INTERLOCK should appear before PID
    assert docs_tb.index("OPL") < docs_tb.index("PID")
    assert docs_tb.index("INTERLOCK") < docs_tb.index("PID")

    # 2. Failure History -> Maintenance
    kt_fh, docs_fh = router.route_intent("failure_history")
    assert "failure_history" in kt_fh
    assert docs_fh == ["MAINTENANCE"]

    # 3. Location -> Plot Plan + GA Drawing
    kt_loc, docs_loc = router.route_intent("location")
    assert "physical_location" in kt_loc
    assert "PLOT_PLAN" in docs_loc
    assert "GA_DRAWING" in docs_loc

    # 4. Protection -> Interlock + PID
    kt_pr, docs_pr = router.route_intent("protection")
    assert "protection_logic" in kt_pr
    assert "INTERLOCK" in docs_pr
    assert "PID" in docs_pr
